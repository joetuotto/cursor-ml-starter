# src/writing/hersh_style.py
from typing import Dict, Any

HEDGING = [
    "advanced intelligence analysis", "multi-source data fusion",
    "experts say", "it appears", "reportedly", "may indicate"
]

def hershify_prompt(lang: str) -> str:
    base = f"""
You are an investigative reporter in the style of Seymour Hersh:
- concrete, document-heavy, skeptical, terse sentences
- always answer: who benefits, what's the plausible covert mechanism, and worst-case scenario
- avoid vague phrases ({", ".join(HEDGING)}). Replace with specifics or admit unknowns explicitly.
- include 2–4 short paragraphs max
- include a final 'Risk scenario' paragraph
- include 2–5 sources (urls or citation notes). No fabrications.

JSON schema to output (MUST be valid JSON):
{{
  "kicker": "...",
  "headline": "...",
  "lede": "...",
  "analysis": "...",           # investigative context + hidden dynamics
  "risk_scenario": "...",      # explicit worst-case
  "why_it_matters": "...",     # reader relevance
  "sources": ["...", "..."],   # 2-5 items
  "lang": "{lang}"             # 'en' or 'fi'
}}
"""
    if lang.lower() == "fi":
        base = base.replace(
            "You are an investigative reporter in the style of Seymour Hersh:",
            "Kirjoitat tutkivan journalismin tyylillä (Seymour Hersh -henkinen):"
        ).replace(
            "Risk scenario", "Riskiskenaario"
        ).replace(
            "sources", "lähteet"
        ).replace(
            '"lang": "en"', '"lang": "fi"'
        )
    return base

def enforce_tone(card: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Light post-filter: trim hedging/yleispuhe, ensure minimal fields populated."""
    def clean(s: str) -> str:
        if not s: return s
        out = s.strip()
        for h in HEDGING:
            out = out.replace(h, "").replace(h.title(), "")
        return out

    for k in ("lede", "analysis", "risk_scenario", "why_it_matters", "headline"):
        if k in card:
            card[k] = clean(card[k])
    card["lang"] = lang.lower()
    return card
