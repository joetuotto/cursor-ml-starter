#!/usr/bin/env python3
"""
Quick hybrid run script - reads sample news and writes to artifacts/report.enriched.json
"""

import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.hybrid.providers.cursor_gpt5 import CursorGpt5Provider
from src.hybrid.models import make_provider
from src.hybrid.enrich import build_messages, route_request

# Sample news items
SAMPLE_NEWS = [
    {
        "id": "fi_sample_1",
        "title": "Suomen Pankki nostaa ohjauskorkoa 0,25 prosenttiyksiköllä",
        "text": "Suomen Pankki päätti nostaa ohjauskorkoa inflaation hillitsemiseksi. Päätös vaikuttaa suoraan asuntolainojen korkoihin ja kuluttajien ostovoimaan.",
        "lang": "fi",
        "topic": "keskuspankki korko",
        "risk": 0.7,
        "complexity": 0.8,
        "source": "YLE Uutiset"
    },
    {
        "id": "en_sample_1", 
        "title": "European Central Bank signals potential rate cuts",
        "text": "ECB officials indicated they may reduce interest rates if inflation continues to cool across the eurozone.",
        "lang": "en",
        "topic": "ecb monetary policy",
        "risk": 0.6,
        "complexity": 0.7,
        "source": "Reuters"
    },
    {
        "id": "tech_sample_1",
        "title": "Finnish tech startup raises €10M Series A",
        "text": "Helsinki-based AI company secured significant funding for European expansion.",
        "lang": "en", 
        "topic": "technology startup",
        "risk": 0.2,
        "complexity": 0.3,
        "source": "TechCrunch"
    }
]

def load_config() -> dict:
    """Load hybrid configuration"""
    config_path = Path("config/hybrid.yaml")
    if not config_path.exists():
        return {
            "routing": {
                "force_gpt5_languages": ["fi"],
                "critical_topics": ["fed", "ecb", "suomen pankki", "korko", "central banking"],
                "risk_threshold": 0.40,
                "complexity_threshold": 0.50
            }
        }
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def mock_provider_response(provider_name: str, text: str, lang: str) -> dict:
    """Mock provider response for testing"""
    if provider_name == "gpt5_cursor":
        return {
            "ok": True,
            "text": json.dumps({
                "kicker": "Premium Analysis",
                "headline": f"Expert analysis: {text[:50]}...",
                "lede": f"In-depth analysis reveals key implications for {lang} markets and stakeholders.",
                "why_it_matters": "This development requires careful monitoring by investors and policymakers.",
                "refs": ["https://example.com/source1", "https://example.com/source2"],
                "locale": lang
            }),
            "usage": {"prompt_tokens": 150, "completion_tokens": 80}
        }
    else:  # deepseek
        return {
            "ok": True,
            "text": json.dumps({
                "kicker": "Quick Update",
                "headline": f"Breaking: {text[:50]}...",
                "lede": f"Latest developments in {lang} market show significant changes.",
                "why_it_matters": "Standard market update for general awareness.",
                "refs": ["https://example.com/source1"],
                "locale": lang
            }),
            "usage": {"prompt_tokens": 100, "completion_tokens": 60}
        }

def process_news_item(item: dict, cfg: dict, mock_mode: bool = True) -> dict:
    """Process single news item"""
    # Route decision
    provider_name = route_request(item, cfg)
    
    print(f"📰 {item['id']}: {item['title'][:50]}...")
    print(f"   🎯 Routed to: {provider_name}")
    print(f"   🌍 Language: {item['lang']}")
    
    if mock_mode or not os.getenv("CURSOR_API_KEY"):
        # Mock mode
        response = mock_provider_response(provider_name, item['text'], item['lang'])
        print(f"   ⚡ Mock response generated")
    else:
        # Real API call
        try:
            if provider_name == "gpt5_cursor":
                provider = CursorGpt5Provider(
                    base_url=os.getenv("CURSOR_BASE_URL", "https://api.cursor.sh/v1"),
                    api_key=os.getenv("CURSOR_API_KEY", ""),
                    model=os.getenv("CURSOR_GPT5_MODEL", "gpt-5-thinking"),
                    timeout_s=int(os.getenv("CURSOR_TIMEOUT_S", "45"))
                )
            else:
                # Fallback to mock for DeepSeek
                response = mock_provider_response(provider_name, item['text'], item['lang'])
                print(f"   ⚡ Mock DeepSeek response (real provider not implemented)")
                return json.loads(response['text'])
            
            messages = build_messages(item['text'], item['lang'])
            response = provider.chat(messages, temperature=0.2)
            print(f"   ✅ Real API response received")
            
        except Exception as e:
            print(f"   ❌ API call failed: {e}")
            response = mock_provider_response(provider_name, item['text'], item['lang'])
    
    if response['ok']:
        try:
            enriched = json.loads(response['text'])
            # Add metadata
            enriched['_meta'] = {
                'provider': provider_name,
                'source_id': item['id'],
                'processed_at': datetime.now().isoformat()
            }
            return enriched
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode failed: {e}")
            return None
    else:
        print(f"   ❌ Provider error: {response.get('err', 'unknown')}")
        return None

def main():
    """Main execution"""
    print("🚀 PARANOID Hybrid News Processing")
    print("=" * 50)
    
    # Load configuration
    cfg = load_config()
    
    # Check if real API mode
    mock_mode = not bool(os.getenv("CURSOR_API_KEY"))
    if mock_mode:
        print("🔧 Running in MOCK mode (no API keys)")
    else:
        print("🌐 Running with REAL APIs")
    
    print()
    
    # Process all news items
    enriched_items = []
    
    for item in SAMPLE_NEWS:
        result = process_news_item(item, cfg, mock_mode)
        if result:
            enriched_items.append(result)
        print()
    
    # Write output
    output_path = Path("artifacts/report.enriched.json")
    output_path.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_items, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Wrote {len(enriched_items)} enriched items to {output_path}")
    print(f"📊 Routing summary:")
    
    # Summary stats
    routing_stats = {}
    for item in enriched_items:
        provider = item.get('_meta', {}).get('provider', 'unknown')
        routing_stats[provider] = routing_stats.get(provider, 0) + 1
    
    for provider, count in routing_stats.items():
        print(f"   {provider}: {count} items")
    
    print("\n🌐 Ready for UI consumption!")

if __name__ == "__main__":
    main()
