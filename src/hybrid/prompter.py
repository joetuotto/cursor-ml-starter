#!/usr/bin/env python3
"""
Prompt optimization using Bayesian optimization and A/B testing
Automatically improves prompt variants based on performance
"""

import json
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import yaml
import numpy as np


class PromptVariant:
    """Single prompt variant with performance tracking"""
    
    def __init__(self, variant_id: str, template: str, model: str):
        self.variant_id = variant_id
        self.template = template
        self.model = model
        self.trials = 0
        self.successes = 0
        self.total_score = 0.0
        self.created_at = str(np.datetime64('now'))
    
    def record_result(self, success: bool, score: float):
        """Record a trial result"""
        self.trials += 1
        if success:
            self.successes += 1
        self.total_score += score
    
    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.trials)
    
    @property
    def avg_score(self) -> float:
        return self.total_score / max(1, self.trials)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "template": self.template,
            "model": self.model,
            "trials": self.trials,
            "successes": self.successes,
            "success_rate": self.success_rate,
            "avg_score": self.avg_score,
            "created_at": self.created_at
        }


class PromptTuner:
    """Bayesian optimization for prompt variants"""
    
    def __init__(self, state_dir: str = "artifacts/selflearn", cfg_path: str = "config/selflearn.yaml"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load config
        with open(cfg_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        self.method = self.cfg['prompt_tuning']['method']
        self.variants_per_model = self.cfg['prompt_tuning']['variants_per_model']
        self.budget_share = self.cfg['prompt_tuning']['budget_share']
        
        # Base templates
        self.base_templates = {
            "deepseek": {
                "fi": "Analysoi tämä suomalainen uutinen: {title}. Anna tarkka ja objektiivinen analyysi.",
                "en": "Analyze this news: {title}. Provide objective, fact-based analysis."
            },
            "gpt5": {
                "fi": "Syvällinen analyysi suomalaisesta näkökulmasta: {title}. Sisällytä konkreettiset vaikutukset.",
                "en": "Deep analysis with specific impacts: {title}. Include concrete implications and evidence."
            }
        }
        
        # State management
        self.state_file = self.state_dir / "prompt_variants.json"
        self.variants = self._load_variants()
    
    def _load_variants(self) -> Dict[str, List[PromptVariant]]:
        """Load existing prompt variants"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                variants = defaultdict(list)
                for model, model_variants in data.items():
                    for variant_data in model_variants:
                        variant = PromptVariant(
                            variant_data["variant_id"],
                            variant_data["template"], 
                            variant_data["model"]
                        )
                        variant.trials = variant_data["trials"]
                        variant.successes = variant_data["successes"]
                        variant.total_score = variant_data.get("total_score", 0.0)
                        variants[model].append(variant)
                
                return dict(variants)
            except Exception as e:
                print(f"Error loading prompt variants: {e}")
        
        # Initialize with base variants
        return self._create_initial_variants()
    
    def _create_initial_variants(self) -> Dict[str, List[PromptVariant]]:
        """Create initial prompt variants for each model"""
        variants = defaultdict(list)
        
        for model in ["deepseek", "gpt5"]:
            # Base variant
            for lang in ["fi", "en"]:
                base_template = self.base_templates[model][lang]
                variant_id = f"{model}_{lang}_base"
                variants[model].append(PromptVariant(variant_id, base_template, model))
            
            # Generate additional variants using mutations
            for i in range(self.variants_per_model - 1):
                variant = self._generate_variant(model, i + 1)
                variants[model].append(variant)
        
        return dict(variants)
    
    def _generate_variant(self, model: str, variant_num: int) -> PromptVariant:
        """Generate a new prompt variant using mutation strategies"""
        
        # Different mutation strategies
        mutations = {
            "deepseek": {
                "fi": [
                    "Analysoi huolellisesti tämä uutinen: {title}. Keskity faktoihin ja vaikutuksiin.",
                    "Tarkastele kriittisesti: {title}. Anna perusteltu arvio merkityksestä.",
                    "Uutisanalyysi: {title}. Korosta konkreettiset seuraukset ja syy-seuraussuhteet."
                ],
                "en": [
                    "Critically examine: {title}. Focus on evidence and concrete impacts.",
                    "News analysis: {title}. Emphasize factual assessment and implications.",
                    "Evaluate thoroughly: {title}. Provide data-driven perspective with context."
                ]
            },
            "gpt5": {
                "fi": [
                    "Eksperttianalyysi: {title}. Sisällytä Suomen markkinoiden erityispiirteet ja kvantitatiiviset vaikutukset.",
                    "Strateginen arvio: {title}. Analysoi pitkän aikavälin seuraukset ja toimenpidesuositukset.",
                    "Monipuolinen tarkastelu: {title}. Yhdistä makrotaloudellinen ja mikrotaloudellinen näkökulma."
                ],
                "en": [
                    "Expert analysis: {title}. Include quantitative impacts and strategic implications.",
                    "Comprehensive assessment: {title}. Integrate macro and micro perspectives with evidence.",
                    "Professional evaluation: {title}. Emphasize actionable insights and risk assessment."
                ]
            }
        }
        
        # Select language based on variant number
        lang = "fi" if variant_num % 2 == 1 else "en"
        
        # Select template from mutations
        templates = mutations[model][lang]
        template = templates[variant_num % len(templates)]
        
        variant_id = f"{model}_{lang}_v{variant_num}"
        return PromptVariant(variant_id, template, model)
    
    def _save_variants(self):
        """Save variants to disk"""
        data = {}
        for model, model_variants in self.variants.items():
            data[model] = [variant.to_dict() for variant in model_variants]
        
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def propose(self, model: str, context: Dict[str, Any]) -> Tuple[str, str]:
        """Propose prompt variant for given model and context"""
        
        if model not in self.variants or not self.variants[model]:
            # Fallback to base template
            lang = context.get('lang', 'en')
            template = self.base_templates.get(model, {}).get(lang, "Analyze: {title}")
            return template, f"{model}_fallback"
        
        variants = self.variants[model]
        
        # Check if we should explore (budget_share portion)
        if random.random() < self.budget_share:
            # Exploration: choose based on uncertainty
            variant = self._choose_exploration(variants)
        else:
            # Exploitation: choose best performing
            variant = self._choose_exploitation(variants)
        
        return variant.template, variant.variant_id
    
    def _choose_exploration(self, variants: List[PromptVariant]) -> PromptVariant:
        """Choose variant for exploration (high uncertainty)"""
        # Thompson sampling: prefer variants with high uncertainty
        candidates = []
        
        for variant in variants:
            if variant.trials < 10:  # Low sample size = high uncertainty
                uncertainty = 1.0 / max(1, variant.trials)
                candidates.append((variant, uncertainty))
        
        if not candidates:
            # All variants well-tested, choose randomly
            return random.choice(variants)
        
        # Weighted random selection by uncertainty
        weights = [weight for _, weight in candidates]
        total_weight = sum(weights)
        
        r = random.random() * total_weight
        cumsum = 0
        for variant, weight in candidates:
            cumsum += weight
            if r <= cumsum:
                return variant
        
        return candidates[-1][0]  # Fallback
    
    def _choose_exploitation(self, variants: List[PromptVariant]) -> PromptVariant:
        """Choose best performing variant"""
        if not variants:
            return None
        
        # Sort by average score (with minimum trials threshold)
        viable_variants = [v for v in variants if v.trials >= 5]
        
        if not viable_variants:
            # Not enough data, return random
            return random.choice(variants)
        
        return max(viable_variants, key=lambda v: v.avg_score)
    
    def record(self, model: str, variant_id: str, metrics: Dict[str, float]):
        """Record performance for a prompt variant"""
        
        if model not in self.variants:
            return
        
        # Find the variant
        variant = None
        for v in self.variants[model]:
            if v.variant_id == variant_id:
                variant = v
                break
        
        if variant is None:
            return
        
        # Calculate success and score
        success = (
            metrics.get('schema_ok', 0) > 0.5 and
            metrics.get('editor_accepted', 0) > 0.5 and
            metrics.get('hallu_score', 1.0) < 0.1
        )
        
        score = (
            0.4 * metrics.get('editor_accepted', 0) +
            0.3 * metrics.get('user_engagement', 0) +
            0.2 * metrics.get('schema_ok', 0) +
            0.1 * (1.0 - metrics.get('hallu_score', 0))
        )
        
        variant.record_result(success, score)
        self._save_variants()
    
    def best(self, model: str, context: Dict[str, Any]) -> str:
        """Get best performing prompt for model and context"""
        template, _ = self.propose(model, context)
        return template
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get prompt tuning statistics"""
        stats = {
            "total_variants": sum(len(variants) for variants in self.variants.values()),
            "model_stats": {}
        }
        
        for model, variants in self.variants.items():
            model_stats = {
                "variant_count": len(variants),
                "total_trials": sum(v.trials for v in variants),
                "best_variant": None,
                "variants": []
            }
            
            if variants:
                # Find best variant
                tested_variants = [v for v in variants if v.trials >= 5]
                if tested_variants:
                    best = max(tested_variants, key=lambda v: v.avg_score)
                    model_stats["best_variant"] = {
                        "variant_id": best.variant_id,
                        "success_rate": best.success_rate,
                        "avg_score": best.avg_score,
                        "trials": best.trials
                    }
                
                # All variants summary
                model_stats["variants"] = [v.to_dict() for v in variants]
            
            stats["model_stats"][model] = model_stats
        
        return stats


if __name__ == "__main__":
    # Test prompt tuner
    tuner = PromptTuner()
    
    # Test proposal
    context = {"lang": "fi", "topic": "economics"}
    
    for model in ["deepseek", "gpt5"]:
        template, variant_id = tuner.propose(model, context)
        print(f"\n{model.upper()} - {variant_id}:")
        print(f"Template: {template}")
        
        # Simulate feedback
        mock_metrics = {
            "schema_ok": 1.0,
            "editor_accepted": 0.8,
            "user_engagement": 0.7,
            "hallu_score": 0.02
        }
        tuner.record(model, variant_id, mock_metrics)
    
    print("\n" + "="*50)
    print("Statistics:")
    stats = tuner.get_statistics()
    for model, model_stats in stats["model_stats"].items():
        print(f"\n{model}: {model_stats['variant_count']} variants, {model_stats['total_trials']} trials")
        if model_stats["best_variant"]:
            best = model_stats["best_variant"]
            print(f"  Best: {best['variant_id']} (score: {best['avg_score']:.3f}, trials: {best['trials']})")
