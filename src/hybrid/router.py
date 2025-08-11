import re
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Item:
    id: str
    title: str
    text: str
    url: str | None
    lang: str
    source_trust: float  # 0..1
    risk: float          # 0..1 (topic sensitivity)
    complexity: float    # 0..1 (financial/technical)
    country: str | None

def _contains_critical_topic(text: str, critical: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in critical)

def route(item: Item, cfg) -> Dict[str, Any]:
    """Enhanced routing function with critical flag support"""
    # Drop to validation if very low trust or clear duplicate will be handled elsewhere
    if item.source_trust < cfg["routing"]["min_source_trust_for_llm"]:
        return {"provider": "validate_only", "reason": "low_trust", "critical": False}

    is_finnish = item.lang.lower() in cfg["routing"]["force_gpt5_languages"]
    is_critical_topic = _contains_critical_topic(f"{item.title} {item.text}", cfg["routing"]["critical_topics"])
    is_complex = item.complexity >= cfg["routing"]["complexity_threshold"]
    is_risky = item.risk >= cfg["routing"]["risk_threshold"]

    # Always GPT-5 for Finnish or configured languages (local nuance)
    if is_finnish:
        return {
            "provider": "gpt5_cursor", 
            "reason": "finnish_content", 
            "critical": True,
            "provider_tag": "gpt5_cursor_critical"
        }

    # Critical macro/finance → GPT-5
    if is_critical_topic:
        return {
            "provider": "gpt5_cursor", 
            "reason": "critical_topic", 
            "critical": True,
            "provider_tag": "gpt5_cursor_critical"
        }

    # Complex or risky → GPT-5 (but not critical - can be throttled)
    if is_complex or is_risky:
        return {
            "provider": "gpt5_cursor", 
            "reason": "complex_or_risky", 
            "critical": False,
            "provider_tag": "gpt5_cursor"
        }

    # Default: DeepSeek (volume work)
    return {"provider": "deepseek", "reason": "volume_work", "critical": False}


class SelfLearningRouter:
    """Self-learning router with bandit integration"""
    
    def __init__(self, cfg_path: str = "config/selflearn.yaml"):
        from .bandit import BanditRouter
        from .prompter import PromptTuner
        from .calibrator import BudgetCalibrator
        from .collector import FeedbackCollector, AutoEvaluator
        
        self.bandit_router = BanditRouter(cfg_path)
        self.prompt_tuner = PromptTuner(cfg_path=cfg_path)
        self.budget_calibrator = BudgetCalibrator(cfg_path=cfg_path)
        self.collector = FeedbackCollector()
        self.evaluator = AutoEvaluator()
        
        import yaml
        with open(cfg_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
    
    def route_and_process(self, item: Item) -> Dict[str, Any]:
        """Route item and process with self-learning"""
        
        # Create context for bandit
        context = {
            "lang": item.lang,
            "country": item.country,
            "topic": self._extract_topic(item),
            "source_reputation": item.source_trust,
            "complexity": item.complexity,
            "risk": item.risk
        }
        
        # Get routing decision from bandit
        routing_decision = self.bandit_router.choose(context)
        model = routing_decision["model"]
        
        # Apply budget constraints
        budget_adjusted_model = self._apply_budget_constraints(model, context)
        
        # Get prompt variant
        prompt_template, variant_id = self.prompt_tuner.propose(budget_adjusted_model, context)
        
        # Update routing decision
        routing_decision.update({
            "model": budget_adjusted_model,
            "prompt_variant": variant_id,
            "budget_adjusted": budget_adjusted_model != model
        })
        
        # Process with selected model (placeholder - integrate with actual models)
        output = self._process_with_model(item, budget_adjusted_model, prompt_template)
        
        # Evaluate output
        evaluation = self.evaluator.evaluate_output(output, [item.url] if item.url else [])
        
        # Calculate cost (placeholder)
        cost_data = self._estimate_cost(budget_adjusted_model, item.text, output)
        
        # Log event for learning
        event_id = self.collector.log_event(
            content_id=item.id,
            input_context=context,
            routing_decision=routing_decision,
            output_analysis=evaluation,
            cost_data=cost_data
        )
        
        # Update budget tracking
        self.budget_calibrator.update_spending(budget_adjusted_model, cost_data["eur"])
        
        return {
            "event_id": event_id,
            "routing": routing_decision,
            "output": output,
            "evaluation": evaluation,
            "cost": cost_data
        }
    
    def _extract_topic(self, item: Item) -> str:
        """Extract topic from item"""
        text = f"{item.title} {item.text}".lower()
        
        # Simple keyword-based topic extraction
        if any(word in text for word in ["fed", "federal reserve", "ecb", "keskuspankki"]):
            return "central_banking"
        elif any(word in text for word in ["korko", "interest", "rate"]):
            return "interest_rates"
        elif any(word in text for word in ["tech", "startup", "ai", "teknologia"]):
            return "technology"
        elif any(word in text for word in ["nato", "security", "turvallisuus"]):
            return "security"
        else:
            return "general"
    
    def _apply_budget_constraints(self, model: str, context: Dict[str, Any]) -> str:
        """Apply budget-based routing constraints"""
        try:
            from .budget import hard_cap_hit, should_throttle, daily_hard_cap_hit, should_daily_throttle
        except Exception:
            hard_cap_hit = lambda: False  # type: ignore
            should_throttle = lambda: False  # type: ignore
            daily_hard_cap_hit = lambda: False  # type: ignore
            should_daily_throttle = lambda: False  # type: ignore

        if model == "gpt5":
            if daily_hard_cap_hit():
                return "deepseek"
            if should_daily_throttle():
                is_critical = context.get("lang", "").lower() == "fi" or context.get("topic") in ("central_banking",)
                if not is_critical:
                    return "deepseek"
            if hard_cap_hit():
                return "deepseek"
            if should_throttle():
                # allow critical Finnish content to remain on GPT-5
                is_critical = context.get("lang", "").lower() == "fi" or context.get("topic") in ("central_banking",)
                if not is_critical:
                    return "deepseek"
        return model
    
    def _process_with_model(self, item: Item, model: str, prompt_template: str) -> Dict[str, Any]:
        """Process item with selected model (placeholder)"""
        
        # This would integrate with actual model APIs
        # For now, return mock output
        return {
            "headline": item.title,
            "lede": f"[{model.upper()}] Analysis of: {item.title}",
            "why_it_matters": "This impacts financial markets and policy decisions.",
            "sources": [item.url] if item.url else [],
            "model_used": model,
            "prompt_variant": prompt_template
        }
    
    def _estimate_cost(self, model: str, input_text: str, output: Dict[str, Any]) -> Dict[str, float]:
        """Estimate processing cost"""
        
        # Simple token estimation
        input_tokens = len(input_text.split()) * 1.3
        output_tokens = len(str(output).split()) * 1.3
        
        # Cost per token (approximate)
        if model == "deepseek":
            cost_per_1k = 0.0012  # DeepSeek pricing
        else:  # gpt5
            cost_per_1k = 0.02   # GPT-5 pricing
        
        total_cost = (input_tokens + output_tokens) / 1000 * cost_per_1k
        
        return {
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "eur": total_cost
        }
    
    def add_user_feedback(self, event_id: str, feedback: Dict[str, Any]):
        """Add user feedback to existing event"""
        self.collector.append_feedback(event_id, "user", feedback)
        
        # TODO: Update bandit with feedback for real-time learning
    
    def add_editor_feedback(self, event_id: str, feedback: Dict[str, Any]):
        """Add editor feedback to existing event"""
        self.collector.append_feedback(event_id, "editor", feedback)
