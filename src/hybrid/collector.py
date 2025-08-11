#!/usr/bin/env python3
"""
Event collector for self-learning feedback system
Records all interactions, evaluations, and user feedback
"""

import json
import time
import uuid
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class FeedbackCollector:
    """Collects and stores feedback events in JSONL format"""
    
    def __init__(self, store_path: str = "artifacts/feedback/events.jsonl"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, 
                  content_id: str,
                  input_context: Dict[str, Any],
                  routing_decision: Dict[str, Any], 
                  output_analysis: Dict[str, Any],
                  cost_data: Dict[str, Any],
                  user_feedback: Optional[Dict[str, Any]] = None,
                  editor_feedback: Optional[Dict[str, Any]] = None) -> str:
        """Log a complete interaction event"""
        
        event_id = f"nw_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "id": event_id,
            "content_id": content_id,
            "input": input_context,
            "route": routing_decision,
            "output": output_analysis,
            "cost": cost_data,
            "user": user_feedback or {},
            "editor": editor_feedback or {}
        }
        
        self._append_event(event)
        return event_id
    
    def append_feedback(self, event_id: str, feedback_type: str, feedback_data: Dict[str, Any]):
        """Append additional feedback to existing event"""
        # For now, create a new event linking to the original
        # In production, you might want to update the original event
        update_event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "feedback_update",
            "original_event_id": event_id,
            "feedback_type": feedback_type,
            "data": feedback_data
        }
        
        self._append_event(update_event)
    
    def _append_event(self, event: Dict[str, Any]):
        """Append event to JSONL file"""
        def convert_numpy(obj):
            """Convert numpy types to native Python types"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Convert numpy types recursively
        def convert_dict(d):
            if isinstance(d, dict):
                return {k: convert_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [convert_dict(v) for v in d]
            else:
                return convert_numpy(d)
        
        converted_event = convert_dict(event)
        
        with open(self.store_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(converted_event, ensure_ascii=False) + '\n')
    
    def read_events(self, days_back: int = 14) -> list[Dict[str, Any]]:
        """Read recent events for analysis"""
        if not self.store_path.exists():
            return []
        
        cutoff_time = time.time() - (days_back * 24 * 3600)
        events = []
        
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        event = json.loads(line.strip())
                        # Parse timestamp and filter by recency
                        event_time = datetime.fromisoformat(event['ts'].replace('Z', '+00:00')).timestamp()
                        if event_time >= cutoff_time:
                            events.append(event)
        except Exception as e:
            print(f"Warning: Error reading events: {e}")
        
        return events


class AutoEvaluator:
    """Automatic quality evaluation for generated content"""
    
    def __init__(self):
        self.hallu_keywords = [
            "unconfirmed", "alleged", "reportedly", "sources say", "rumors suggest",
            "väitetään", "kerrotaan", "huhutaan", "epävirallinen"
        ]
    
    def evaluate_output(self, content: Dict[str, Any], sources: list = None) -> Dict[str, Any]:
        """Evaluate content quality automatically"""
        
        # Basic schema validation
        schema_ok = all(key in content for key in ['headline', 'lede', 'why_it_matters'])
        
        # Check if why_it_matters has content
        why_matters_ok = bool(content.get('why_it_matters', '').strip())
        
        # Check for references/sources
        has_refs = bool(sources and len(sources) > 0)
        uniq_refs = len(set(sources)) if sources else 0
        
        # Simple hallucination heuristic
        text = f"{content.get('lede', '')} {content.get('why_it_matters', '')}"
        hallu_score = self._estimate_hallucination(text)
        
        # Toxicity placeholder (would use actual model in production)
        tox_score = 0.01  # Very low baseline
        
        return {
            "schema_ok": schema_ok,
            "why_matters_ok": why_matters_ok,
            "has_refs": has_refs,
            "uniq_refs": uniq_refs,
            "hallu_score": hallu_score,
            "tox": tox_score,
            "ref_miss_rate": 0.0 if has_refs else 1.0
        }
    
    def _estimate_hallucination(self, text: str) -> float:
        """Simple heuristic for hallucination detection"""
        if not text:
            return 0.5
        
        text_lower = text.lower()
        
        # Count uncertain language
        uncertain_count = sum(1 for keyword in self.hallu_keywords if keyword in text_lower)
        
        # Normalize by text length
        score = min(uncertain_count / max(1, len(text.split()) / 50), 1.0)
        
        return score


def create_mock_event():
    """Create a mock event for testing"""
    collector = FeedbackCollector()
    evaluator = AutoEvaluator()
    
    # Mock input
    content = {
        "headline": "Suomen Pankki nostaa ohjauskorkoa",
        "lede": "Keskuspankki nosti ohjauskorkoa 0.25 prosenttiyksiköllä inflaation hillitsemiseksi",
        "why_it_matters": "Vaikuttaa suoraan asuntolainojen korkoihin ja kuluttajien ostovoimaan"
    }
    
    sources = ["https://yle.fi/example", "https://hs.fi/example"]
    
    # Evaluate
    evaluation = evaluator.evaluate_output(content, sources)
    
    # Log event
    event_id = collector.log_event(
        content_id="test_001",
        input_context={"lang": "fi", "country": "FI", "topic": "ECB", "complexity": 0.7},
        routing_decision={"model": "gpt5", "prompt_variant": "fi_v1", "cache_hit": False},
        output_analysis=evaluation,
        cost_data={"input_tokens": 1500, "output_tokens": 600, "eur": 0.032},
        user_feedback={"click": 1, "time_on_card": 45, "share": 0},
        editor_feedback={"accepted": 1, "edits": 0.1}
    )
    
    print(f"Created mock event: {event_id}")
    return event_id


if __name__ == "__main__":
    create_mock_event()
