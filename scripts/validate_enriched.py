import json
import sys
from pathlib import Path

try:
    import jsonschema  # type: ignore
except Exception:
    print("[info] jsonschema not installed; skipping schema validation")
    sys.exit(0)

schema_path = Path("artifacts/feed_item_schema.json")
doc_path = Path("artifacts/report.enriched.json")

if not doc_path.exists() or not schema_path.exists():
    print("[info] artifact or schema missing; skip validation")
    sys.exit(0)

schema = json.loads(schema_path.read_text())
doc = json.loads(doc_path.read_text())
items = doc.get("items", doc if isinstance(doc, list) else [doc])
for item in items:
    jsonschema.validate(item, schema)

print(f"[ok] schema validation passed for {len(items)} item(s)")
