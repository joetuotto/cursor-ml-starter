import json
from pathlib import Path

p = Path("artifacts/report.enriched.json")
summary, lede = "Newswire", "—"
if p.exists():
    d = json.loads(p.read_text())
    if isinstance(d, list):
        d = d[0] if d else {}
    summary = (d.get("kicker") or d.get("category") or summary)[:80]
    lede_txt = d.get("lede") or d.get("summary") or ""
    lede = " ".join(str(lede_txt).split())[:240] or lede

print(f"SUMMARY={summary}")
print(f"LEDE={lede}")
