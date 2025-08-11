#!/usr/bin/env python3
"""
Budget calibration and cost management
Automatically adjusts routing to stay within budget constraints
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import yaml
import numpy as np


class BudgetCalibrator:
    """Manages budget constraints and adjusts routing accordingly"""
    
    def __init__(self, state_dir: str = "artifacts/selflearn", cfg_path: str = "config/selflearn.yaml"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        with open(cfg_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        self.calibration_cfg = self.cfg['calibration']
        self.target_budget = self.calibration_cfg['target_budget_eur_month']
        self.soft_cap = self.calibration_cfg['soft_cap']
        self.hard_cap = self.calibration_cfg['hard_cap']
        
        # State files
        self.budget_state_file = self.state_dir / "budget_state.json"
        self.routing_adjustments_file = self.state_dir / "routing_adjustments.json"
        
        # Load state
        self.budget_state = self._load_budget_state()
        self.routing_adjustments = self._load_routing_adjustments()
    
    def _load_budget_state(self) -> Dict[str, Any]:
        """Load current budget state"""
        if self.budget_state_file.exists():
            try:
                with open(self.budget_state_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "current_month": datetime.now().strftime("%Y-%m"),
            "deepseek_spent": 0.0,
            "gpt5_spent": 0.0,
            "total_spent": 0.0,
            "daily_spending": {},
            "last_reset": str(datetime.now().date()),
            "spending_rate_eur_per_day": 0.0
        }
    
    def _load_routing_adjustments(self) -> Dict[str, Any]:
        """Load current routing adjustments"""
        if self.routing_adjustments_file.exists():
            try:
                with open(self.routing_adjustments_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "gpt5_usage_multiplier": 1.0,  # 1.0 = normal, <1.0 = reduce GPT-5
            "validation_only_segments": [],  # Segments forced to validation only
            "frozen_mode": False,  # Stop all experimentation
            "emergency_mode": False,  # Hard budget cap triggered
            "last_adjustment": None,
            "adjustment_reason": None
        }
    
    def _save_budget_state(self):
        """Save budget state to disk"""
        with open(self.budget_state_file, 'w') as f:
            json.dump(self.budget_state, f, indent=2)
    
    def _save_routing_adjustments(self):
        """Save routing adjustments to disk"""
        with open(self.routing_adjustments_file, 'w') as f:
            json.dump(self.routing_adjustments, f, indent=2)
    
    def update_spending(self, model: str, cost_eur: float):
        """Update spending tracking"""
        current_month = datetime.now().strftime("%Y-%m")
        
        # Reset if new month
        if self.budget_state["current_month"] != current_month:
            self._reset_monthly_budget()
        
        # Update totals
        if model == "deepseek":
            self.budget_state["deepseek_spent"] += cost_eur
        elif model == "gpt5":
            self.budget_state["gpt5_spent"] += cost_eur
        
        self.budget_state["total_spent"] += cost_eur
        
        # Update daily tracking
        today = str(datetime.now().date())
        if today not in self.budget_state["daily_spending"]:
            self.budget_state["daily_spending"][today] = 0.0
        self.budget_state["daily_spending"][today] += cost_eur
        
        # Update spending rate
        self._update_spending_rate()
        
        self._save_budget_state()
    
    def _reset_monthly_budget(self):
        """Reset budget for new month"""
        self.budget_state = {
            "current_month": datetime.now().strftime("%Y-%m"),
            "deepseek_spent": 0.0,
            "gpt5_spent": 0.0,
            "total_spent": 0.0,
            "daily_spending": {},
            "last_reset": str(datetime.now().date()),
            "spending_rate_eur_per_day": 0.0
        }
        
        # Reset routing adjustments for new month
        self.routing_adjustments = {
            "gpt5_usage_multiplier": 1.0,
            "validation_only_segments": [],
            "frozen_mode": False,
            "emergency_mode": False,
            "last_adjustment": None,
            "adjustment_reason": None
        }
        
        self._save_budget_state()
        self._save_routing_adjustments()
    
    def _update_spending_rate(self):
        """Calculate current spending rate"""
        daily_spending = self.budget_state["daily_spending"]
        
        if not daily_spending:
            self.budget_state["spending_rate_eur_per_day"] = 0.0
            return
        
        # Calculate average over last 7 days
        recent_days = sorted(daily_spending.keys())[-7:]
        recent_spending = [daily_spending[day] for day in recent_days]
        
        self.budget_state["spending_rate_eur_per_day"] = np.mean(recent_spending)
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status"""
        total_spent = self.budget_state["total_spent"]
        utilization = total_spent / self.target_budget
        
        # Project end-of-month spending
        days_in_month = 30  # Approximate
        day_of_month = datetime.now().day
        remaining_days = days_in_month - day_of_month
        
        projected_spending = total_spent + (self.budget_state["spending_rate_eur_per_day"] * remaining_days)
        projected_utilization = projected_spending / self.target_budget
        
        return {
            "current_spending": {
                "deepseek": self.budget_state["deepseek_spent"],
                "gpt5": self.budget_state["gpt5_spent"],
                "total": total_spent
            },
            "budget": {
                "target": self.target_budget,
                "utilization": utilization,
                "remaining": max(0, self.target_budget - total_spent)
            },
            "projections": {
                "end_of_month_spending": projected_spending,
                "end_of_month_utilization": projected_utilization,
                "daily_rate": self.budget_state["spending_rate_eur_per_day"]
            },
            "thresholds": {
                "soft_cap_triggered": utilization >= self.soft_cap,
                "hard_cap_triggered": utilization >= self.hard_cap,
                "projected_over_budget": projected_utilization > 1.0
            },
            "routing_adjustments": self.routing_adjustments
        }
    
    def calibrate_routing(self) -> Dict[str, Any]:
        """Adjust routing based on budget status"""
        status = self.get_budget_status()
        adjustments_made = []
        
        # Check if adjustments needed
        if status["thresholds"]["hard_cap_triggered"]:
            # Emergency mode: only validation
            if not self.routing_adjustments["emergency_mode"]:
                self.routing_adjustments["emergency_mode"] = True
                self.routing_adjustments["gpt5_usage_multiplier"] = 0.1
                self.routing_adjustments["frozen_mode"] = True
                adjustments_made.append("EMERGENCY: Hard cap reached, minimal GPT-5 usage")
        
        elif status["thresholds"]["soft_cap_triggered"] or status["thresholds"]["projected_over_budget"]:
            # Soft cap: reduce GPT-5 usage
            current_multiplier = self.routing_adjustments["gpt5_usage_multiplier"]
            
            if status["projections"]["end_of_month_utilization"] > 1.2:
                # Aggressive reduction
                new_multiplier = max(0.3, current_multiplier * 0.7)
                adjustments_made.append(f"Aggressive GPT-5 reduction: {current_multiplier:.2f} → {new_multiplier:.2f}")
            elif status["projections"]["end_of_month_utilization"] > 1.1:
                # Moderate reduction
                new_multiplier = max(0.5, current_multiplier * 0.8)
                adjustments_made.append(f"Moderate GPT-5 reduction: {current_multiplier:.2f} → {new_multiplier:.2f}")
            else:
                # Light reduction
                new_multiplier = max(0.7, current_multiplier * 0.9)
                adjustments_made.append(f"Light GPT-5 reduction: {current_multiplier:.2f} → {new_multiplier:.2f}")
            
            self.routing_adjustments["gpt5_usage_multiplier"] = new_multiplier
            
            # Consider frozen mode for extreme cases
            if status["projections"]["end_of_month_utilization"] > 1.3:
                self.routing_adjustments["frozen_mode"] = True
                adjustments_made.append("Frozen mode: No prompt experimentation")
        
        else:
            # Under budget: can relax restrictions
            if self.routing_adjustments["emergency_mode"]:
                self.routing_adjustments["emergency_mode"] = False
                self.routing_adjustments["gpt5_usage_multiplier"] = 0.8
                adjustments_made.append("Exited emergency mode")
            
            elif self.routing_adjustments["gpt5_usage_multiplier"] < 1.0:
                # Gradually restore GPT-5 usage
                current_multiplier = self.routing_adjustments["gpt5_usage_multiplier"]
                new_multiplier = min(1.0, current_multiplier * 1.1)
                self.routing_adjustments["gpt5_usage_multiplier"] = new_multiplier
                adjustments_made.append(f"Restored GPT-5 usage: {current_multiplier:.2f} → {new_multiplier:.2f}")
            
            if self.routing_adjustments["frozen_mode"] and status["budget"]["utilization"] < 0.8:
                self.routing_adjustments["frozen_mode"] = False
                adjustments_made.append("Unfroze experimentation")
        
        # Update adjustment metadata
        if adjustments_made:
            self.routing_adjustments["last_adjustment"] = datetime.now().isoformat()
            self.routing_adjustments["adjustment_reason"] = adjustments_made
            self._save_routing_adjustments()
        
        return {
            "adjustments_made": adjustments_made,
            "routing_config": self.routing_adjustments,
            "budget_status": status
        }
    
    def should_use_gpt5(self, base_decision: bool, context: Dict[str, Any]) -> bool:
        """Apply budget-based routing adjustments"""
        
        # Emergency mode: minimal GPT-5
        if self.routing_adjustments["emergency_mode"]:
            # Only for critical Finnish content
            if context.get("lang") == "fi" and context.get("complexity", 0) > 0.8:
                return True
            return False
        
        # Apply multiplier
        if base_decision:
            multiplier = self.routing_adjustments["gpt5_usage_multiplier"]
            return np.random.random() < multiplier
        
        return base_decision
    
    def should_experiment(self, base_decision: bool) -> bool:
        """Apply experimentation restrictions"""
        if self.routing_adjustments["frozen_mode"]:
            return False
        return base_decision
    
    def get_cost_forecast(self, days_ahead: int = 7) -> Dict[str, float]:
        """Forecast spending for next N days"""
        daily_rate = self.budget_state["spending_rate_eur_per_day"]
        
        return {
            f"forecast_{days_ahead}_days": daily_rate * days_ahead,
            "daily_rate": daily_rate,
            "monthly_projection": daily_rate * 30,
            "budget_remaining": max(0, self.target_budget - self.budget_state["total_spent"])
        }


class CostController:
    """Simple wrapper for budget calibration"""
    
    def __init__(self, cfg_path: str = "config/selflearn.yaml"):
        self.calibrator = BudgetCalibrator(cfg_path=cfg_path)
    
    def record_cost(self, model: str, cost_eur: float):
        """Record a cost event"""
        self.calibrator.update_spending(model, cost_eur)
    
    def daily_calibration(self) -> Dict[str, Any]:
        """Run daily budget calibration"""
        return self.calibrator.calibrate_routing()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current budget and routing status"""
        return self.calibrator.get_budget_status()


if __name__ == "__main__":
    # Test calibrator
    controller = CostController()
    
    # Simulate some spending
    print("Simulating spending...")
    for i in range(20):
        model = "gpt5" if i % 3 == 0 else "deepseek"
        cost = 0.05 if model == "gpt5" else 0.01
        controller.record_cost(model, cost)
    
    # Check status
    status = controller.get_status()
    print("\nBudget Status:")
    print(f"Total spent: €{status['current_spending']['total']:.3f}")
    print(f"Budget utilization: {status['budget']['utilization']*100:.1f}%")
    print(f"Projected end-of-month: €{status['projections']['end_of_month_spending']:.2f}")
    
    # Run calibration
    print("\nRunning calibration...")
    calibration = controller.daily_calibration()
    
    if calibration["adjustments_made"]:
        print("Adjustments made:")
        for adj in calibration["adjustments_made"]:
            print(f"  - {adj}")
    else:
        print("No adjustments needed")
    
    print(f"\nGPT-5 usage multiplier: {calibration['routing_config']['gpt5_usage_multiplier']:.2f}")
    print(f"Frozen mode: {calibration['routing_config']['frozen_mode']}")
    print(f"Emergency mode: {calibration['routing_config']['emergency_mode']}")
