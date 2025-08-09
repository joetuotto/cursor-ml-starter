.PHONY: enrich

enrich:
	python -m src.cli enrich \
		--signal artifacts/signal.raw.json \
		--schema artifacts/feed_item_schema.json \
		--out artifacts/report.enriched.json

.PHONY: enrich-smoke-prod
enrich-smoke-prod:
	gh workflow run post-merge-enrich-smoke.yml --ref main
	@echo "Waiting for run to register..."
	@sleep 3
	@RUN_URL=$$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json url --jq '.[0].url'); \
		echo "Run URL: $$RUN_URL"; \
		if command -v open >/dev/null 2>&1; then open "$$RUN_URL"; \
		elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$$RUN_URL" >/dev/null 2>&1 || true; \
		fi
	@RUN_ID=$$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json databaseId --jq '.[0].databaseId'); \
		mkdir -p artifacts && gh run download $$RUN_ID --name report.enriched.json -D artifacts || true; \
		echo "Downloaded artifact (if available) to artifacts/report.enriched.json"; \
		python - <<'PY' || true
import json, sys
from pathlib import Path
try:
    import jsonschema
except Exception:
    print("[info] jsonschema not installed; skipping schema validation")
    sys.exit(0)
sch_p = Path('artifacts/feed_item_schema.json')
doc_p = Path('artifacts/report.enriched.json')
if not doc_p.exists() or not sch_p.exists():
    print("[info] artifact or schema missing; skip validation")
    sys.exit(0)
schema = json.loads(sch_p.read_text())
doc = json.loads(doc_p.read_text())
items = doc.get('items', doc if isinstance(doc, list) else [doc])
for it in items:
    jsonschema.validate(it, schema)
print(f"[ok] schema validation passed for {len(items)} item(s)")
PY
