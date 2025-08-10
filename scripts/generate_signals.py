#!/usr/bin/env python3
"""
🚨 SIMPLE SIGNAL GENERATOR

Generates paranoid signals for immediate deployment without full model training.
"""

import json
import random
from datetime import datetime, timezone
import os

def generate_paranoid_signals(n_signals=5):
    """Generate mock paranoid intelligence signals."""
    
    signal_categories = [
        "anomalies_timeseries",
        "anomalies_networks", 
        "coordination_signals",
        "narrative_shifts",
        "suppression_indicators",
        "secret_history_signals"
    ]
    
    regions = ["US", "EU", "APAC", "MENA", "LATAM", "GLOBAL"]
    severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    signals = []
    
    for i in range(n_signals):
        # Generate random signal
        signal = {
            "signal_id": f"PV5-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": random.choice(signal_categories),
            "region": random.choice(regions),
            "severity": random.choice(severity_levels),
            "confidence": round(random.uniform(0.65, 0.98), 3),
            "title": generate_signal_title(),
            "description": generate_signal_description(),
            "indicators": {
                "sensitive_class_prob": round(random.uniform(0.15, 0.95), 3),
                "suppression_event_6w_prob": round(random.uniform(0.05, 0.85), 3),
                "narrative_shift_4w_prob": round(random.uniform(0.1, 0.75), 3),
                "conflict_intensity": round(random.uniform(0.0, 0.9), 3)
            },
            "risk_factors": generate_risk_factors(),
            "recommended_actions": generate_actions(),
            "metadata": {
                "model_version": "paranoid_v5_demo",
                "data_sources": ["WGI", "GDELT", "OSI"], 
                "processing_time_ms": random.randint(450, 1200)
            }
        }
        signals.append(signal)
    
    return signals

def generate_signal_title():
    """Generate realistic signal titles."""
    titles = [
        "Elevated Coordination Activity in Information Networks",
        "Narrative Coherence Shifts Detected in Media Landscape",
        "Anomalous Pattern Recognition in Communication Channels",
        "Suppression Indicators Rising in Target Demographics",
        "Secret History Signals: Documentation Gap Analysis",
        "Network Density Fluctuations Suggest Coordinated Behavior",
        "Temporal Analysis Reveals Systematic Information Control",
        "Cross-Platform Narrative Synchronization Detected",
        "Actor Network Analysis: Influence Operation Signatures",
        "Financial Pressure Index Correlates with Narrative Changes"
    ]
    return random.choice(titles)

def generate_signal_description():
    """Generate signal descriptions."""
    descriptions = [
        "Multi-source analysis indicates coordinated information operations with elevated suppression probabilities across monitored channels.",
        "Statistical anomalies in narrative framing patterns suggest systematic influence campaigns targeting specific demographic segments.",
        "Network topology analysis reveals unusual clustering behaviors consistent with coordinated inauthentic activity patterns.",
        "Temporal correlation analysis identifies synchronized narrative shifts across multiple information ecosystems and geographic regions.",
        "Documentation gap analysis reveals systematic historical record manipulation with elevated concealment probability scores.",
        "Cross-platform behavioral signatures indicate organized influence operations with sophisticated coordination mechanisms in play.",
        "Multi-domain threat indicators suggest escalating information warfare tactics with increased suppression and narrative control efforts.",
        "Predictive models identify elevated risk scenarios with high confidence intervals for systematic information suppression events."
    ]
    return random.choice(descriptions)

def generate_risk_factors():
    """Generate risk factor analysis."""
    factors = [
        "Elevated propaganda index scores",
        "Increased framing intensity metrics", 
        "Network density anomalies",
        "Suppression pressure indicators",
        "Coordination signal clustering",
        "Historical visibility gaps",
        "Missing documentation scores",
        "Treatment asymmetry patterns",
        "Echo signal amplification",
        "External sanction correlations"
    ]
    return random.sample(factors, random.randint(3, 6))

def generate_actions():
    """Generate recommended actions."""
    actions = [
        "Enhance monitoring of identified network clusters",
        "Deploy counter-narrative analysis protocols",
        "Initiate deep-dive investigation on source networks",
        "Coordinate with relevant stakeholders for verification",
        "Implement enhanced documentation preservation measures",
        "Activate real-time monitoring on detected channels",
        "Conduct actor network analysis for attribution",
        "Deploy predictive modeling for scenario planning",
        "Initiate cross-platform correlation analysis",
        "Establish communication channels for threat response"
    ]
    return random.sample(actions, random.randint(2, 4))

def main():
    """Generate signals and save to artifacts."""
    print("🚨 Generating Paranoid V5 Intelligence Signals...")
    
    # Generate signals
    signals = generate_paranoid_signals(8)
    
    # Create output structure
    output = {
        "run_meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_version": "paranoid_v5_demo",
            "total_signals": len(signals),
            "generation_method": "mock_intelligence",
            "data_quality": "synthetic_demo"
        },
        "signals": signals,
        "summary": {
            "by_severity": {
                "CRITICAL": len([s for s in signals if s["severity"] == "CRITICAL"]),
                "HIGH": len([s for s in signals if s["severity"] == "HIGH"]),
                "MEDIUM": len([s for s in signals if s["severity"] == "MEDIUM"]),
                "LOW": len([s for s in signals if s["severity"] == "LOW"])
            },
            "by_category": {},
            "avg_confidence": round(sum(s["confidence"] for s in signals) / len(signals), 3)
        }
    }
    
    # Calculate category breakdown
    categories = {}
    for signal in signals:
        cat = signal["category"]
        categories[cat] = categories.get(cat, 0) + 1
    output["summary"]["by_category"] = categories
    
    # Save to artifacts
    os.makedirs("artifacts", exist_ok=True)
    
    with open("artifacts/signal.raw.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Generated {len(signals)} signals → artifacts/signal.raw.json")
    print(f"📊 Severity breakdown: {output['summary']['by_severity']}")
    print(f"🎯 Average confidence: {output['summary']['avg_confidence']}")
    print(f"📂 Categories: {list(output['summary']['by_category'].keys())}")

if __name__ == "__main__":
    main()
