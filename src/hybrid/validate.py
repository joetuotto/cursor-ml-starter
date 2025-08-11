def validate_card(card: dict, cfg) -> tuple[bool, list[str]]:
    errs = []
    if not card.get("headline"):
        errs.append("headline missing")
    if not card.get("lede"):
        errs.append("lede missing")
    if len(card.get("sources",[])) < cfg["quality"]["require_sources_min"]:
        errs.append("not enough sources")
    if not card.get("why_it_matters"):
        errs.append("why_it_matters missing")
    return (len(errs) == 0, errs)
