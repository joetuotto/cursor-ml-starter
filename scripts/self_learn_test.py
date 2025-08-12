#!/usr/bin/env python3
"""
Test the self-learning system with mock data
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.hybrid.router import SelfLearningRouter, Item
from src.hybrid.collector import FeedbackCollector
from scripts.self_learn_daily import SelfLearningCycle
import numpy as np


def create_mock_items() -> list[Item]:
    """Create mock news items for testing"""
    items = [
        Item(
            id="test_fi_1",
            title="Suomen Pankki nostaa ohjauskorkoa 25 korkopisteellä",
            text="Keskuspankki päätti nostaa ohjauskorkoa inflaation hillitsemiseksi. Päätös vaikuttaa asuntolainoihin.",
            url="https://yle.fi/test1",
            lang="fi",
            source_trust=0.9,
            risk=0.7,
            complexity=0.8,
            country="FI"
        ),
        Item(
            id="test_us_1", 
            title="Federal Reserve signals rate pause amid cooling inflation",
            text="The Fed indicated it may pause rate hikes as inflation shows signs of cooling.",
            url="https://reuters.com/test1",
            lang="en",
            source_trust=0.85,
            risk=0.6,
            complexity=0.7,
            country="US"
        ),
        Item(
            id="test_tech_1",
            title="AI startup raises $50M in Series B funding",
            text="Technology company focused on machine learning secured significant funding.",
            url="https://techcrunch.com/test1",
            lang="en",
            source_trust=0.7,
            risk=0.2,
            complexity=0.4,
            country="US"
        ),
        Item(
            id="test_fi_2",
            title="Helsingin pörssi nousussa teknologiaosakkeiden vedossa",
            text="Suomalaiset teknologiayhtiöt vetivät pörssiä ylöspäin vahvojen tulosten myötä.",
            url="https://kauppalehti.fi/test1",
            lang="fi",
            source_trust=0.8,
            risk=0.3,
            complexity=0.5,
            country="FI"
        ),
        Item(
            id="test_security_1",
            title="NATO announces new defense initiative",
            text="Alliance members agreed on strengthened defense cooperation in Northern Europe.",
            url="https://nato.int/test1",
            lang="en",
            source_trust=0.95,
            risk=0.8,
            complexity=0.6,
            country="EU"
        )
    ]
    return items


def test_self_learning_router():
    """Test the self-learning router with mock items"""
    print("🧪 Testing Self-Learning Router")
    print("=" * 50)
    
    router = SelfLearningRouter()
    items = create_mock_items()
    
    results = []
    
    for item in items:
        print(f"\n📰 Processing: {item.title[:50]}...")
        
        result = router.route_and_process(item)
        results.append(result)
        
        print(f"   Model: {result['routing']['model']}")
        print(f"   Reason: {result['routing']['reason']}")
        print(f"   Cost: €{result['cost']['eur']:.4f}")
        print(f"   Event ID: {result['event_id']}")
        
        # Simulate user feedback
        user_feedback = {
            "click": np.random.choice([0, 1], p=[0.3, 0.7]),
            "time_on_card": np.random.randint(10, 120),
            "share": np.random.choice([0, 1], p=[0.8, 0.2]),
            "feedback": np.random.choice(["useful", "not_useful", "neutral"], p=[0.6, 0.1, 0.3])
        }
        
        router.add_user_feedback(result['event_id'], user_feedback)
        print(f"   User feedback: {user_feedback['feedback']}")
        
        # Simulate editor feedback
        editor_feedback = {
            "accepted": np.random.choice([0, 1], p=[0.2, 0.8]),
            "edits": np.random.uniform(0, 0.3)
        }
        
        router.add_editor_feedback(result['event_id'], editor_feedback)
        print(f"   Editor accepted: {bool(editor_feedback['accepted'])}")
    
    print(f"\n✅ Processed {len(items)} items")
    
    # Show budget status
    budget_status = router.budget_calibrator.get_budget_status()
    print(f"\n💰 Budget Status:")
    print(f"   Total spent: €{budget_status['current_spending']['total']:.4f}")
    print(f"   Utilization: {budget_status['budget']['utilization']*100:.1f}%")
    
    return results


def test_daily_cycle():
    """Test the daily learning cycle"""
    print("\n🔄 Testing Daily Learning Cycle")
    print("=" * 50)
    
    # Generate some mock events first
    collector = FeedbackCollector()
    
    # Create events over the last few days
    base_time = datetime.now()
    
    for i in range(30):  # 30 mock events
        event_time = base_time - timedelta(days=np.random.randint(0, 7))
        
        mock_event = {
            "ts": event_time.isoformat() + "Z",
            "id": f"mock_event_{i}",
            "content_id": f"content_{i}",
            "input": {
                "lang": np.random.choice(["fi", "en"], p=[0.4, 0.6]),
                "country": np.random.choice(["FI", "US", "EU"], p=[0.4, 0.4, 0.2]),
                "topic": np.random.choice(["central_banking", "technology", "security"], p=[0.4, 0.4, 0.2]),
                "complexity": np.random.uniform(0.2, 0.9),
                "source_reputation": np.random.uniform(0.6, 0.95)
            },
            "route": {
                "model": np.random.choice(["deepseek", "gpt5"], p=[0.7, 0.3]),
                "prompt_variant": f"variant_{np.random.randint(1, 4)}",
                "cache_hit": np.random.choice([True, False], p=[0.1, 0.9])
            },
            "output": {
                "schema_ok": np.random.choice([0, 1], p=[0.1, 0.9]),
                "why_matters_ok": np.random.choice([0, 1], p=[0.15, 0.85]),
                "has_refs": np.random.choice([0, 1], p=[0.2, 0.8]),
                "uniq_refs": np.random.randint(0, 5),
                "hallu_score": np.random.uniform(0, 0.1),
                "tox": np.random.uniform(0, 0.02),
                "ref_miss_rate": np.random.uniform(0, 0.2)
            },
            "user": {
                "click": np.random.choice([0, 1], p=[0.3, 0.7]),
                "time_on_card": np.random.randint(5, 180),
                "share": np.random.choice([0, 1], p=[0.8, 0.2]),
                "feedback": np.random.choice(["useful", "not_useful", "neutral"], p=[0.6, 0.1, 0.3])
            },
            "editor": {
                "accepted": np.random.choice([0, 1], p=[0.2, 0.8]),
                "edits": np.random.uniform(0, 0.5)
            },
            "cost": {
                "input_tokens": np.random.randint(800, 2000),
                "output_tokens": np.random.randint(400, 1000),
                "eur": np.random.uniform(0.01, 0.08)
            }
        }
        
        # Convert numpy types for JSON
        def convert_for_json(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        def convert_dict(d):
            if isinstance(d, dict):
                return {k: convert_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [convert_dict(v) for v in d]
            else:
                return convert_for_json(d)
        
        json_event = convert_dict(mock_event)
        
        # Write to events file
        with open("artifacts/feedback/events.jsonl", "a") as f:
            f.write(json.dumps(json_event) + "\n")
    
    print(f"📝 Generated 30 mock events")
    
    # Run the daily cycle
    cycle = SelfLearningCycle()
    result = cycle.run_daily_cycle()
    
    print(f"\n📊 Cycle Results:")
    print(f"   Status: {result.get('status', 'unknown')}")
    print(f"   Events processed: {result.get('events_processed', 0)}")
    
    if 'evaluation' in result:
        eval_result = result['evaluation']
        print(f"   Quality gates passed: {eval_result.get('quality_gates_passed', False)}")
        
        if 'overall_metrics' in eval_result:
            metrics = eval_result['overall_metrics']
            print(f"   Card pass rate: {metrics.get('card_pass_rate', 0):.3f}")
            print(f"   Hallucination rate: {metrics.get('hallu_rate', 0):.3f}")
            print(f"   Editor accept rate: {metrics.get('editor_accept_rate', 0):.3f}")
    
    if 'budget_calibration' in result:
        budget = result['budget_calibration']
        if budget.get('adjustments_made'):
            print(f"   Budget adjustments: {len(budget['adjustments_made'])}")
    
    if result.get('rollback_check', {}).get('rollback_executed'):
        print("   ⚠️  ROLLBACK EXECUTED")
    
    return result


def main():
    """Run all tests"""
    print("🚀 PARANOID Self-Learning System Test Suite")
    print("=" * 60)
    
    # Test 1: Router functionality
    router_results = test_self_learning_router()
    
    # Test 2: Daily learning cycle
    cycle_results = test_daily_cycle()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("=" * 60)
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"   Items processed: {len(router_results)}")
    print(f"   Daily cycle status: {cycle_results.get('status', 'unknown')}")
    
    # Show final state files
    state_dir = Path("artifacts/selflearn")
    if state_dir.exists():
        state_files = list(state_dir.glob("*.json"))
        print(f"   State files created: {len(state_files)}")
        for f in state_files:
            print(f"     - {f.name}")
    
    print("\n🔍 Check artifacts/selflearn/ for detailed results")
    print("💡 Run 'make selflearn-daily' to test in production mode")


if __name__ == "__main__":
    main()
