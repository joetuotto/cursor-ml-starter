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
        (fi if it.get("lang") == "fi" else en).append(it)

    OUT_EN.parent.mkdir(parents=True, exist_ok=True)
    OUT_EN.write_text(json.dumps(en, ensure_ascii=False, indent=2))
    OUT_FI.write_text(json.dumps(fi, ensure_ascii=False, indent=2))
    print(f"✅ Wrote {OUT_EN} ({len(en)}) and {OUT_FI} ({len(fi)})")

if __name__ == "__main__":
    main()
