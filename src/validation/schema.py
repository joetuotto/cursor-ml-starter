# src/validation/schema.py
REQUIRED_FIELDS = [
    "kicker","headline","lede","analysis","risk_scenario","why_it_matters","sources","lang"
]

FORBIDDEN_PHRASES = [
    "multi-source data fusion", "advanced intelligence analysis",
    "high confidence without evidence", "vague", "general statement"
]

def validate_card(card: dict) -> list[str]:
    errs = []
    for f in REQUIRED_FIELDS:
        if f not in card or not str(card[f]).strip():
            errs.append(f"Missing or empty: {f}")

    if "sources" in card:
        src = card["sources"]
        if not isinstance(src, list) or len(src) < 2:
            errs.append("Need >= 2 sources")
        if any("example.com" in s or "example.eu" in s for s in src):
            errs.append("Example source left in output")

    blob = " ".join(str(card.get(k, "")) for k in ("lede","analysis","risk_scenario","why_it_matters"))
    for p in FORBIDDEN_PHRASES:
        if p.lower() in blob.lower():
            errs.append(f"Forbidden phrase: {p}")

    # "dark tolerance": must include worst-case + cui bono
    if "risk_scenario" in card:
        has_who_benefits = (
            "who benefits" in blob.lower() or 
            "beneficiaries" in blob.lower() or
            "kuka hyötyy" in blob.lower() or
            "hyötyjät" in blob.lower()
        )
        if not has_who_benefits:
            errs.append("Missing 'who benefits' analysis")

    return errs
