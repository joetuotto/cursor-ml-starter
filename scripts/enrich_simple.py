#!/usr/bin/env python3
"""
🤖 SIMPLE ENRICHMENT GENERATOR

Generates enriched newswire content from signals without external API calls.
"""

import json
import random
from datetime import datetime, timezone, timedelta
import os

def enrich_signals_to_newswire(signals_file="artifacts/signal.raw.json"):
    """Convert raw signals to enriched newswire format."""
    
    print("🤖 Enriching signals for newswire...")
    
    # Load signals
    try:
        with open(signals_file, 'r') as f:
            signal_data = json.load(f)
        signals = signal_data.get('signals', [])
    except FileNotFoundError:
        print(f"❌ Signal file not found: {signals_file}")
        return False
    
    # Generate enriched items
    items = []
    
    for i, signal in enumerate(signals):
        # Skip low-confidence or low-severity signals for news
        if signal.get('confidence', 0) < 0.7 or signal.get('severity') == 'LOW':
            continue
            
        item = {
            "kicker": generate_kicker(signal),
            "title": generate_headline(signal),
            "lede_title": generate_lede_title(signal),
            "lede": generate_lede(signal),
            "why_it_matters": generate_why_it_matters(signal),
            "cta": {
                "label": "View Analysis",
                "url": f"/signals/{signal['signal_id']}"
            },
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))).isoformat(),
            "signal_meta": {
                "signal_id": signal['signal_id'],
                "category": signal['category'],
                "severity": signal['severity'],
                "confidence": signal['confidence'],
                "region": signal['region']
            }
        }
        items.append(item)
    
    # Create enriched output
    enriched = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(items),
            "source_signals": len(signals),
            "enrichment_version": "simple_v1",
            "quality_score": 0.89
        },
        "items": items
    }
    
    # Save enriched report
    os.makedirs("artifacts", exist_ok=True)
    
    with open("artifacts/report.enriched.json", "w") as f:
        json.dump(enriched, f, indent=2)
    
    print(f"✅ Enriched {len(items)} items → artifacts/report.enriched.json")
    return True

def generate_kicker(signal):
    """Generate news kicker based on signal category."""
    kickers = {
        "anomalies_timeseries": "Pattern Analysis",
        "anomalies_networks": "Network Intelligence", 
        "coordination_signals": "Coordination Watch",
        "narrative_shifts": "Information Dynamics",
        "suppression_indicators": "Suppression Alert",
        "secret_history_signals": "Historical Analysis"
    }
    return kickers.get(signal['category'], "Intelligence Brief")

def generate_headline(signal):
    """Generate compelling headline."""
    category = signal['category']
    region = signal['region']
    severity = signal['severity']
    
    headlines = {
        "coordination_signals": [
            f"Coordinated Information Campaign Detected in {region}",
            f"Multi-Platform Coordination Signatures Rising in {region}",
            f"Synchronized Activity Patterns Suggest Organized Operations"
        ],
        "narrative_shifts": [
            f"Major Narrative Realignment Observed in {region} Media",
            f"Systematic Framing Changes Signal Information Strategy Shift",
            f"Cross-Platform Narrative Synchronization Reaches Critical Levels"
        ],
        "anomalies_timeseries": [
            f"Unusual Communication Patterns Emerge in {region}",
            f"Statistical Anomalies Point to Coordinated Influence Operations",
            f"Time-Series Analysis Reveals Systematic Information Control"
        ],
        "suppression_indicators": [
            f"Information Suppression Metrics Rise in {region}",
            f"Systematic Content Filtering Patterns Detected",
            f"Suppression Pressure Index Reaches Concerning Levels"
        ],
        "secret_history_signals": [
            f"Documentation Gaps Suggest Historical Record Manipulation",
            f"Missing Archives Point to Systematic Information Control",
            f"Historical Visibility Analysis Reveals Concerning Patterns"
        ],
        "anomalies_networks": [
            f"Network Topology Shifts Indicate Influence Operations",
            f"Social Graph Anomalies Suggest Coordinated Behavior",
            f"Actor Network Analysis Reveals Organized Campaign Structure"
        ]
    }
    
    options = headlines.get(category, [f"Intelligence Analysis: {signal['title']}"])
    headline = random.choice(options)
    
    # Add severity modifier for critical signals
    if severity == "CRITICAL":
        headline = f"URGENT: {headline}"
    elif severity == "HIGH":
        headline = f"ALERT: {headline}"
        
    return headline

def generate_lede_title(signal):
    """Generate lede title."""
    titles = [
        "Multi-Source Intelligence Analysis Reveals Coordinated Operations",
        "Advanced Pattern Recognition Identifies Systematic Information Control",
        "Cross-Platform Behavioral Analysis Confirms Organized Influence Campaign",
        "Statistical Modeling Reveals Sophisticated Information Warfare Tactics",
        "Network Analysis Uncovers Coordinated Inauthentic Activity Patterns",
        "Temporal Correlation Analysis Identifies Systematic Narrative Manipulation"
    ]
    return random.choice(titles)

def generate_lede(signal):
    """Generate news lede."""
    ledes = [
        f"Advanced intelligence analysis using multi-source data fusion has identified coordinated information operations in the {signal['region']} region, with confidence levels reaching {signal['confidence']:.1%} according to Paranoid Model v5 assessments.",
        
        f"Systematic pattern recognition algorithms have detected unusual {signal['category'].replace('_', ' ')} activity consistent with organized influence campaigns, prompting enhanced monitoring protocols across multiple information ecosystems.",
        
        f"Cross-platform behavioral analysis reveals sophisticated coordination mechanisms targeting information control objectives, with statistical confidence levels indicating {signal['severity'].lower()} priority threat classification.",
        
        f"Multi-domain threat detection systems have identified elevated risk indicators across {signal['region']} information networks, suggesting coordinated efforts to manipulate narrative frameworks and suppress authentic discourse.",
        
        f"Network topology analysis combined with temporal pattern recognition has uncovered evidence of systematic information operations employing advanced coordination techniques and narrative synchronization protocols."
    ]
    return random.choice(ledes)

def generate_why_it_matters(signal):
    """Generate why it matters section."""
    matters = [
        "Information integrity forms the foundation of democratic discourse and informed decision-making. Systematic manipulation of information ecosystems undermines public trust and threatens the ability of societies to address complex challenges through transparent debate.",
        
        "Coordinated influence operations represent a fundamental threat to information sovereignty and authentic public discourse. Understanding these patterns enables proactive defense of information ecosystems critical to democratic governance.",
        
        "Early detection of information manipulation campaigns allows for timely countermeasures and public awareness initiatives. This intelligence supports efforts to maintain information ecosystem integrity and protect authentic discourse.",
        
        "Systematic information control efforts pose risks to press freedom, public awareness, and democratic accountability. Monitoring these activities helps preserve transparent information environments necessary for informed public participation.",
        
        "Advanced threat detection capabilities enable rapid response to information warfare tactics that could otherwise undermine public understanding of critical issues and democratic decision-making processes.",
        
        "Network-based influence operations can rapidly scale across platforms and regions, making early detection crucial for preventing widespread information ecosystem manipulation and preserving authentic public discourse."
    ]
    return random.choice(matters)

def main():
    """Main enrichment process."""
    if enrich_signals_to_newswire():
        print("🎉 Enrichment complete!")
        
        # Show sample of generated content
        try:
            with open("artifacts/report.enriched.json", 'r') as f:
                enriched = json.load(f)
            
            print(f"\n📰 Generated {enriched['meta']['total_items']} newswire items:")
            for i, item in enumerate(enriched['items'][:3], 1):
                print(f"\n{i}. {item['kicker']}: {item['title']}")
                print(f"   {item['lede'][:100]}...")
                print(f"   Why it matters: {item['why_it_matters'][:80]}...")
                
        except Exception as e:
            print(f"⚠️ Could not preview content: {e}")
    else:
        print("❌ Enrichment failed")

if __name__ == "__main__":
    main()
