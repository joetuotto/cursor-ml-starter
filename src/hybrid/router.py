import re
from dataclasses import dataclass

@dataclass
class Item:
    id: str
    title: str
    text: str
    url: str | None
    lang: str
    source_trust: float  # 0..1
    risk: float          # 0..1 (topic sensitivity)
    complexity: float    # 0..1 (financial/technical)
    country: str | None

def _contains_critical_topic(text: str, critical: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in critical)

def route(item: Item, cfg) -> str:
    # Drop to validation if very low trust or clear duplicate will be handled elsewhere
    if item.source_trust < cfg["routing"]["min_source_trust_for_llm"]:
        return "validate_only"

    # Always GPT-5 for Finnish or configured languages (local nuance)
    if item.lang.lower() in cfg["routing"]["force_gpt5_languages"]:
        return "gpt5"

    # Critical macro/finance → GPT-5
    if _contains_critical_topic(f"{item.title} {item.text}", cfg["routing"]["critical_topics"]):
        return "gpt5"

    # Complex or risky → GPT-5
    if item.complexity >= cfg["routing"]["complexity_threshold"]:
        return "gpt5"
    if item.risk >= cfg["routing"]["risk_threshold"]:
        return "gpt5"

    # Default: DeepSeek (volume work)
    return "deepseek"
