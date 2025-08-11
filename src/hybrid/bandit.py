#!/usr/bin/env python3
"""
Contextual bandit for intelligent model routing
Uses Thompson Sampling or UCB for exploration/exploitation
"""

import json
import math
import random
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
import yaml


class ContextualBandit:
    """Thompson Sampling contextual bandit for model selection"""
    
    def __init__(self, state_dir: str = "artifacts/selflearn", cfg_path: str = "config/selflearn.yaml"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load config
        with open(cfg_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        self.algorithm = self.cfg['routing']['algorithm']
        self.features = self.cfg['routing']['features']
        self.cost_weight = self.cfg['routing']['cost_weight']
        self.quality_weight = self.cfg['routing']['quality_weight']
        
        # Model options
        self.models = ['deepseek', 'gpt5']
        
        # State: Beta distributions for each context-model pair
        self.state_file = self.state_dir / "bandit_state.json"
        self.state = self._load_state()
        
        # Cold start rules
        self.cold_start_topics = self.cfg['routing']['cold_start_gpt5_topics']
    
    def _load_state(self) -> Dict[str, Any]:
        """Load bandit state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading bandit state: {e}")
        
        # Initialize empty state
        return {
            "context_stats": defaultdict(lambda: {
                "deepseek": {"alpha": 1.0, "beta": 1.0, "count": 0, "total_reward": 0.0},
                "gpt5": {"alpha": 1.0, "beta": 1.0, "count": 0, "total_reward": 0.0}
            }),
            "global_stats": {
                "total_events": 0,
                "last_update": None
            }
        }
    
    def _save_state(self):
        """Save bandit state to disk"""
        # Convert defaultdict to regular dict for JSON serialization
        state_copy = {
            "context_stats": dict(self.state["context_stats"]),
            "global_stats": self.state["global_stats"]
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state_copy, f, indent=2)
    
    def _contextualize(self, context: Dict[str, Any]) -> str:
        """Convert context to string key for state tracking"""
        # Create simplified context key from selected features
        key_parts = []
        for feature in self.features:
            if feature in context:
                value = context[feature]
                if isinstance(value, float):
                    # Bin continuous values
                    if feature == "complexity":
                        value = "high" if value > 0.6 else "med" if value > 0.3 else "low"
                    elif feature == "source_reputation":
                        value = "trusted" if value > 0.7 else "medium" if value > 0.4 else "low"
                key_parts.append(f"{feature}:{value}")
        
        return "|".join(key_parts)
    
    def choose(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Choose model based on context using bandit algorithm"""
        
        # Check cold start rules first
        topic = context.get('topic', '')
        lang = context.get('lang', '')
        country = context.get('country', '')
        
        for cold_start_rule in self.cold_start_topics:
            if self._matches_cold_start(cold_start_rule, lang, country, topic):
                return {
                    "model": "gpt5",
                    "reason": f"cold_start:{cold_start_rule}",
                    "explore": False
                }
        
        # Get context key
        context_key = self._contextualize(context)
        
        # Get stats for this context
        if context_key not in self.state["context_stats"]:
            self.state["context_stats"][context_key] = {
                "deepseek": {"alpha": 1.0, "beta": 1.0, "count": 0, "total_reward": 0.0},
                "gpt5": {"alpha": 1.0, "beta": 1.0, "count": 0, "total_reward": 0.0}
            }
        
        stats = self.state["context_stats"][context_key]
        
        # Choose based on algorithm
        if self.algorithm == "thompson":
            model = self._thompson_sampling(stats)
        else:  # UCB
            model = self._ucb_selection(stats)
        
        is_explore = self._is_exploration_choice(stats, model)
        
        return {
            "model": model,
            "reason": f"{self.algorithm}:{context_key}",
            "explore": is_explore
        }
    
    def _matches_cold_start(self, rule: str, lang: str, country: str, topic: str) -> bool:
        """Check if context matches cold start rule"""
        if rule == "FI/*":
            return lang == "fi" or country == "FI"
        elif rule in ["ECB", "Fed", "NatSec"]:
            return rule.lower() in topic.lower()
        return False
    
    def _thompson_sampling(self, stats: Dict[str, Dict[str, float]]) -> str:
        """Thompson sampling: sample from posterior Beta distributions"""
        samples = {}
        
        for model in self.models:
            alpha = stats[model]["alpha"]
            beta = stats[model]["beta"]
            # Sample from Beta(alpha, beta)
            samples[model] = np.random.beta(alpha, beta)
        
        return max(samples, key=samples.get)
    
    def _ucb_selection(self, stats: Dict[str, Dict[str, float]]) -> str:
        """Upper Confidence Bound selection"""
        total_count = sum(stats[model]["count"] for model in self.models)
        
        if total_count == 0:
            return random.choice(self.models)
        
        ucb_values = {}
        
        for model in self.models:
            count = stats[model]["count"]
            if count == 0:
                ucb_values[model] = float('inf')  # Unvisited arm
            else:
                avg_reward = stats[model]["total_reward"] / count
                confidence = math.sqrt(2 * math.log(total_count) / count)
                ucb_values[model] = avg_reward + confidence
        
        return max(ucb_values, key=ucb_values.get)
    
    def _is_exploration_choice(self, stats: Dict[str, Dict[str, float]], chosen_model: str) -> bool:
        """Determine if this choice is exploration vs exploitation"""
        # Simple heuristic: if chosen model has less than 50% of total trials in this context
        total_count = sum(stats[model]["count"] for model in self.models)
        if total_count < 10:
            return True
        
        chosen_count = stats[chosen_model]["count"]
        return chosen_count / total_count < 0.5
    
    def update(self, context: Dict[str, Any], model: str, reward: float):
        """Update bandit state with observed reward"""
        context_key = self._contextualize(context)
        
        if context_key not in self.state["context_stats"]:
            self.state["context_stats"][context_key] = {
                "deepseek": {"alpha": 1.0, "beta": 1.0, "count": 0, "total_reward": 0.0},
                "gpt5": {"alpha": 1.0, "beta": 1.0, "count": 0, "total_reward": 0.0}
            }
        
        stats = self.state["context_stats"][context_key][model]
        
        # Update Beta distribution parameters
        if reward > 0.5:  # Success
            stats["alpha"] += reward
        else:  # Failure
            stats["beta"] += (1.0 - reward)
        
        # Update counts and totals
        stats["count"] += 1
        stats["total_reward"] += reward
        
        # Update global stats
        self.state["global_stats"]["total_events"] += 1
        self.state["global_stats"]["last_update"] = str(np.datetime64('now'))
        
        self._save_state()
    
    def calculate_reward(self, quality_metrics: Dict[str, float], cost_eur: float) -> float:
        """Calculate reward from quality metrics and cost"""
        
        # Quality score (0-1)
        quality_score = (
            0.4 * quality_metrics.get('editor_accepted', 0.0) +
            0.3 * quality_metrics.get('user_engagement', 0.0) +
            0.2 * quality_metrics.get('schema_ok', 0.0) +
            0.1 * quality_metrics.get('ref_quality', 0.0)
        )
        
        # Penalties
        hallu_penalty = quality_metrics.get('hallu_score', 0.0)
        ref_miss_penalty = quality_metrics.get('ref_miss_rate', 0.0)
        
        quality_score = max(0.0, quality_score - hallu_penalty - ref_miss_penalty)
        
        # Normalize cost (assume €0.05 is high cost)
        normalized_cost = min(1.0, cost_eur / 0.05)
        
        # Combined reward
        reward = (
            self.quality_weight * quality_score - 
            self.cost_weight * normalized_cost
        )
        
        return max(0.0, min(1.0, reward))  # Clamp to [0,1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bandit performance statistics"""
        stats = {
            "total_events": self.state["global_stats"]["total_events"],
            "context_count": len(self.state["context_stats"]),
            "model_performance": defaultdict(lambda: {"count": 0, "avg_reward": 0.0})
        }
        
        for context_key, context_stats in self.state["context_stats"].items():
            for model, model_stats in context_stats.items():
                if model_stats["count"] > 0:
                    stats["model_performance"][model]["count"] += model_stats["count"]
                    avg_reward = model_stats["total_reward"] / model_stats["count"]
                    stats["model_performance"][model]["avg_reward"] = avg_reward
        
        return dict(stats)


class BanditRouter:
    """Simple wrapper for the contextual bandit"""
    
    def __init__(self, cfg_path: str = "config/selflearn.yaml"):
        self.bandit = ContextualBandit(cfg_path=cfg_path)
    
    def choose(self, context: Dict[str, Any]) -> Dict[str, str]:
        return self.bandit.choose(context)
    
    def update(self, context: Dict[str, Any], model: str, quality_metrics: Dict[str, float], cost_eur: float):
        reward = self.bandit.calculate_reward(quality_metrics, cost_eur)
        self.bandit.update(context, model, reward)


if __name__ == "__main__":
    # Test the bandit
    router = BanditRouter()
    
    # Test contexts
    test_contexts = [
        {"lang": "fi", "country": "FI", "topic": "ECB", "complexity": 0.7, "source_reputation": 0.8},
        {"lang": "en", "country": "US", "topic": "tech", "complexity": 0.3, "source_reputation": 0.6},
        {"lang": "en", "country": "EU", "topic": "Fed", "complexity": 0.8, "source_reputation": 0.9}
    ]
    
    for i, context in enumerate(test_contexts):
        choice = router.choose(context)
        print(f"Context {i+1}: {context}")
        print(f"Choice: {choice}")
        
        # Simulate feedback
        mock_quality = {
            "editor_accepted": 0.8,
            "user_engagement": 0.6,
            "schema_ok": 1.0,
            "ref_quality": 0.7,
            "hallu_score": 0.02,
            "ref_miss_rate": 0.1
        }
        router.update(context, choice["model"], mock_quality, 0.025)
        print()
    
    print("Statistics:", router.bandit.get_statistics())
