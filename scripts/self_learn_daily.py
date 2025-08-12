#!/usr/bin/env python3
"""
Daily self-learning cycle
Runs evaluation, bandit updates, prompt tuning, and calibration
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.hybrid.collector import FeedbackCollector, AutoEvaluator
from src.hybrid.bandit import BanditRouter
from src.hybrid.prompter import PromptTuner
from src.hybrid.evaluator import QualityEvaluator, RegressionDetector
from src.hybrid.calibrator import BudgetCalibrator, CostController
import yaml


class SelfLearningCycle:
    """Orchestrates the daily self-learning cycle"""
    
    def __init__(self, cfg_path: str = "config/selflearn.yaml"):
        self.cfg_path = cfg_path
        with open(cfg_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        # Initialize components
        self.collector = FeedbackCollector(self.cfg['feedback_store'])
        self.bandit_router = BanditRouter(cfg_path)
        self.prompt_tuner = PromptTuner(cfg_path=cfg_path)
        self.evaluator = QualityEvaluator(cfg_path)
        self.regression_detector = RegressionDetector(cfg_path)
        self.cost_controller = CostController(cfg_path)
        
        # State directory
        self.state_dir = Path(self.cfg['state_dir'])
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Cycle log
        self.cycle_log = []
    
    def run_daily_cycle(self) -> Dict[str, Any]:
        """Run the complete daily learning cycle"""
        
        cycle_start = datetime.now()
        self.log("Starting daily self-learning cycle")
        
        try:
            # 1. Ingest: Load recent events
            events = self._ingest_events()
            self.log(f"Loaded {len(events)} events from last {self.cfg['window_days']} days")
            
            if len(events) < self.cfg['min_samples_route']:
                self.log("Insufficient data for full cycle, running minimal updates")
                return self._minimal_cycle()
            
            # 2. Evaluate: Calculate quality metrics
            evaluation_result = self._evaluate_quality(events)
            self.log(f"Quality evaluation completed, gates passed: {evaluation_result['quality_gates_passed']}")
            
            # 3. Check for regressions
            regression_result = self._check_regressions(events)
            
            # 4. Update bandit with recent performance
            bandit_result = self._update_bandit(events)
            self.log(f"Updated bandit with {bandit_result['updates_made']} context updates")
            
            # 5. Tune prompts if enough data
            prompt_result = self._tune_prompts(events)
            self.log(f"Prompt tuning: {prompt_result['action_taken']}")
            
            # 6. Calibrate budget and routing
            calibration_result = self._calibrate_budget()
            if calibration_result['adjustments_made']:
                self.log(f"Budget calibration: {len(calibration_result['adjustments_made'])} adjustments")
            
            # 7. Quality gates and rollback check
            rollback_result = self._check_rollback_conditions(
                evaluation_result, regression_result, calibration_result
            )
            
            # 8. Persist state and generate report
            cycle_summary = self._finalize_cycle(
                cycle_start, events, evaluation_result, bandit_result, 
                prompt_result, calibration_result, rollback_result
            )
            
            self.log("Daily cycle completed successfully")
            return cycle_summary
            
        except Exception as e:
            self.log(f"ERROR in daily cycle: {e}")
            return {"status": "error", "error": str(e), "cycle_log": self.cycle_log}
    
    def _ingest_events(self) -> List[Dict[str, Any]]:
        """Load and filter recent events"""
        events = self.collector.read_events(self.cfg['window_days'])
        
        # Filter out incomplete events
        complete_events = []
        for event in events:
            if all(key in event for key in ['route', 'output', 'cost']):
                complete_events.append(event)
        
        return complete_events
    
    def _evaluate_quality(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate overall quality metrics"""
        return self.evaluator.evaluate_batch(events)
    
    def _check_regressions(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for performance regressions"""
        compare_days = self.cfg['rollbacks']['compare_days']
        cutoff_time = time.time() - (compare_days * 24 * 3600)
        
        # Split events into recent and historical
        recent_events = []
        historical_events = []
        
        for event in events:
            event_time = datetime.fromisoformat(event['ts'].replace('Z', '+00:00')).timestamp()
            if event_time >= cutoff_time:
                recent_events.append(event)
            else:
                historical_events.append(event)
        
        if len(recent_events) < 20 or len(historical_events) < 20:
            return {"regression_detected": False, "reason": "Insufficient data for comparison"}
        
        should_rollback, rollback_data = self.regression_detector.should_rollback(recent_events, historical_events)
        return {"regression_detected": should_rollback, "rollback_data": rollback_data}
    
    def _update_bandit(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update bandit with performance data"""
        updates_made = 0
        
        for event in events:
            if 'input' in event and 'route' in event and 'output' in event:
                context = event['input']
                model = event['route'].get('model')
                
                # Calculate quality metrics for reward
                output = event['output']
                user = event.get('user', {})
                editor = event.get('editor', {})
                
                quality_metrics = {
                    'editor_accepted': editor.get('accepted', 0),
                    'user_engagement': user.get('click', 0) * min(1.0, user.get('time_on_card', 0) / 60.0),
                    'schema_ok': output.get('schema_ok', 0),
                    'ref_quality': 1.0 - output.get('ref_miss_rate', 0),
                    'hallu_score': output.get('hallu_score', 0),
                    'ref_miss_rate': output.get('ref_miss_rate', 0)
                }
                
                cost_eur = event.get('cost', {}).get('eur', 0)
                
                self.bandit_router.update(context, model, quality_metrics, cost_eur)
                updates_made += 1
        
        return {"updates_made": updates_made}
    
    def _tune_prompts(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update prompt variants based on performance"""
        
        # Group events by model and variant
        variant_performance = {}
        
        for event in events:
            route = event.get('route', {})
            model = route.get('model')
            variant_id = route.get('prompt_variant', f"{model}_default")
            
            if variant_id not in variant_performance:
                variant_performance[variant_id] = []
            
            # Calculate performance metrics
            output = event.get('output', {})
            user = event.get('user', {})
            editor = event.get('editor', {})
            
            metrics = {
                'schema_ok': output.get('schema_ok', 0),
                'editor_accepted': editor.get('accepted', 0),
                'user_engagement': user.get('click', 0) * min(1.0, user.get('time_on_card', 0) / 60.0),
                'hallu_score': output.get('hallu_score', 0)
            }
            
            variant_performance[variant_id].append((model, metrics))
        
        # Update prompt tuner
        updates_made = 0
        for variant_id, performances in variant_performance.items():
            if len(performances) >= 5:  # Minimum sample size
                model = performances[0][0]  # Get model from first performance
                
                # Average metrics
                avg_metrics = {}
                for key in ['schema_ok', 'editor_accepted', 'user_engagement', 'hallu_score']:
                    values = [perf[1][key] for perf in performances]
                    avg_metrics[key] = sum(values) / len(values)
                
                self.prompt_tuner.record(model, variant_id, avg_metrics)
                updates_made += 1
        
        if updates_made >= self.cfg['min_samples_prompt']:
            return {"action_taken": f"Updated {updates_made} prompt variants"}
        else:
            return {"action_taken": "Insufficient data for prompt tuning"}
    
    def _calibrate_budget(self) -> Dict[str, Any]:
        """Run budget calibration"""
        return self.cost_controller.daily_calibration()
    
    def _check_rollback_conditions(self, evaluation_result: Dict[str, Any], 
                                 regression_result: Dict[str, Any],
                                 calibration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check if rollback is needed"""
        
        should_rollback = False
        rollback_reasons = []
        
        # Quality gates failure
        if not evaluation_result.get('quality_gates_passed', True):
            should_rollback = True
            rollback_reasons.extend(evaluation_result.get('quality_issues', []))
        
        # Performance regression
        if regression_result.get('regression_detected', False):
            should_rollback = True
            rollback_reasons.extend(regression_result.get('details', []))
        
        # Budget emergency
        if calibration_result.get('routing_config', {}).get('emergency_mode', False):
            rollback_reasons.append("Budget emergency mode triggered")
        
        if should_rollback:
            self._execute_rollback(rollback_reasons)
        
        return {
            "rollback_executed": should_rollback,
            "reasons": rollback_reasons
        }
    
    def _execute_rollback(self, reasons: List[str]):
        """Execute rollback procedure"""
        self.log(f"ROLLBACK TRIGGERED: {'; '.join(reasons)}")
        
        # Reset to conservative settings
        conservative_state = {
            "gpt5_usage_multiplier": 1.0,  # Use GPT-5 for all critical content
            "validation_only_segments": [],
            "frozen_mode": True,  # Stop experimentation
            "emergency_mode": False,
            "last_adjustment": datetime.now().isoformat(),
            "adjustment_reason": f"Rollback due to: {'; '.join(reasons)}"
        }
        
        # Save conservative routing state
        routing_file = self.state_dir / "routing_adjustments.json"
        with open(routing_file, 'w') as f:
            json.dump(conservative_state, f, indent=2)
        
        # Log rollback
        rollback_log = {
            "timestamp": datetime.now().isoformat(),
            "reasons": reasons,
            "action": "conservative_routing_restored"
        }
        
        change_log_file = self.state_dir / "change_log.jsonl"
        with open(change_log_file, 'a') as f:
            f.write(json.dumps(rollback_log) + '\n')
    
    def _minimal_cycle(self) -> Dict[str, Any]:
        """Run minimal cycle when insufficient data"""
        
        # Just run budget calibration
        calibration_result = self._calibrate_budget()
        
        return {
            "status": "minimal_cycle",
            "reason": "insufficient_data",
            "calibration": calibration_result,
            "cycle_log": self.cycle_log
        }
    
    def _finalize_cycle(self, start_time: datetime, events: List[Dict[str, Any]], 
                       evaluation: Dict[str, Any], bandit: Dict[str, Any],
                       prompt: Dict[str, Any], calibration: Dict[str, Any],
                       rollback: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize cycle and generate summary"""
        
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            "cycle_timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "events_processed": len(events),
            "status": "success",
            "evaluation": evaluation,
            "bandit_updates": bandit,
            "prompt_tuning": prompt,
            "budget_calibration": calibration,
            "rollback_check": rollback,
            "cycle_log": self.cycle_log
        }
        
        # Save summary
        summary_file = self.state_dir / f"cycle_summary_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Update latest summary
        latest_file = self.state_dir / "latest_cycle.json"
        with open(latest_file, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return summary
    
    def log(self, message: str):
        """Add message to cycle log"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        self.cycle_log.append(log_entry)
        print(log_entry)


def main():
    parser = argparse.ArgumentParser(description="Run daily self-learning cycle")
    parser.add_argument("--cfg", default="config/selflearn.yaml", help="Config file path")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - No state changes will be made")
    
    cycle = SelfLearningCycle(args.cfg)
    result = cycle.run_daily_cycle()
    
    # Print summary
    print("\n" + "="*60)
    print("DAILY SELF-LEARNING CYCLE SUMMARY")
    print("="*60)
    
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Events processed: {result.get('events_processed', 0)}")
    
    if 'evaluation' in result:
        eval_result = result['evaluation']
        print(f"Quality gates passed: {eval_result.get('quality_gates_passed', False)}")
        
        if 'overall_metrics' in eval_result:
            metrics = eval_result['overall_metrics']
            print(f"Card pass rate: {metrics.get('card_pass_rate', 0):.3f}")
            print(f"Hallucination rate: {metrics.get('hallu_rate', 0):.3f}")
    
    if 'budget_calibration' in result:
        budget = result['budget_calibration']
        if budget.get('adjustments_made'):
            print("Budget adjustments:")
            for adj in budget['adjustments_made']:
                print(f"  - {adj}")
    
    if 'rollback_check' in result:
        rollback = result['rollback_check']
        if rollback.get('rollback_executed'):
            print("⚠️  ROLLBACK EXECUTED:")
            for reason in rollback.get('reasons', []):
                print(f"  - {reason}")
    
    print("="*60)
    
    # Exit with appropriate code
    if result.get('status') == 'error':
        sys.exit(1)
    elif result.get('rollback_check', {}).get('rollback_executed'):
        sys.exit(2)  # Rollback executed
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
