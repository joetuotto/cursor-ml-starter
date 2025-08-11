#!/usr/bin/env python3
"""
Quality evaluation and regression detection
Monitors performance and triggers rollbacks when quality degrades
"""

import json
import statistics
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import yaml
import numpy as np


class QualityEvaluator:
    """Evaluates content quality and detects regressions"""
    
    def __init__(self, cfg_path: str = "config/selflearn.yaml"):
        with open(cfg_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        self.quality_gates = self.cfg['quality_gates']
        self.window_days = self.cfg['window_days']
        self.regression_cfg = self.cfg['rollbacks']
    
    def evaluate_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a batch of events for quality metrics"""
        
        if not events:
            return {"error": "No events to evaluate"}
        
        # Group events by model and time period
        model_groups = defaultdict(list)
        segment_groups = defaultdict(list)
        
        for event in events:
            if 'route' in event and 'output' in event:
                model = event['route'].get('model', 'unknown')
                model_groups[model].append(event)
                
                # Create segment key
                input_ctx = event.get('input', {})
                segment = f"{input_ctx.get('lang', 'unknown')}_{input_ctx.get('country', 'unknown')}"
                segment_groups[segment].append(event)
        
        # Calculate metrics
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_events": len(events),
            "quality_gates_passed": True,
            "overall_metrics": self._calculate_metrics(events),
            "model_metrics": {},
            "segment_metrics": {},
            "quality_issues": []
        }
        
        # Model-specific metrics
        for model, model_events in model_groups.items():
            if len(model_events) >= 10:  # Minimum sample size
                results["model_metrics"][model] = self._calculate_metrics(model_events)
        
        # Segment-specific metrics
        for segment, segment_events in segment_groups.items():
            if len(segment_events) >= 10:
                results["segment_metrics"][segment] = self._calculate_metrics(segment_events)
        
        # Check quality gates
        overall = results["overall_metrics"]
        results["quality_gates_passed"] = self._check_quality_gates(overall)
        
        if not results["quality_gates_passed"]:
            results["quality_issues"] = self._identify_quality_issues(overall)
        
        return results
    
    def _calculate_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate quality metrics for a set of events"""
        
        if not events:
            return {}
        
        # Extract metrics from events
        schema_oks = []
        why_matters_oks = []
        hallu_scores = []
        ref_miss_rates = []
        editor_accepts = []
        user_engagements = []
        costs = []
        
        for event in events:
            output = event.get('output', {})
            user = event.get('user', {})
            editor = event.get('editor', {})
            cost = event.get('cost', {})
            
            schema_oks.append(float(output.get('schema_ok', 0)))
            why_matters_oks.append(float(output.get('why_matters_ok', 0)))
            hallu_scores.append(float(output.get('hallu_score', 0)))
            ref_miss_rates.append(float(output.get('ref_miss_rate', 0)))
            
            editor_accepts.append(float(editor.get('accepted', 0)))
            user_engagements.append(float(user.get('click', 0) * user.get('time_on_card', 0) / 60.0))  # Engagement score
            
            costs.append(float(cost.get('eur', 0)))
        
        # Calculate aggregated metrics
        metrics = {
            "card_pass_rate": statistics.mean(schema_oks),
            "coverage_why_matters": statistics.mean(why_matters_oks),
            "hallu_rate": statistics.mean(hallu_scores),
            "ref_miss_rate": statistics.mean(ref_miss_rates),
            "editor_accept_rate": statistics.mean(editor_accepts) if editor_accepts else 0.0,
            "user_engagement": statistics.mean(user_engagements) if user_engagements else 0.0,
            "avg_cost_eur": statistics.mean(costs) if costs else 0.0,
            "total_cost_eur": sum(costs),
            "sample_size": len(events)
        }
        
        # Add confidence intervals for key metrics
        if len(events) >= 30:
            metrics.update(self._calculate_confidence_intervals(
                schema_oks, hallu_scores, ref_miss_rates, editor_accepts
            ))
        
        return metrics
    
    def _calculate_confidence_intervals(self, schema_oks: List[float], hallu_scores: List[float], 
                                      ref_miss_rates: List[float], editor_accepts: List[float]) -> Dict[str, float]:
        """Calculate 95% confidence intervals for key metrics"""
        
        def wilson_ci(successes: int, n: int) -> Tuple[float, float]:
            """Wilson confidence interval for proportions"""
            if n == 0:
                return 0.0, 0.0
            
            p = successes / n
            z = 1.96  # 95% CI
            
            denominator = 1 + z**2 / n
            centre = (p + z**2 / (2*n)) / denominator
            margin = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denominator
            
            return max(0, centre - margin), min(1, centre + margin)
        
        n = len(schema_oks)
        
        cis = {}
        if n > 0:
            # Schema pass rate CI
            schema_successes = sum(schema_oks)
            lower, upper = wilson_ci(int(schema_successes), n)
            cis["schema_pass_ci_lower"] = lower
            cis["schema_pass_ci_upper"] = upper
            
            # Editor accept rate CI
            if editor_accepts:
                editor_successes = sum(editor_accepts)
                lower, upper = wilson_ci(int(editor_successes), len(editor_accepts))
                cis["editor_accept_ci_lower"] = lower
                cis["editor_accept_ci_upper"] = upper
        
        return cis
    
    def _check_quality_gates(self, metrics: Dict[str, float]) -> bool:
        """Check if metrics pass quality gates"""
        
        gates = self.quality_gates
        
        checks = [
            metrics.get('card_pass_rate', 0) >= gates['min_card_pass_rate'],
            metrics.get('coverage_why_matters', 0) >= gates['min_coverage_why_matters'],
            metrics.get('hallu_rate', 1) <= gates['max_hallu_rate'],
            metrics.get('ref_miss_rate', 1) <= gates['max_ref_miss_rate']
        ]
        
        return all(checks)
    
    def _identify_quality_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Identify specific quality issues"""
        
        issues = []
        gates = self.quality_gates
        
        if metrics.get('card_pass_rate', 0) < gates['min_card_pass_rate']:
            issues.append(f"Card pass rate too low: {metrics['card_pass_rate']:.3f} < {gates['min_card_pass_rate']}")
        
        if metrics.get('coverage_why_matters', 0) < gates['min_coverage_why_matters']:
            issues.append(f"Why-it-matters coverage too low: {metrics['coverage_why_matters']:.3f} < {gates['min_coverage_why_matters']}")
        
        if metrics.get('hallu_rate', 1) > gates['max_hallu_rate']:
            issues.append(f"Hallucination rate too high: {metrics['hallu_rate']:.3f} > {gates['max_hallu_rate']}")
        
        if metrics.get('ref_miss_rate', 1) > gates['max_ref_miss_rate']:
            issues.append(f"Reference miss rate too high: {metrics['ref_miss_rate']:.3f} > {gates['max_ref_miss_rate']}")
        
        return issues
    
    def detect_regression(self, current_events: List[Dict[str, Any]], 
                         historical_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect if current performance has regressed compared to historical"""
        
        if not self.regression_cfg['regression_guardrail']:
            return {"regression_detected": False, "reason": "Regression detection disabled"}
        
        current_metrics = self._calculate_metrics(current_events)
        historical_metrics = self._calculate_metrics(historical_events)
        
        if not current_metrics or not historical_metrics:
            return {"regression_detected": False, "reason": "Insufficient data"}
        
        # Check required improvements
        regression_detected = False
        regression_details = []
        
        for metric in self.regression_cfg['require_improvement']:
            current_val = current_metrics.get(metric, 0)
            historical_val = historical_metrics.get(metric, 0)
            
            # For rates that should decrease (like hallu_rate, ref_miss_rate)
            if metric in ['hallu_rate', 'ref_miss_rate']:
                if current_val > historical_val * 1.2:  # 20% worse threshold
                    regression_detected = True
                    regression_details.append(f"{metric}: {current_val:.3f} > {historical_val:.3f} (20% threshold)")
            
            # For rates that should increase (like card_pass_rate)
            else:
                if current_val < historical_val * 0.8:  # 20% worse threshold
                    regression_detected = True
                    regression_details.append(f"{metric}: {current_val:.3f} < {historical_val:.3f} (20% threshold)")
        
        # Statistical significance test (simple z-test for proportions)
        if regression_detected and len(current_events) >= 30 and len(historical_events) >= 30:
            # Perform binomial test for schema_ok rate
            p_test = self._binomial_significance_test(
                current_events, historical_events, 'schema_ok'
            )
            
            if p_test > 0.05:  # Not statistically significant
                regression_detected = False
                regression_details.append("Not statistically significant (p > 0.05)")
        
        return {
            "regression_detected": regression_detected,
            "details": regression_details,
            "current_metrics": current_metrics,
            "historical_metrics": historical_metrics,
            "sample_sizes": {
                "current": len(current_events),
                "historical": len(historical_events)
            }
        }
    
    def _binomial_significance_test(self, current_events: List[Dict[str, Any]], 
                                   historical_events: List[Dict[str, Any]], 
                                   metric: str) -> float:
        """Simple binomial test for metric significance"""
        
        # Extract binary outcomes
        current_outcomes = [event.get('output', {}).get(metric, 0) for event in current_events]
        historical_outcomes = [event.get('output', {}).get(metric, 0) for event in historical_events]
        
        n1, n2 = len(current_outcomes), len(historical_outcomes)
        x1, x2 = sum(current_outcomes), sum(historical_outcomes)
        
        if n1 == 0 or n2 == 0:
            return 1.0
        
        p1, p2 = x1/n1, x2/n2
        p_pooled = (x1 + x2) / (n1 + n2)
        
        # Standard error
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
        
        if se == 0:
            return 1.0
        
        # Z-statistic
        z = (p1 - p2) / se
        
        # Two-tailed p-value (approximate)
        p_value = 2 * (1 - np.abs(z) / 3.0)  # Rough approximation
        
        return max(0.0, min(1.0, p_value))


class RegressionDetector:
    """Wrapper for regression detection functionality"""
    
    def __init__(self, cfg_path: str = "config/selflearn.yaml"):
        self.evaluator = QualityEvaluator(cfg_path)
    
    def should_rollback(self, recent_events: List[Dict[str, Any]], 
                       comparison_events: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """Determine if a rollback should be triggered"""
        
        # Quality gate check
        recent_eval = self.evaluator.evaluate_batch(recent_events)
        if not recent_eval.get('quality_gates_passed', True):
            return True, {
                "reason": "quality_gates_failed",
                "details": recent_eval.get('quality_issues', []),
                "evaluation": recent_eval
            }
        
        # Regression check
        regression_result = self.evaluator.detect_regression(recent_events, comparison_events)
        if regression_result.get('regression_detected', False):
            return True, {
                "reason": "performance_regression",
                "details": regression_result.get('details', []),
                "regression_analysis": regression_result
            }
        
        return False, {"reason": "no_issues_detected"}


if __name__ == "__main__":
    # Test evaluator
    evaluator = QualityEvaluator()
    
    # Create mock events
    mock_events = []
    for i in range(50):
        event = {
            "id": f"test_{i}",
            "route": {"model": "gpt5" if i % 3 == 0 else "deepseek"},
            "input": {"lang": "fi" if i % 2 == 0 else "en", "country": "FI" if i % 2 == 0 else "US"},
            "output": {
                "schema_ok": 1 if i % 10 != 0 else 0,  # 90% pass rate
                "why_matters_ok": 1 if i % 8 != 0 else 0,  # 87.5% pass rate
                "hallu_score": 0.02 + (i % 5) * 0.01,  # 0.02-0.06
                "ref_miss_rate": 0.05 + (i % 3) * 0.02  # 0.05-0.09
            },
            "user": {"click": 1 if i % 4 != 0 else 0, "time_on_card": 30 + i % 60},
            "editor": {"accepted": 1 if i % 5 != 0 else 0},
            "cost": {"eur": 0.02 + (i % 10) * 0.003}
        }
        mock_events.append(event)
    
    # Evaluate
    results = evaluator.evaluate_batch(mock_events)
    
    print("Quality Evaluation Results:")
    print(f"Total events: {results['total_events']}")
    print(f"Quality gates passed: {results['quality_gates_passed']}")
    print("\nOverall metrics:")
    for metric, value in results['overall_metrics'].items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.3f}")
        else:
            print(f"  {metric}: {value}")
    
    if results['quality_issues']:
        print("\nQuality issues:")
        for issue in results['quality_issues']:
            print(f"  - {issue}")
    
    # Test regression detection
    recent_events = mock_events[:25]
    historical_events = mock_events[25:]
    
    regression = evaluator.detect_regression(recent_events, historical_events)
    print(f"\nRegression detected: {regression['regression_detected']}")
    if regression['regression_detected']:
        print("Details:")
        for detail in regression['details']:
            print(f"  - {detail}")
