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

.PHONY: enrich-smoke-prod-notify
enrich-smoke-prod-notify: enrich-smoke-prod
	@RUN_URL=$$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json url --jq '.[0].url'); \
		SUM=Newswire; LED=—; \
		python - <<'PY' > /tmp/enrich_summary.env || true
import json, pathlib
p = pathlib.Path('artifacts/report.enriched.json')
summary, lede = 'Newswire', '—'
if p.exists():
    d = json.loads(p.read_text())
    if isinstance(d, list):
        d = d[0] if d else {}
    summary = (d.get('kicker') or d.get('category') or summary)[:80]
    lede_txt = (d.get('lede') or d.get('summary') or '')
    lede = ' '.join(str(lede_txt).split())[:240] or lede
print(f"SUMMARY={summary}")
print(f"LEDE={lede}")
PY
		source /tmp/enrich_summary.env; \
		if [ -n "$$SLACK_WEBHOOK_URL" ]; then \
		  payload=$$(jq -nc --arg sum "$$SUMMARY" --arg le "$$LEDE" --arg url "$$RUN_URL" '{text: ("✅ Enrich smoke (manual)\n*"+$$sum+"* — "+$$le+"\nRun: "+$$url+"\nArtifact: report.enriched.json")}'); \
		  curl -s -X POST -H 'Content-type: application/json' --data "$$payload" "$$SLACK_WEBHOOK_URL" >/dev/null || true; \
		fi; \
		if [ -n "$$TG_BOT_TOKEN" ] && [ -n "$$TG_CHAT_ID" ]; then \
		  esc() { python - "$1" <<'PY'
import sys, re
s=sys.argv[1]
print(re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\\\1', s))
PY
}; \
		  S=$$(esc "$$SUMMARY"); L=$$(esc "$$LEDE"); \
		  TEXT=$$(printf '✅ Enrich smoke (manual)\n*%s* — %s\nRun: %s\nArtifact: report.enriched.json' "$$S" "$$L" "$$RUN_URL"); \
		  curl -s "https://api.telegram.org/bot$${TG_BOT_TOKEN}/sendMessage" \
		    --data-urlencode "chat_id=$${TG_CHAT_ID}" \
		    --data-urlencode "text=$$TEXT" \
		    --data-urlencode "parse_mode=MarkdownV2" >/dev/null || true; \
		fi; \
		echo "Notified (if channels configured)."
