#!/usr/bin/env python3
"""
Enrichment functions for Cursor GPT-5 integration
"""

from typing import List, Dict, Any
try:
    from src.hybrid.budget import hard_cap_hit, should_throttle, estimate_cost_eur, record_usage, push_prom
except Exception:
    hard_cap_hit = lambda: False  # type: ignore
    should_throttle = lambda: False  # type: ignore
    def estimate_cost_eur(provider: str, input_tok: int, output_tok: int) -> float:  # type: ignore
        return 0.0
    def record_usage(provider: str, input_tok: int, output_tok: int, eur=None, meta=None):  # type: ignore
        return {}
    def push_prom():  # type: ignore
        return None

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
    """Run LLM with provider with budget guardrails"""
    # Budget routing: if hard cap hit, force DeepSeek-style fallback by caller selecting provider
    # Soft cap: caller can decide provider; here we just execute and log costs
    messages = build_messages(source_text, lang)
    res = provider.chat(messages, temperature=0.2)
    try:
        usage = res.get("usage", {}) if isinstance(res, dict) else {}
        in_tok = int(usage.get("prompt_tokens", 800))
        out_tok = int(usage.get("completion_tokens", usage.get("output_tokens", 600)))
        model_name = getattr(provider, "model", "gpt5" if "gpt" in str(getattr(provider, "model", "")).lower() else "deepseek")
        prov = "gpt5_cursor" if "gpt" in model_name else "deepseek"
        eur = estimate_cost_eur(prov, in_tok, out_tok)
        record_usage(prov, in_tok, out_tok, eur, meta={"lang": lang})
        push_prom()
    except Exception:
        pass
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
