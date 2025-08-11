#!/usr/bin/env python3
"""
Enrichment functions for Cursor GPT-5 integration
"""

from typing import List, Dict, Any

def build_messages(source_text: str, lang: str = "en") -> List[Dict[str, str]]:
    """Build messages for LLM chat completion"""
    system = (
        "You are an investigations analyst. "
        "Return STRICT JSON with keys: kicker, headline, lede, why_it_matters, refs (array of URLs), locale."
    )
    user = f"Text:\n{source_text}\n\nlocale='{lang}'. Ensure valid JSON only."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]

def run_llm(provider, source_text: str, lang: str):
    """Run LLM with provider"""
    messages = build_messages(source_text, lang)
    res = provider.chat(messages, temperature=0.2)
    return res

def route_request(item: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """Route request to appropriate provider"""
    lang = (item.get("lang") or "en").lower()
    topic = (item.get("topic") or "").lower()
    risk = float(item.get("risk") or 0.0)
    complexity = float(item.get("complexity") or 0.0)

    force_langs = set(s.lower() for s in cfg["routing"]["force_gpt5_languages"])
    if lang in force_langs:
        return "gpt5_cursor"

    for kw in cfg["routing"]["critical_topics"]:
        if kw in topic:
            return "gpt5_cursor"

    if risk >= cfg["routing"]["risk_threshold"] or complexity >= cfg["routing"]["complexity_threshold"]:
        return "gpt5_cursor"

    return "deepseek"
