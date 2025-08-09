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
		echo "Downloaded artifact (if available) to artifacts/report.enriched.json"
	@python scripts/validate_enriched.py || true

.PHONY: panic-mode
panic-mode:
	@RUN_URL=$$(gh run list --workflow deploy-and-watch.yml --limit 1 --json url --jq '.[0].url'); \
	RUN_ID=$$(gh run list --workflow deploy-and-watch.yml --limit 1 --json databaseId --jq '.[0].databaseId'); \
	echo "CI Run URL: $$RUN_URL"; \
	if command -v open >/dev/null 2>&1; then open "$$RUN_URL"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$$RUN_URL" >/dev/null 2>&1 || true; fi; \
	mkdir -p artifacts/ci-panic && gh run download $$RUN_ID -D artifacts/ci-panic || true; \
	FOUND=$$(find artifacts/ci-panic -type f -name 'report.enriched.json' | head -n 1); \
	if [ -n "$$FOUND" ]; then cp "$$FOUND" artifacts/report.enriched.json; fi; \
	(python3 scripts/validate_enriched.py || true); \
	(python3 scripts/build_enrich_summary_env.py > /tmp/enrich_summary.env 2>/dev/null || true); \
	if [ -f /tmp/enrich_summary.env ]; then . /tmp/enrich_summary.env; echo "Summary: $${SUMMARY:-n/a}"; echo "Lede: $${LEDE:-n/a}"; fi; \
	echo "Downloaded artifact files:"; find artifacts/ci-panic -maxdepth 2 -type f | sed 's/^/ - /'; \
	echo "Traces (if any):"; find artifacts/ci-panic -type f -name '*trace*.zip' -o -name '*.zip' | sed 's/^/ - /'; \
	echo "Open a trace with: npx playwright show-trace <path/to/trace.zip>"

.PHONY: enrich-smoke-prod-notify
enrich-smoke-prod-notify: enrich-smoke-prod
	@RUN_URL=$$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json url --jq '.[0].url'); \
		SUM=Newswire; LED=—;
	@python scripts/build_enrich_summary_env.py > /tmp/enrich_summary.env || true
		source /tmp/enrich_summary.env; \
		if [ -n "$$SLACK_WEBHOOK_URL" ]; then \
		  payload=$$(jq -nc --arg sum "$$SUMMARY" --arg le "$$LEDE" --arg url "$$RUN_URL" '{text: ("✅ Enrich smoke (manual)\n*"+$$sum+"* — "+$$le+"\nRun: "+$$url+"\nArtifact: report.enriched.json")}'); \
		  if [ -n "$$NOTIFY_DRY_RUN" ]; then \
		    echo "[dry-run] Slack payload:" && echo "$$payload"; \
		  else \
		    curl -s -X POST -H 'Content-type: application/json' --data "$$payload" "$$SLACK_WEBHOOK_URL" >/dev/null || true; \
		  fi; \
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
		  if [ -n "$$NOTIFY_DRY_RUN" ]; then \
		    echo "[dry-run] Telegram text:" && echo "$$TEXT"; \
		  else \
		    curl -s "https://api.telegram.org/bot$${TG_BOT_TOKEN}/sendMessage" \
		      --data-urlencode "chat_id=$${TG_CHAT_ID}" \
		      --data-urlencode "text=$$TEXT" \
		      --data-urlencode "parse_mode=MarkdownV2" >/dev/null || true; \
		  fi; \
		fi; \
		echo "Notified (if channels configured)."
