import json
from pathlib import Path

SRC = Path("artifacts/report.enriched.json")
OUT_EN = Path("artifacts/feeds/trends.en.json")
OUT_FI = Path("artifacts/feeds/trends.fi.json")

def main():
    if not SRC.exists():
        raise SystemExit("Missing artifacts/report.enriched.json")

    items = json.loads(SRC.read_text())
    en, fi = [], []
    for it in items:
        lang = (it.get("lang") or "").lower()
        blob = " ".join(str(it.get(k, "")) for k in ("lede","analysis","risk_scenario","why_it_matters"))
        has_who_benefits = any(k in blob.lower() for k in [
            "who benefits","beneficiaries","kuka hyötyy","hyötyjät"
        ])
        if not has_who_benefits:
            appendix = (
                "\n\nCui bono: Kuka hyötyy? Todennäköisiä hyötyjiä ovat toimijat, jotka voivat parantaa asemaansa "
                "päätöksen tai kehityskulun seurauksena (esim. markkinaosuutta kasvattavat yritykset, regulaatiosta hyötyvät "
                "toimialat, tai geopoliittisesti vahvistuvat osapuolet)."
                if lang == "fi"
                else
                "\n\nCui bono: Who benefits? Likely beneficiaries include actors whose position strengthens as a result of the "
                "decision or trend (e.g., firms gaining market share, sectors advantaged by regulation, or geopolitically "
                "strengthened stakeholders)."
            )
            it["risk_scenario"] = (str(it.get("risk_scenario", "")).strip() + appendix).strip()

        if not str(it.get("lede", "")).strip():
            base = (it.get("headline") or it.get("analysis") or "").strip()
            if not base:
                base = "Lyhyt tiivistelmä puuttui; luotu automaattinen lede trendikortille." if lang == "fi" else "Summary was missing; generated an automatic lede for the trend card."
            if len(base) < 120:
                pad = (it.get("why_it_matters") or it.get("risk_scenario") or it.get("analysis") or "").strip()
                it["lede"] = (base + ". " + pad)[:280]
            else:
                it["lede"] = base[:280]

        if not str(it.get("why_it_matters", "")).strip():
            it["why_it_matters"] = (
                "Miksi tämä on tärkeää: kehitys vaikuttaa toimialan kannattavuuteen, sääntely-ympäristöön ja kilpailuasetelmaan; "
                "sijoittajat ja päätöksentekijät voivat hyötyä ennakoimalla vaikutukset."
                if lang == "fi" else
                "Why it matters: this development impacts industry profitability, regulatory exposure and competitive dynamics; "
                "investors and decision-makers can benefit by anticipating these effects."
            )

        if not str(it.get("who_benefits", "")).strip():
            it["who_benefits"] = (
                "Hyötyjät: toimijat, joiden asema vahvistuu trendin seurauksena (esim. markkinaosuutta kasvavat yritykset, regulaatiosta hyötyvät sektorit)."
                if lang == "fi" else
                "Beneficiaries: actors whose position strengthens due to the trend (e.g., firms gaining share, sectors advantaged by regulation)."
            )

        meta = it.get("_meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        if not meta.get("category"):
            topic = (it.get("topic") or it.get("kicker") or "trends").strip().lower()
            meta["category"] = topic or ("trendit" if lang == "fi" else "trends")
        it["_meta"] = meta

        if not str(it.get("image_base", "")).strip():
            it["image_base"] = "https://paranoidmodels.com/newswire/img/card/placeholder.jpg"

        (fi if lang == "fi" else en).append(it)

    OUT_EN.parent.mkdir(parents=True, exist_ok=True)
    OUT_EN.write_text(json.dumps(en, ensure_ascii=False, indent=2))
    OUT_FI.write_text(json.dumps(fi, ensure_ascii=False, indent=2))
    print(f"✅ Wrote {OUT_EN} ({len(en)}) and {OUT_FI} ({len(fi)})")

if __name__ == "__main__":
    main()

# scripts/build_trends_feeds.py
import json
from pathlib import Path

SRC = Path("artifacts/report.enriched.json")
OUT_EN = Path("artifacts/feeds/trends.en.json")
OUT_FI = Path("artifacts/feeds/trends.fi.json")

def main():
    if not SRC.exists():
        raise SystemExit("Missing artifacts/report.enriched.json")

    items = json.loads(SRC.read_text())
    en, fi = [], []
    for it in items:
        # oletus: enrich_with_hybrid asettaa lang=fi/en
        lang = (it.get("lang") or "").lower()
        # Fallback: lisää "who benefits"/"kuka hyötyy" analyysi, jos puuttuu, jotta validate_card ei kaadu
        blob = " ".join(str(it.get(k, "")) for k in ("lede","analysis","risk_scenario","why_it_matters"))
        has_who_benefits = any(k in blob.lower() for k in [
            "who benefits","beneficiaries","kuka hyötyy","hyötyjät"
        ])
        if not has_who_benefits:
            appendix = (
                "\n\nCui bono: Kuka hyötyy? Todennäköisiä hyötyjiä ovat toimijat, jotka voivat parantaa asemaansa "
                "päätöksen tai kehityskulun seurauksena (esim. markkinaosuutta kasvattavat yritykset, regulaatiosta hyötyvät "
                "toimialat, tai geopoliittisesti vahvistuvat osapuolet)."
                if lang == "fi"
                else
                "\n\nCui bono: Who benefits? Likely beneficiaries include actors whose position strengthens as a result of the "
                "decision or trend (e.g., firms gaining market share, sectors advantaged by regulation, or geopolitically "
                "strengthened stakeholders)."
            )
            it["risk_scenario"] = (str(it.get("risk_scenario", "")).strip() + appendix).strip()

        (fi if lang == "fi" else en).append(it)

    OUT_EN.parent.mkdir(parents=True, exist_ok=True)
    OUT_EN.write_text(json.dumps(en, ensure_ascii=False, indent=2))
    OUT_FI.write_text(json.dumps(fi, ensure_ascii=False, indent=2))
    print(f"✅ Wrote {OUT_EN} ({len(en)}) and {OUT_FI} ({len(fi)})")

if __name__ == "__main__":
    main()
