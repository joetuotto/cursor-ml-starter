import os
import time
import json
import hashlib
from typing import Dict, Any

# HUOM: Toteuta oikeat API-kutsut omien SDK:ien mukaan.
# Tässä placeholder-rajapinnat, joita voi korvata helpposti.

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def deepseek_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    # TODO: korvaa DeepSeekin oikealla kutsulla
    # Simuloidaan vastaus
    time.sleep(0.1)
    return {
        "model": "deepseek",
        "analysis": f"[DS] {payload['title'][:80]}",
        "category": "standard",
        "why_it_matters": "Adds context for general readers.",
        "sources": payload.get("guessed_sources", [])[:3],
        "confidence": 0.74,
    }

def gpt5_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    # TODO: käytä Cursor/OpenAI clienttiä GPT-5:lle
    # Simuloidaan vastaus
    time.sleep(0.2)
    lang = payload.get("lang","en")
    why = "Miksi tämä on tärkeää" if lang == "fi" else "Why it matters"
    return {
        "model": "gpt5",
        "analysis": f"[GPT5] {payload['title'][:80]}",
        "category": "premium",
        "why_it_matters": f"{why}: tarkka vaikutus lukijalle.",
        "sources": payload.get("guessed_sources", [])[:5],
        "confidence": 0.86,
    }

def estimate_tokens(text: str) -> int:
    # erittäin karkea arvio
    return max(1, int(len(text) / 4))

def estimate_cost_eur(model: str, prompt_tokens: int, cfg) -> float:
    if model == "deepseek":
        return (prompt_tokens / 1000) * float(os.getenv("DEEPSEEK_COST_PER_1K_TOKENS","0.0012"))
    return (prompt_tokens / 1000) * float(os.getenv("GPT5_COST_PER_1K_TOKENS","0.02"))
