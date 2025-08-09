from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict

from .cursor_client import call_cursor_gpt5 as cursor_call


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


def enrich_signal(raw_signal: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    cfg = CursorGpt5Config()
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
