import os
import time
import json
import hashlib
from typing import Dict, Any
from src.hybrid.providers.cursor_gpt5 import CursorGpt5Provider
from src.hybrid.budget import (
    estimate_cost_eur as budget_estimate_cost_eur, 
    record_usage, 
    stats, 
    should_throttle, 
    hard_cap_hit, 
    push_prom,
    notify_slack
)

# HUOM: Toteuta oikeat API-kutsut omien SDK:ien mukaan.
# Tässä placeholder-rajapinnat, joita voi korvata helpposti.

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def deepseek_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    # TODO: korvaa DeepSeekin oikealla kutsulla
    # Simuloidaan vastaus
    time.sleep(0.1)
    
    # Record simulated usage
    input_tokens = estimate_tokens(payload.get('title', '') + payload.get('summary', ''))
    output_tokens = 150  # Simulated output
    record_usage("deepseek", input_tokens, output_tokens, meta={"simulated": True})
    
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
    
    # Record simulated usage
    input_tokens = estimate_tokens(payload.get('title', '') + payload.get('summary', ''))
    output_tokens = 250  # Simulated output for premium model
    record_usage("gpt5_cursor", input_tokens, output_tokens, meta={"simulated": True})
    
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

def run_llm(route, prompt, want_json=True):
    """
    Budget-aware LLM runner with soft/hard cap logic
    """
    provider = route.get("provider","deepseek")
    original_provider = provider
    
    # 1) Hard cap → jäädytys / halpa fallback
    if hard_cap_hit():
        # pakota deepseek_only tai palauta minimikortti
        if provider != "deepseek":
            route["provider"] = "deepseek"
            route["reason"] = "hard_cap_fallback"
            provider = "deepseek"
            # Notify about hard cap
            s = stats()
            notify_slack(f"⛔ Hard cap reached: spent €{s['spent']:.2f} / hard €{s['hard']:.2f} — forcing deepseek_only")
    
    # 2) Soft cap → throttle: aggressiivisempi reititys halvempaan
    elif should_throttle() and route.get("provider_tag") != "gpt5_cursor_critical":
        if provider == "gpt5_cursor":
            route["provider"] = "deepseek"
            route["reason"] = "soft_cap_throttle"
            provider = "deepseek"
            # Notify about soft cap throttling
            s = stats()
            if original_provider != provider:
                notify_slack(f"⚠️ Soft cap reached: spent €{s['spent']:.2f} / €{s['soft']:.2f} — throttling to DeepSeek")

    # 3) Tee varsinainen LLM-kutsu
    if provider == "deepseek":
        resp = deepseek_analyze(prompt)
        usage = {"input_tokens": estimate_tokens(str(prompt)), "output_tokens": 150}
    else:  # gpt5_cursor
        resp = gpt5_analyze(prompt)
        usage = {"input_tokens": estimate_tokens(str(prompt)), "output_tokens": 250}

    # 4) Kirjaa kustannus (already done in analyze functions, but push metrics)
    try:
        push_prom()
    except Exception:
        pass

    return resp, usage

def make_provider(kind: str, cfg: dict):
    """Provider factory function"""
    if kind == "cursor":
        return CursorGpt5Provider(
            base_url=cfg["base_url"],
            api_key=os.environ[cfg.get("api_key_env", "CURSOR_API_KEY")],
            model=cfg["model"],
            timeout_s=int(cfg.get("timeout_s", 45)),
            max_output_tokens=int(cfg.get("max_output_tokens", 1200)),
        )
    elif kind == "deepseek":
        # Placeholder for DeepSeek provider
        return None  # TODO: Implement DeepSeek provider
    else:
        raise ValueError(f"Unknown provider kind: {kind}")
