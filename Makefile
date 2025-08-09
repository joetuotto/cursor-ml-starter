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
	@echo "Run URL:" && gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json url --jq '.[0].url'
	@RUN_ID=$$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json databaseId --jq '.[0].databaseId'); \
		mkdir -p artifacts && gh run download $$RUN_ID --name report.enriched.json -D artifacts || true; \
		echo "Downloaded artifact (if available) to artifacts/report.enriched.json"
