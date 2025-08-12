import json
from pathlib import Path

ENRICHED = Path("artifacts/report.enriched.json")


def ensure_text(value: str) -> str:
    return (value or "").strip()


def main() -> None:
    if not ENRICHED.exists():
        print("[normalize] skip: no artifacts/report.enriched.json")
        return

    data = json.loads(ENRICHED.read_text())

    # Robustly derive items and remember original shape
    output_is_dict = False
    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            items = list(data["items"])  # shallow copy
            output_is_dict = True
        else:
            items = [data]
            output_is_dict = False
    elif isinstance(data, list):
        items = list(data)
        output_is_dict = False
    else:
        print(f"[normalize] unsupported data shape: {type(data)} — skipping")
        return

    for item in items:
        # Defensive: coerce to dict if somehow not
        if not isinstance(item, dict):
            continue

        lang = ensure_text(item.get("lang")).lower()

        # Build blob for checks
        blob = " ".join(
            ensure_text(item.get(k, "")) for k in ("lede", "analysis", "risk_scenario", "why_it_matters")
        )

        # Lede fallback: ensure presence and reasonable length
        if not ensure_text(item.get("lede")):
            base = ensure_text(item.get("headline") or item.get("analysis"))
            if not base:
                base = (
                    "Lyhyt tiivistelmä puuttui; luotu automaattinen lede trendikortille."
                    if lang == "fi"
                    else "Summary was missing; generated an automatic lede."
                )
            if len(base) < 120:
                pad = ensure_text(item.get("why_it_matters") or item.get("risk_scenario") or item.get("analysis"))
                item["lede"] = (base + ". " + pad)[:280]
            else:
                item["lede"] = base[:280]

        # why_it_matters fallback
        if not ensure_text(item.get("why_it_matters")):
            item["why_it_matters"] = (
                "Miksi tämä on tärkeää: kehitys vaikuttaa toimialan kannattavuuteen, regulaatioriskeihin ja kilpailuun; vaikutusten ennakointi luo etua."
                if lang == "fi"
                else "Why it matters: impacts profitability, regulatory exposure and competition; anticipating effects creates advantage."
            )

        # risk_scenario must include cui bono-like analysis
        cui_markers = ["who benefits", "beneficiaries", "kuka hyötyy", "hyötyjät"]
        if not any(m in blob.lower() for m in cui_markers):
            appendix = (
                "\n\nCui bono: Kuka hyötyy? Todennäköisiä hyötyjiä ovat toimijat, joiden asema vahvistuu kehityksen seurauksena."
                if lang == "fi"
                else "\n\nCui bono: Who benefits? Likely beneficiaries are actors whose position strengthens as a result of the development."
            )
            item["risk_scenario"] = (ensure_text(item.get("risk_scenario")) + appendix).strip()

        # who_benefits field (explicit)
        if not ensure_text(item.get("who_benefits")):
            item["who_benefits"] = (
                "Hyötyjät: markkina-asemaa vahvistavat yritykset, regulaatiosta hyötyvät sektorit."
                if lang == "fi"
                else "Beneficiaries: firms gaining share, sectors advantaged by regulation."
            )

        # _meta.category
        meta = item.get("_meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        if not ensure_text(meta.get("category")):
            topic = ensure_text(item.get("topic") or item.get("kicker") or "trends").lower()
            meta["category"] = topic or ("trendit" if lang == "fi" else "trends")
        item["_meta"] = meta

        # image_base absolute placeholder if missing
        if not ensure_text(item.get("image_base")):
            item["image_base"] = "https://paranoidmodels.com/newswire/img/card/placeholder.jpg"

    # Write back preserving original shape
    out = {"items": items} if output_is_dict else items
    ENRICHED.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[normalize] normalized {len(items)} item(s) in {ENRICHED}")


if __name__ == "__main__":
    main()


