import os, json
from pathlib import Path
from .router import route, Item
from .models import deepseek_analyze, gpt5_analyze, estimate_tokens, estimate_cost_eur
from .cache import get_cache, set_cache, make_item_key
from .validate import validate_card

def _to_card(item: Item, res: dict) -> dict:
    return {
        "kicker": "Paranoid Analysis",
        "headline": item.title,
        "lede": res["analysis"],
        "why_it_matters": res["why_it_matters"],
        "cta": {"href": item.url or "#", "label": "Lähde"},
        "timestamp": None,
        "category": res.get("category","standard"),
        "model": res.get("model"),
        "sources": res.get("sources",[]),
        "confidence": res.get("confidence",0.5),
        "lang": item.lang,
        "country": item.country,
    }

def run_batch(items: list[Item], cfg: dict) -> list[dict]:
    out = []
    cache_dir = cfg["cache"]["dir"]
    ttl = cfg["cache"]["ttl_hours"]
    prompt_version = cfg["cache"]["prompt_version"]

    for it in items:
        r = route(it, cfg)
        key = make_item_key(it, prompt_version)
        cached = get_cache(cache_dir, key, ttl)
        if cached:
            out.append(cached); continue

        payload = {
            "title": it.title,
            "text": it.text,
            "lang": it.lang,
            "guessed_sources": [it.url] if it.url else [],
        }

        tokens = estimate_tokens(it.text)
        if r == "deepseek":
            res = deepseek_analyze(payload)
            cost = estimate_cost_eur("deepseek", tokens, cfg)
        elif r == "gpt5":
            res = gpt5_analyze(payload)
            cost = estimate_cost_eur("gpt5", tokens, cfg)
        else:  # validate_only
            res = {
                "model": "validate_only",
                "analysis": it.text[:140],
                "category": "validation",
                "why_it_matters": "",
                "sources": [],
                "confidence": 0.4,
            }
            cost = 0.0

        card = _to_card(it, res)
        ok, errs = validate_card(card, cfg)
        if not ok and r != "gpt5":
            # korjaus GPT-5:llä (= "rewrite")
            res2 = gpt5_analyze(payload)
            card = _to_card(it, res2)

        set_cache(cache_dir, key, card)
        out.append(card)
    return out

def save_newswire(cards: list[dict], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
