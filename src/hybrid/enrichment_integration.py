#!/usr/bin/env python3
"""
Integration glue for connecting live LLM clients to existing enrichment pipeline
Provides drop-in replacement for publisher_llm.py functions
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.hybrid.llm_clients import DeepSeekClient, GPT5Client, LLMResponse
try:
    from src.hybrid.budget import (
        record_usage as _budget_record_usage,
        estimate_cost_eur as _budget_estimate_cost,
        push_prom as _budget_push_prom,
        stats as _budget_stats,
        should_throttle as _budget_should_throttle,
        hard_cap_hit as _budget_hard_cap_hit,
        should_daily_throttle as _budget_should_daily_throttle,
        daily_hard_cap_hit as _budget_daily_hard_cap_hit,
    )
except Exception:
    _budget_record_usage = None
    _budget_estimate_cost = None
    _budget_push_prom = None
    _budget_stats = None
    _budget_should_throttle = None
    _budget_hard_cap_hit = None
from src.hybrid.router import SelfLearningRouter, Item


class HybridEnrichmentClient:
    """Drop-in replacement for existing enrichment functions"""
    
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode or os.getenv("MOCK_MODE", "false").lower() == "true"
        
        if not self.mock_mode:
            # Initialize real clients
            try:
                self.deepseek_client = DeepSeekClient()
            except RuntimeError:
                print("Warning: DeepSeek API key missing, falling back to mock mode")
                self.mock_mode = True
            
            try:
                self.gpt5_client = GPT5Client()
            except RuntimeError:
                print("Warning: GPT-5 API key missing, falling back to mock mode")
                self.mock_mode = True
        
        # Initialize self-learning router
        try:
            self.router = SelfLearningRouter()
        except Exception as e:
            print(f"Warning: Self-learning router disabled: {e}")
            self.router = None
    
    def enrich_signal(self, raw_signal: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced enrichment with intelligent routing
        Drop-in replacement for publisher_llm.enrich_signal()
        """
        
        if self.mock_mode:
            return self._mock_enrichment(raw_signal)
        
        # Extract signal metadata for routing
        item = Item(
            id=raw_signal.get('id', 'unknown'),
            title=raw_signal.get('title', ''),
            text=raw_signal.get('summary_raw', ''),
            url=raw_signal.get('source_url'),
            lang=raw_signal.get('origin_country', 'en').lower(),
            source_trust=0.8,  # Default, could be enhanced
            risk=self._assess_risk(raw_signal),
            complexity=self._assess_complexity(raw_signal),
            country=raw_signal.get('origin_country', 'US')
        )
        
        # Use self-learning router if available
        if self.router:
            try:
                result = self.router.route_and_process(item)
                return result['output']
            except Exception as e:
                print(f"Router failed, falling back to simple routing: {e}")
        
        # Fallback to simple routing
        return self._simple_route_and_enrich(raw_signal, schema)
    
    def _simple_route_and_enrich(self, raw_signal: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Simple routing logic when self-learning router is unavailable"""
        
        # Determine route
        lang = raw_signal.get('origin_country', 'US').lower()
        complexity = self._assess_complexity(raw_signal)
        risk = self._assess_risk(raw_signal)
        
        # Route decision
        use_gpt5 = (
            lang == 'fi' or                          # Finnish content
            complexity > 0.6 or                      # High complexity
            risk > 0.5 or                           # High risk
            any(topic in raw_signal.get('title', '').lower() 
                for topic in ['ecb', 'fed', 'central bank', 'keskuspankki'])
        )
        
        # Budget-aware routing adjustments
        try:
            if _budget_daily_hard_cap_hit and _budget_daily_hard_cap_hit():
                use_gpt5 = False
            elif _budget_should_daily_throttle and _budget_should_daily_throttle():
                critical = lang == 'fi' or any(topic in raw_signal.get('title','').lower() for topic in ['ecb','fed','central bank','keskuspankki'])
                if not critical:
                    use_gpt5 = False
            elif _budget_hard_cap_hit and _budget_hard_cap_hit():
                use_gpt5 = False
            elif _budget_should_throttle and _budget_should_throttle():
                # keep GPT-5 for Finnish/critical topics only
                critical = lang == 'fi' or any(topic in raw_signal.get('title','').lower() for topic in ['ecb','fed','central bank','keskuspankki'])
                if not critical:
                    use_gpt5 = False
        except Exception:
            pass

        client = self.gpt5_client if use_gpt5 else self.deepseek_client
        
        # Build prompts
        sys_prompt = self._build_system_prompt(lang)
        user_prompt = self._build_user_prompt(raw_signal)
        
        # Generate
        try:
            result, meta = client.generate_json(
                sys_prompt=sys_prompt,
                user_prompt=user_prompt,
                schema=schema,
                temperature=0.25 if use_gpt5 else 0.3,
                max_output_tokens=800
            )
            
            # Add metadata
            result['_meta'] = {
                'model': meta.model,
                'cost_eur': meta.cost_eur,
                'tokens_in': meta.prompt_tokens,
                'tokens_out': meta.completion_tokens,
                'routed_to': 'gpt5' if use_gpt5 else 'deepseek'
            }
            
            # Log budget usage
            try:
                if _budget_record_usage is not None:
                    prov = 'gpt5_cursor' if use_gpt5 else 'deepseek'
                    _budget_record_usage(prov, meta.prompt_tokens, meta.completion_tokens, meta.cost_eur, meta={"routed_to": prov})
                    if _budget_push_prom is not None:
                        _budget_push_prom()
            except Exception:
                pass

            return result
            
        except Exception as e:
            print(f"LLM generation failed: {e}")
            return self._mock_enrichment(raw_signal)
    
    def _assess_complexity(self, signal: Dict[str, Any]) -> float:
        """Simple complexity assessment"""
        title = signal.get('title', '').lower()
        text = signal.get('summary_raw', '').lower()
        
        complexity_indicators = [
            'monetary policy', 'fiscal policy', 'quantitative easing',
            'derivatives', 'securities', 'regulation',
            'geopolitical', 'sanctions', 'trade war'
        ]
        
        score = 0.0
        for indicator in complexity_indicators:
            if indicator in title or indicator in text:
                score += 0.2
        
        return min(1.0, score)
    
    def _assess_risk(self, signal: Dict[str, Any]) -> float:
        """Simple risk assessment"""
        title = signal.get('title', '').lower()
        
        risk_indicators = [
            'crisis', 'emergency', 'sanctions', 'war',
            'recession', 'inflation', 'default'
        ]
        
        score = 0.0
        for indicator in risk_indicators:
            if indicator in title:
                score += 0.3
        
        return min(1.0, score)
    
    def _build_system_prompt(self, lang: str) -> str:
        """Build system prompt based on language"""
        if lang == 'fi':
            return (
                "Olet talousasiantuntija, joka analysoi uutisia suomalaisesta näkökulmasta. "
                "Tuota tarkka, faktapohjainen analyysi sisältäen konkreettiset vaikutukset "
                "Suomen markkinoihin. Sisällytä luotettavat lähteet."
            )
        else:
            return (
                "You're a financial analyst producing expert-level market analysis. "
                "Focus on concrete impacts, quantifiable effects, and verifiable sources. "
                "Output structured JSON only."
            )
    
    def _build_user_prompt(self, signal: Dict[str, Any]) -> str:
        """Build user prompt from signal"""
        return f"""
SOURCE: {signal.get('source_name', 'Unknown')}
TITLE: {signal.get('title', '')}
CONTENT: {signal.get('summary_raw', '')}
URL: {signal.get('source_url', '')}
PUBLISHED: {signal.get('published_at', '')}

Generate a comprehensive analysis focusing on market impacts and concrete implications.
"""
    
    def _mock_enrichment(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Mock enrichment for testing"""
        from datetime import datetime
        
        return {
            "kicker": "Market Update",
            "headline": signal.get('title', 'News Update'),
            "lede": f"Analysis of: {signal.get('title', 'Unknown news')}. Market implications and investor considerations.",
            "why_it_matters": "This development affects market sentiment and investment decisions across sectors.",
            "refs": [
                signal.get('source_url', 'https://example.com'),
                "https://example.com/reference1",
                "https://example.com/reference2"
            ],
            "confidence": 0.8,
            "tags": ["market", "analysis", "update"],
            "timestamp": datetime.now().isoformat(),
            "_meta": {
                "model": "mock",
                "cost_eur": 0.001,
                "tokens_in": 100,
                "tokens_out": 50,
                "routed_to": "mock"
            }
        }


# Global instance for easy import
enrichment_client = HybridEnrichmentClient()


def enrich_signal(raw_signal: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Drop-in replacement function"""
    return enrichment_client.enrich_signal(raw_signal, schema)


# Legacy compatibility
def cursor_call(*args, **kwargs):
    """Legacy function compatibility"""
    print("Warning: cursor_call is deprecated, use HybridEnrichmentClient instead")
    return {"content": "Legacy function called, please update to new API"}


if __name__ == "__main__":
    # Test the integration
    test_signal = {
        "id": "test_001",
        "title": "European Central Bank considers rate cut amid cooling inflation",
        "summary_raw": "ECB officials signal potential monetary policy changes for September meeting",
        "source_name": "Reuters",
        "source_url": "https://reuters.com/test",
        "published_at": "2025-08-11T12:00:00Z",
        "origin_country": "EU"
    }
    
    test_schema = {
        "type": "object",
        "required": ["kicker", "headline", "lede"],
        "properties": {
            "kicker": {"type": "string"},
            "headline": {"type": "string"},
            "lede": {"type": "string"}
        }
    }
    
    result = enrich_signal(test_signal, test_schema)
    print("Test enrichment result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
