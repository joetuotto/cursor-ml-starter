from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from .cursor_client import call_cursor_gpt5 as cursor_call

# --- HYBRID LLM drop-in ---
try:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))
    
    from src.hybrid.enrich import route_request, build_messages, run_llm
    from src.hybrid.models import make_provider
    from src.hybrid.providers.cursor_gpt5 import CursorGpt5Provider
    from src.hybrid.budget import (
        estimate_cost_eur as _budget_estimate_cost_eur,
        record_usage as _budget_record_usage,
        stats as _budget_stats,
        should_throttle as _budget_should_throttle,
        hard_cap_hit as _budget_hard_cap_hit,
        should_daily_throttle as _budget_should_daily_throttle,
        daily_hard_cap_hit as _budget_daily_hard_cap_hit,
        push_prom as _budget_push_prom,
        notify_slack as _budget_notify_slack,
    )
except Exception as e:
    # Debug: print what went wrong
    print(f"❌ Hybrid import failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Salli paikallinen ajaminen vaikka hybrid-moduuli ei olisi vielä asennettu
    route_request = None
    build_messages = None
    run_llm = None
    make_provider = None
    CursorGpt5Provider = None
    _budget_estimate_cost_eur = lambda *args: 0.0
    _budget_record_usage = lambda *args, **kwargs: None
    _budget_stats = lambda: {"spent": 0, "soft": 25.5, "hard": 37.5, "month": "none"}
    _budget_should_throttle = lambda: False
    _budget_hard_cap_hit = lambda: False
    _budget_should_daily_throttle = lambda: False
    _budget_daily_hard_cap_hit = lambda: False
    _budget_push_prom = lambda: None
    _budget_notify_slack = lambda msg: None


@dataclass
class CursorGpt5Config:
    temperature: float = 0.3
    top_p: float = 0.9
    max_tokens: int = 2200
    seed: int = 42
    retries: int = 2
    backoff_seconds: tuple[float, float] = (2.0, 5.0)


# Transport is provided by cursor_client.call_cursor_gpt5


def validate_against_schema(obj: Dict[str, Any], schema: Dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("jsonschema package is required for validation") from exc

    jsonschema.validate(instance=obj, schema=schema)


def sanitize_svg(svg_text: str, allowed_palette: list[str]) -> str:
    # Minimal palette enforcement: ensure only allowed hex colors are present
    import re

    hex_colors = set(re.findall(r"#[0-9a-fA-F]{6}", svg_text))
    disallowed = [c for c in hex_colors if c not in set(allowed_palette)]
    if disallowed:
        raise ValueError(f"SVG contains disallowed colors: {sorted(disallowed)}")
    return svg_text


# Kevyt skeemavalidaattori
REQUIRED_FIELDS = ["kicker", "headline", "lede", "why_it_matters", "cta", "timestamp"]

def _validate_card(card: Dict[str, Any]) -> List[str]:
    errs = []
    for k in REQUIRED_FIELDS:
        if k not in card or card[k] in (None, "", []):
            errs.append(f"missing_or_empty:{k}")
    # muutama fiksu tarkistus
    if "cta" in card and isinstance(card["cta"], dict):
        if "href" not in card["cta"] or not str(card["cta"]["href"]).startswith(("http://", "https://")):
            errs.append("invalid:cta.href")
    return errs


def build_system_prompt() -> str:
    return (
        'You are a careful news synthesizer for "Paranoid Newswire". '
        "Your job is to turn model signals into clear, truthful, minimally "
        "sensational news briefs for non-experts. "
        "Be precise, avoid hype, quantify impacts, cite sources, and output "
        "STRICT JSON that passes the provided JSON Schema. "
        "Include a minimal symbolist SVG illustration that matches the signal "
        "category, using only the allowed palette and simple shapes."
    )


def build_user_prompt(raw_signal_json: str) -> str:
    return "\n".join(
        [
            "TASK:",
            (
                "Turn the following paranoid-model signal into a reader-"
                "friendly news brief card and a matching minimal symbolist SVG."
            ),
            "",
            "AUDIENCE:",
            "Smart readers without stats background. Keep it concise and explanatory.",
            "",
            "TONE:",
            (
                "Sober, confident, FT-style with a subtle facelift. No hype. "
                "Numbers over adjectives."
            ),
            "",
            "BRAND PALETTE:",
            "- Dark Blue: #0A2342",
            "- Accent Orange: #FF7A00",
            "- Paper: #F2F4F7",
            "- Anchor: #1A1F2B",
            "",
            "LAYOUT HINTS:",
            "- kicker, title, lede, why_it_matters (bullets), confidence, fact_checks",
            "- symbolic_art: SVG (viewBox 0 0 320 180), palette only, alt text",
            "- visual_tag, cta (label,url)",
            "",
            "CATEGORY→ICON GUIDE:",
            (
                "geopolitics: compass / routes; economy: candles+line; bio_health: "
                "cell nucleus; climate_energy: sun/wind/leaf; cyber_tech: "
                "circuit/lock; socio_culture: bubbles; supply_chain: containers+arrow; "
                "ai_research: lambda/neurons"
            ),
            "",
            "INPUT SIGNAL (verbatim JSON):",
            raw_signal_json,
            "",
            "OUTPUT:",
            (
                "Return a SINGLE JSON object that conforms to FEED_ITEM_SCHEMA "
                "plus the extra fields described. Do not include explanations."
            ),
        ]
    )


def enrich_with_hybrid(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Drop-in: käyttää hybrid-reititystä (Cursor GPT-5 / DeepSeek) sisällön rikastamiseen.
    Palauttaa UI-yhteensopivan kortin.
    """
    # === BUDGET RUNTIME GUARDS ===
    try:
        budget_stats = _budget_stats()
        if _budget_hard_cap_hit():
            print("⛔ Hard cap reached — forcing deepseek_only mode")
            os.environ["LLM_PROVIDER_MODE"] = "deepseek_only"
            _budget_notify_slack(f"⛔ Hard cap reached: spent €{budget_stats['spent']:.2f} / hard €{budget_stats['hard']:.2f} — forcing deepseek_only")
        elif _budget_should_throttle():
            print("⚠️ Soft cap reached — throttling premium usage")
            _budget_notify_slack(f"⚠️ Soft cap reached: spent €{budget_stats['spent']:.2f} / €{budget_stats['soft']:.2f} — throttling premium usage")
    except Exception:
        # Continue if budget module fails
        pass
    
    mode = os.getenv("LLM_PROVIDER_MODE", "hybrid").lower()
    if mode not in ("hybrid", "cursor_only", "deepseek_only"):
        mode = "hybrid"

    # Basic availability check - modules should be imported successfully above
    # if route_request is None or build_messages is None or CursorGpt5Provider is None:
    #     raise RuntimeError("Hybrid modules not available. Run `make hybrid-setup` or check src/hybrid/*.")

    # 1) Prep content
    content = f"""
    Title: {item.get('title', '')}
    Summary: {item.get('summary_raw', item.get('text', ''))}
    Source: {item.get('source_name', '')}
    URL: {item.get('source_url', '')}
    """

    # 2) Routing decision  
    route_item = {
        "lang": item.get("lang", item.get("language", "en")),
        "country": item.get("country", item.get("origin_country", "XX")),
        "topic": item.get("topic", "general"),
        "risk": item.get("risk", 0.3),
        "complexity": item.get("complexity", 0.3)
    }
    
    provider_name = route_request(route_item, {"routing": {
        "force_gpt5_languages": ["fi"],
        "critical_topics": ["fed", "ecb", "suomen pankki", "korko", "central banking"],
        "risk_threshold": 0.40,
        "complexity_threshold": 0.50
    }})

    # 3) Override mode if specified
    if mode == "cursor_only":
        provider_name = "gpt5_cursor"
    elif mode == "deepseek_only":
        provider_name = "deepseek"

    # 3b) Budget guards (soft/hard caps)
    is_critical = False
    try:
        # Critical if Finnish or topic contains critical keywords
        lang_lc = str(route_item.get("lang", "")).lower()
        topic_lc = str(route_item.get("topic", "")).lower()
        critical_kw = ["fed", "ecb", "central bank", "keskuspankki", "suomen pankki", "korko"]
        is_critical = (lang_lc == "fi") or any(k in topic_lc for k in critical_kw) or route_item.get("risk", 0) >= 0.6 or route_item.get("complexity", 0) >= 0.6
    except Exception:
        is_critical = False

    # 0) Daily guards first
    if _budget_daily_hard_cap_hit and _budget_daily_hard_cap_hit():
        if provider_name != "deepseek":
            provider_name = "deepseek"
            route_reason = "daily_hard_cap_fallback"
        else:
            route_reason = "daily_hard_cap_deepseek"
    elif _budget_should_daily_throttle and _budget_should_daily_throttle() and not is_critical:
        if provider_name == "gpt5_cursor":
            provider_name = "deepseek"
            route_reason = "daily_soft_cap_throttle"
        else:
            route_reason = "daily_soft_cap_noop"
    # 1) Monthly guards
    elif _budget_hard_cap_hit and _budget_hard_cap_hit():
        if provider_name != "deepseek":
            provider_name = "deepseek"
            route_reason = "hard_cap_fallback"
        else:
            route_reason = "hard_cap_deepseek"
    elif _budget_should_throttle and _budget_should_throttle() and not is_critical:
        if provider_name == "gpt5_cursor":
            provider_name = "deepseek"
            route_reason = "soft_cap_throttle"
        else:
            route_reason = "soft_cap_noop"
    else:
        route_reason = f"mode={mode}"

    # 4) Build messages
    lang = route_item["lang"]
    messages = build_messages(content, lang)

    # 5) Run LLM
    try:
        if provider_name == "gpt5_cursor":
            provider = CursorGpt5Provider(
                base_url=os.getenv("CURSOR_BASE", "https://api.cursor.sh/v1"),
                api_key=os.getenv("CURSOR_API_KEY", ""),
                model=os.getenv("CURSOR_MODEL", "gpt-5-large"),
                timeout_s=int(os.getenv("CURSOR_TIMEOUT_S", "45"))
            )
            llm_resp = provider.chat(messages, temperature=0.2)
        else:
            # Mock DeepSeek response for now
            timestamp = "2025-08-11T13:30:00Z"
            llm_resp = {
                "ok": True,
                "text": json.dumps({
                    "kicker": "Market Update",
                    "headline": item.get('title', 'News Update'),
                    "lede": f"Analysis: {item.get('title', 'Unknown')}",
                    "why_it_matters": "This development affects market dynamics.",
                    "cta": {"label": "Read more", "href": item.get('source_url', 'https://example.com')},
                    "timestamp": timestamp,
                    "locale": lang
                }),
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}
            }
    except Exception as e:
        # Fallback response
        llm_resp = {
            "ok": False,
            "error": str(e),
            "text": json.dumps({
                "kicker": "System Update",
                "headline": item.get('title', 'Processing Error'),
                "lede": "Content processing temporarily unavailable.",
                "why_it_matters": "System fallback engaged for continuity.",
                "cta": {"label": "Try again", "href": item.get('source_url', 'https://example.com')},
                "timestamp": "2025-08-11T13:30:00Z",
                "locale": lang
            })
        }

    # 6) Parse response
    if llm_resp.get("ok"):
        try:
            card = json.loads(llm_resp["text"])
        except json.JSONDecodeError:
            card = {
                "kicker": "Parse Error",
                "headline": item.get('title', 'Content Error'),
                "lede": "Response parsing failed.",
                "why_it_matters": "Technical issue resolved in fallback mode.",
                "cta": {"label": "Source", "href": item.get('source_url', 'https://example.com')},
                "timestamp": "2025-08-11T13:30:00Z"
            }
    else:
        try:
            card = json.loads(llm_resp["text"])
        except (json.JSONDecodeError, KeyError):
            card = {
                "kicker": "Response Error",
                "headline": item.get('title', 'Processing Failed'),
                "lede": "Failed to parse LLM response.",
                "why_it_matters": "System error handled gracefully.",
                "cta": {"label": "Source", "href": item.get('source_url', 'https://example.com')},
                "timestamp": "2025-08-11T13:30:00Z"
            }

    # 6b) Budget logging (best-effort)
    try:
        if _budget_record_usage is not None:
            usage = llm_resp.get("usage", {}) if isinstance(llm_resp, dict) else {}
            in_tok = int(usage.get("prompt_tokens", 800))
            out_tok = int(usage.get("completion_tokens", usage.get("output_tokens", 600)))
            eur = None
            if _budget_estimate_cost_eur is not None:
                eur = _budget_estimate_cost_eur("gpt5_cursor" if provider_name == "gpt5_cursor" else "deepseek", in_tok, out_tok)
            _budget_record_usage("gpt5_cursor" if provider_name == "gpt5_cursor" else "deepseek", in_tok, out_tok, eur, meta={"reason": route_reason})
            if _budget_push_prom is not None:
                _budget_push_prom()
            if _budget_stats is not None and _budget_notify_slack is not None:
                s = _budget_stats()
                if s.get("spent", 0) >= s.get("soft", 0):
                    _budget_notify_slack(f"⚠️ Soft cap reached: spent €{s['spent']:.2f} / €{s['soft']:.2f}")
                if s.get("spent", 0) >= s.get("hard", 0):
                    _budget_notify_slack(f"⛔ Hard cap reached: spent €{s['spent']:.2f} / hard €{s['hard']:.2f} — forcing deepseek_only")
    except Exception:
        pass

    # 7) Validation and metadata
    errs = _validate_card(card)
    card.setdefault("_meta", {})
    card["_meta"]["validation"] = {"errors": errs, "ok": len(errs) == 0}
    card["_meta"]["routing"] = {
        "provider": provider_name,
        "reason": route_reason,
        "risk_score": route_item["risk"],
        "complexity": route_item["complexity"],
    }

    return card


def enrich_signal(raw_signal: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich signal using PARANOID model with Finnish localization support"""
    cfg = CursorGpt5Config()
    
    # Detect origin country for Finnish prompts
    origin_country = raw_signal.get('origin_country', 'US')
    
    # Use Finnish prompts if available
    if origin_country == 'FI':
        try:
            from ..prompts.enrich_fi import get_prompt_template
            system_prompt, user_template = get_prompt_template(origin_country)
            
            # Format Finnish template
            user_prompt = user_template.format(
                title=raw_signal.get('title', ''),
                source_name=raw_signal.get('source_name', ''),
                source_url=raw_signal.get('source_url', ''),
                published_at=raw_signal.get('published_at', ''),
                summary_raw=raw_signal.get('summary_raw', ''),
                category_guess=raw_signal.get('category_guess', ''),
                origin_country=origin_country
            )
        except ImportError:
            # Fallback to original prompts
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(json.dumps(raw_signal, ensure_ascii=False))
    else:
        # Use enhanced English prompts
        try:
            from ..prompts.enrich_fi import get_prompt_template
            system_prompt, user_template = get_prompt_template(origin_country)
            
            user_prompt = user_template.format(
                title=raw_signal.get('title', ''),
                source_name=raw_signal.get('source_name', ''),
                source_url=raw_signal.get('source_url', ''),
                published_at=raw_signal.get('published_at', ''),
                summary_raw=raw_signal.get('summary_raw', ''),
                category_guess=raw_signal.get('category_guess', ''),
                origin_country=origin_country
            )
        except ImportError:
            # Fallback to original prompts
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(json.dumps(raw_signal, ensure_ascii=False))

    for attempt in range(cfg.retries + 1):
        try:
            result = cursor_call(
                system=system_prompt,
                user=user_prompt,
                model="gpt-5",
                temperature=cfg.temperature,
                top_p=cfg.top_p,
                max_tokens=cfg.max_tokens,
                seed=cfg.seed,
                retries=cfg.retries,
            )
            validate_against_schema(result, schema)
            
            # Additional quality validation for Finnish content
            if origin_country == 'FI':
                try:
                    from ..prompts.enrich_fi import validate_enrichment
                    validation_result = validate_enrichment(result, origin_country)
                    if not validation_result['valid']:
                        raise ValueError(f"Finnish quality validation failed: {validation_result['errors']}")
                except ImportError:
                    pass  # Skip quality validation if module not available
            
            # Palette guard for SVG
            allowed = ["#0A2342", "#FF7A00", "#F2F4F7", "#1A1F2B"]
            if "symbolic_art" in result and isinstance(result["symbolic_art"], dict):
                svg = result["symbolic_art"].get("svg", "")
                if svg:
                    sanitize_svg(svg, allowed)
            return result
        except Exception:  # schema or palette failure
            if attempt < cfg.retries:
                time.sleep(cfg.backoff_seconds[min(attempt, len(cfg.backoff_seconds) - 1)])
                # Ask model to fix only schema violations next
                user_prompt = user_prompt + (
                    "\n\nNote: return the SAME object, fix only schema violations."
                )
                continue
            raise


def write_enriched_report(obj: Dict[str, Any], out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return out_path
