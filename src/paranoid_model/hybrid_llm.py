#!/usr/bin/env python3
"""
Hybrid LLM system for PARANOID: DeepSeek + GPT-5
Budget-optimized architecture: €30/month
"""

import json
import os
import time
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal
from enum import Enum

import requests


class ModelProvider(Enum):
    DEEPSEEK = "deepseek"
    GPT5 = "gpt5"
    CURSOR = "cursor"


@dataclass
class ModelConfig:
    """Model configuration with cost tracking"""
    provider: ModelProvider
    model_name: str
    cost_per_input_token: float  # USD per 1M tokens
    cost_per_output_token: float  # USD per 1M tokens
    max_tokens: int = 2000
    temperature: float = 0.3
    monthly_budget_usd: float = 0.0


# Cost-optimized model configurations
MODELS = {
    ModelProvider.DEEPSEEK: ModelConfig(
        provider=ModelProvider.DEEPSEEK,
        model_name="deepseek-r1",
        cost_per_input_token=0.55,   # $0.55/1M tokens
        cost_per_output_token=2.19,  # $2.19/1M tokens  
        max_tokens=1500,
        monthly_budget_usd=22.0      # €20 ≈ $22
    ),
    ModelProvider.GPT5: ModelConfig(
        provider=ModelProvider.GPT5,
        model_name="gpt-5",
        cost_per_input_token=1.25,   # $1.25/1M tokens
        cost_per_output_token=10.0,  # $10.0/1M tokens
        max_tokens=2500,
        monthly_budget_usd=11.0      # €10 ≈ $11
    )
}


class CostTracker:
    """Track API costs and enforce budget limits"""
    
    def __init__(self, budget_file: str = "artifacts/monthly_budget.json"):
        self.budget_file = budget_file
        self.load_usage()
    
    def load_usage(self):
        """Load current month usage"""
        try:
            with open(self.budget_file, 'r') as f:
                data = json.load(f)
                current_month = time.strftime("%Y-%m")
                if data.get('month') == current_month:
                    self.usage = data.get('usage', {})
                else:
                    self.usage = {}  # New month, reset
        except FileNotFoundError:
            self.usage = {}
    
    def save_usage(self):
        """Save usage to file"""
        os.makedirs(os.path.dirname(self.budget_file), exist_ok=True)
        data = {
            'month': time.strftime("%Y-%m"),
            'usage': self.usage,
            'updated_at': time.time()
        }
        with open(self.budget_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_usage(self, provider: ModelProvider, input_tokens: int, output_tokens: int):
        """Record token usage and cost"""
        config = MODELS[provider]
        cost = (input_tokens * config.cost_per_input_token / 1_000_000 + 
                output_tokens * config.cost_per_output_token / 1_000_000)
        
        provider_key = provider.value
        if provider_key not in self.usage:
            self.usage[provider_key] = {'cost': 0, 'input_tokens': 0, 'output_tokens': 0}
        
        self.usage[provider_key]['cost'] += cost
        self.usage[provider_key]['input_tokens'] += input_tokens
        self.usage[provider_key]['output_tokens'] += output_tokens
        
        self.save_usage()
        return cost
    
    def can_afford(self, provider: ModelProvider, estimated_tokens: int) -> bool:
        """Check if we can afford the request"""
        config = MODELS[provider]
        estimated_cost = estimated_tokens * config.cost_per_output_token / 1_000_000
        current_cost = self.usage.get(provider.value, {}).get('cost', 0)
        
        return (current_cost + estimated_cost) <= config.monthly_budget_usd
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary"""
        summary = {'total_cost': 0, 'providers': {}}
        
        for provider, config in MODELS.items():
            usage = self.usage.get(provider.value, {})
            cost = usage.get('cost', 0)
            remaining = max(0, config.monthly_budget_usd - cost)
            
            summary['providers'][provider.value] = {
                'cost': cost,
                'budget': config.monthly_budget_usd,
                'remaining': remaining,
                'utilization': cost / config.monthly_budget_usd if config.monthly_budget_usd > 0 else 0
            }
            summary['total_cost'] += cost
        
        return summary


class ContentRouter:
    """Intelligent routing between DeepSeek and GPT-5"""
    
    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
    
    def route_content(self, signal: Dict[str, Any]) -> ModelProvider:
        """Route content to appropriate model based on complexity and budget"""
        
        # Critical content always goes to GPT-5 (if budget allows)
        if self._is_critical_content(signal):
            if self.cost_tracker.can_afford(ModelProvider.GPT5, 2000):
                return ModelProvider.GPT5
        
        # Finnish content preferentially to GPT-5 (better localization)
        if signal.get('origin_country') == 'FI':
            if self.cost_tracker.can_afford(ModelProvider.GPT5, 1500):
                return ModelProvider.GPT5
        
        # Complex financial content to GPT-5
        if self._is_complex_financial(signal):
            if self.cost_tracker.can_afford(ModelProvider.GPT5, 1800):
                return ModelProvider.GPT5
        
        # Default to DeepSeek for volume work
        if self.cost_tracker.can_afford(ModelProvider.DEEPSEEK, 1500):
            return ModelProvider.DEEPSEEK
        
        # If both models are over budget, use emergency GPT-5
        return ModelProvider.GPT5
    
    def _is_critical_content(self, signal: Dict[str, Any]) -> bool:
        """Detect critical content requiring premium model"""
        title = signal.get('title', '').lower()
        critical_keywords = [
            'federal reserve', 'ecb', 'suomen pankki', 'interest rate',
            'recession', 'crisis', 'bankruptcy', 'korko', 'inflaatio'
        ]
        return any(keyword in title for keyword in critical_keywords)
    
    def _is_complex_financial(self, signal: Dict[str, Any]) -> bool:
        """Detect complex financial content"""
        category = signal.get('category_guess', '').lower()
        complex_categories = ['talous', 'finance', 'yritykset', 'markkinat']
        
        # Check for quantitative content
        title_summary = f"{signal.get('title', '')} {signal.get('summary_raw', '')}"
        has_numbers = any(char.isdigit() for char in title_summary)
        
        return category in complex_categories and has_numbers


class DeepSeekClient:
    """DeepSeek API client"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
    
    def generate(self, system: str, user: str, max_tokens: int = 1500) -> Dict[str, Any]:
        """Generate content using DeepSeek"""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-r1",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        )
        
        response.raise_for_status()
        data = response.json()
        
        content = data['choices'][0]['message']['content']
        usage = data.get('usage', {})
        
        return {
            'content': json.loads(content),
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0)
        }


class HybridEnricher:
    """Hybrid enrichment system using DeepSeek + GPT-5"""
    
    def __init__(self):
        self.cost_tracker = CostTracker()
        self.router = ContentRouter(self.cost_tracker)
        self.deepseek = DeepSeekClient()
        
        # Import existing GPT-5 client
        from .cursor_client import call_cursor_gpt5
        self.gpt5_client = call_cursor_gpt5
    
    def enrich_signal(self, signal: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich signal using hybrid model approach"""
        
        # Route to appropriate model
        provider = self.router.route_content(signal)
        
        print(f"🤖 Routing to {provider.value} for content: {signal.get('title', '')[:50]}...")
        
        # Get prompts
        from ..prompts.enrich_fi import get_prompt_template
        origin_country = signal.get('origin_country', 'US')
        system_prompt, user_template = get_prompt_template(origin_country)
        
        user_prompt = user_template.format(
            title=signal.get('title', ''),
            source_name=signal.get('source_name', ''),
            source_url=signal.get('source_url', ''),
            published_at=signal.get('published_at', ''),
            summary_raw=signal.get('summary_raw', ''),
            category_guess=signal.get('category_guess', ''),
            origin_country=origin_country
        )
        
        # Generate with selected model
        if provider == ModelProvider.DEEPSEEK:
            result_data = self._generate_with_deepseek(system_prompt, user_prompt)
        else:  # GPT-5
            result_data = self._generate_with_gpt5(system_prompt, user_prompt)
        
        # Quality control with GPT-5 if DeepSeek was used
        if provider == ModelProvider.DEEPSEEK:
            result_data['content'] = self._quality_control(result_data['content'], signal)
        
        # Record costs
        self.cost_tracker.record_usage(
            provider, 
            result_data['input_tokens'], 
            result_data['output_tokens']
        )
        
        return result_data['content']
    
    def _generate_with_deepseek(self, system: str, user: str) -> Dict[str, Any]:
        """Generate using DeepSeek"""
        return self.deepseek.generate(system, user, max_tokens=1500)
    
    def _generate_with_gpt5(self, system: str, user: str) -> Dict[str, Any]:
        """Generate using GPT-5"""
        result = self.gpt5_client(
            system=system,
            user=user,
            model="gpt-5",
            max_tokens=2500,
            temperature=0.3
        )
        
        # Estimate token usage (rough approximation)
        input_tokens = len(f"{system} {user}".split()) * 1.3
        output_tokens = len(str(result).split()) * 1.3
        
        return {
            'content': result,
            'input_tokens': int(input_tokens),
            'output_tokens': int(output_tokens)
        }
    
    def _quality_control(self, content: Dict[str, Any], signal: Dict[str, Any]) -> Dict[str, Any]:
        """GPT-5 quality control for DeepSeek output"""
        
        # Only run QC if we have budget and content needs improvement
        if not self.cost_tracker.can_afford(ModelProvider.GPT5, 500):
            return content
        
        # Quick quality check
        from ..prompts.enrich_fi import validate_enrichment
        validation = validate_enrichment(content, signal.get('origin_country'))
        
        if validation['valid']:
            return content  # Content is good, no QC needed
        
        # Run GPT-5 quality improvement
        qc_prompt = f"""
Improve this content to meet quality standards:

Original: {json.dumps(content, ensure_ascii=False)}

Issues: {', '.join(validation['errors'][:3])}

Return only the corrected JSON object.
"""
        
        try:
            improved = self.gpt5_client(
                system="You are a quality control specialist. Fix content to meet standards.",
                user=qc_prompt,
                model="gpt-5",
                max_tokens=500,
                temperature=0.1
            )
            
            # Record QC cost
            self.cost_tracker.record_usage(ModelProvider.GPT5, 100, 300)
            
            return improved
        except Exception:
            return content  # Return original if QC fails
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost usage summary"""
        return self.cost_tracker.get_usage_summary()


def main():
    """CLI interface for hybrid enrichment"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid LLM enrichment")
    parser.add_argument("--signal", required=True, help="Input signal JSON file")
    parser.add_argument("--schema", required=True, help="Schema file")
    parser.add_argument("--output", required=True, help="Output file")
    parser.add_argument("--cost-summary", action="store_true", help="Show cost summary")
    
    args = parser.parse_args()
    
    enricher = HybridEnricher()
    
    if args.cost_summary:
        summary = enricher.get_cost_summary()
        print("💰 Monthly Cost Summary:")
        print(f"   Total: ${summary['total_cost']:.2f}")
        for provider, data in summary['providers'].items():
            print(f"   {provider}: ${data['cost']:.2f}/${data['budget']:.2f} ({data['utilization']*100:.1f}%)")
        return
    
    # Load signal and schema
    with open(args.signal, 'r') as f:
        signal = json.load(f)
    
    with open(args.schema, 'r') as f:
        schema = json.load(f)
    
    # Enrich
    result = enricher.enrich_signal(signal, schema)
    
    # Save result
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Enriched content saved to {args.output}")
    
    # Show cost summary
    summary = enricher.get_cost_summary()
    print(f"💰 Monthly cost: ${summary['total_cost']:.2f}")


if __name__ == "__main__":
    main()
