#!/usr/bin/env python3
"""
Test script for hybrid enrichment integration
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.paranoid_model.publisher_llm import enrich_with_hybrid

def main():
    """Test hybrid enrichment with sample data"""
    
    # DEMO inputit — vaihda omaan signaalietappiin (esim. artifacts/signal.raw.json)
    items = [
        {
            "title": "Suomen Pankki pitää ohjauskoron ennallaan", 
            "lang": "fi", 
            "country": "FI", 
            "topic": "central_banking", 
            "source_url": "https://example.fi/a",
            "summary_raw": "Keskuspankki päätti pitää ohjauskoron 4,75 prosentissa inflaation hidastumisen vuoksi."
        },
        {
            "title": "ECB signals rate cuts", 
            "lang": "en", 
            "country": "EU", 
            "topic": "central_banking", 
            "source_url": "https://example.eu/b",
            "summary_raw": "European Central Bank officials indicated potential rate reductions in upcoming meetings."
        },
        {
            "title": "Tech startup raises series A", 
            "lang": "en", 
            "country": "US", 
            "topic": "technology", 
            "source_url": "https://example.com/c",
            "summary_raw": "Helsinki-based AI company secured €15M in Series A funding for European expansion."
        },
    ]
    
    print("🚀 Testing Hybrid Enrichment Pipeline")
    print("=" * 50)
    
    cards = []
    for i, item in enumerate(items, 1):
        print(f"\n📰 Processing item {i}: {item['title'][:50]}...")
        print(f"   Language: {item['lang']}")
        print(f"   Topic: {item['topic']}")
        
        try:
            card = enrich_with_hybrid(item)
            cards.append(card)
            
            # Show routing decision
            routing = card.get('_meta', {}).get('routing', {})
            provider = routing.get('provider', 'unknown')
            print(f"   ✅ Routed to: {provider}")
            print(f"   ✅ Validation: {'PASS' if card.get('_meta', {}).get('validation', {}).get('ok') else 'FAIL'}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            # Add error card
            cards.append({
                "kicker": "Error",
                "headline": item.get('title', 'Processing Failed'),
                "lede": f"Error processing content: {str(e)}",
                "why_it_matters": "System error requires attention.",
                "cta": {"label": "Source", "href": item.get('source_url', 'https://example.com')},
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "_meta": {"error": str(e)}
            })
    
    # Save results
    Path("artifacts").mkdir(parents=True, exist_ok=True)
    out = Path("artifacts/report.enriched.json")
    out.write_text(json.dumps(cards, ensure_ascii=False, indent=2))
    
    print(f"\n✅ Wrote {out} ({len(cards)} cards) at {datetime.utcnow().isoformat()}Z")
    
    # Show summary stats
    routing_stats = {}
    validation_stats = {"pass": 0, "fail": 0}
    
    for card in cards:
        provider = card.get('_meta', {}).get('routing', {}).get('provider', 'unknown')
        routing_stats[provider] = routing_stats.get(provider, 0) + 1
        
        validation_ok = card.get('_meta', {}).get('validation', {}).get('ok', False)
        validation_stats["pass" if validation_ok else "fail"] += 1
    
    print(f"\n📊 Summary:")
    print(f"   Routing: {dict(routing_stats)}")
    print(f"   Validation: {validation_stats}")
    
    # Quick content preview
    if cards:
        print(f"\n📄 Sample output (first card):")
        sample = cards[0]
        print(f"   Kicker: {sample.get('kicker', 'N/A')}")
        print(f"   Headline: {sample.get('headline', 'N/A')[:60]}...")
        print(f"   Provider: {sample.get('_meta', {}).get('routing', {}).get('provider', 'N/A')}")

if __name__ == "__main__":
    main()
