# ===== PARANOID MODEL V5 =====
.PHONY: paranoid-setup paranoid-train paranoid-signal paranoid-enrich paranoid-pipeline

paranoid-setup:
	@echo "🔧 Setting up paranoid model v5..."
	mkdir -p data artifacts config scripts
	python3 scripts/generate_mock.py --out data/paranoid_mock.csv --n 500

paranoid-train:
	@echo "🎯 Training paranoid model v5..."
	python3 scripts/train_paranoid.py \
		--config config/paranoid_v5.yaml \
		--data data/paranoid.csv --fallback data/paranoid_mock.csv \
		--outdir artifacts

paranoid-gates:
	@echo "🚦 Checking quality gates..."
	python3 scripts/quality_gates.py --metrics artifacts/metrics.json --config config/paranoid_v5.yaml

paranoid-signal:
	@echo "🚨 Generating paranoid signal..."
	python3 scripts/generate_paranoid_signal.py \
		--models artifacts/paranoid_models.joblib \
		--out artifacts/signal.raw.json \
		--n 100

paranoid-enrich:
	@echo "🤖 Enriching signal with Cursor GPT-5..."
	python -m src.cli enrich \
		--signal artifacts/signal.raw.json \
		--schema artifacts/feed_item_schema.json \
		--out artifacts/report.enriched.json

paranoid-pipeline: paranoid-setup paranoid-train paranoid-gates paranoid-signal paranoid-enrich
	@echo "✅ Full paranoid pipeline completed!"
	@echo "📊 Check artifacts/ for results"

paranoid-data:
	@echo "🌍 Fetching WGI and GDELT data..."
	python3 scripts/merge_wgi_gdelt.py \
		--download \
		--max_gdelt_files 5 \
		--out data/paranoid.csv

paranoid-data-existing:
	@echo "📁 Processing existing WGI/GDELT data..."
	python3 scripts/merge_wgi_gdelt.py \
		--wgi_dir data/raw/wgi \
		--gdelt_dir data/raw/gdelt \
		--out data/paranoid.csv

paranoid-full: paranoid-data paranoid-train paranoid-gates paranoid-signal paranoid-enrich
	@echo "🎉 COMPLETE PARANOID PIPELINE FINISHED!"
	@echo "📊 Results in artifacts/"
	@echo "📰 Enriched newswire: artifacts/report.enriched.json"
	@echo "🚨 Signal detected: artifacts/signal.raw.json"
	@echo "🤖 Models saved: artifacts/paranoid_models.joblib"

paranoid-full-mock: paranoid-setup paranoid-train paranoid-gates paranoid-signal
	@echo "🎉 PARANOID PIPELINE (MOCK DATA) FINISHED!"
	@echo "📊 Results in artifacts/ (using mock data)"
	@echo "🚨 Signal detected: artifacts/signal.raw.json"  
	@echo "💡 Run 'make paranoid-enrich' with CURSOR_API_KEY to complete"

# ===== ENHANCED PARANOID OPERATIONS =====

paranoid-humint:
	@echo "🕵️ Generating HUMINT profile..."
	python3 scripts/humint_profiler.py \
		--data data/paranoid.csv \
		--signal artifacts/signal.raw.json \
		--out artifacts/humint_profile.json

paranoid-drift:
	@echo "📊 Checking for concept drift..."
	python3 scripts/drift_detector.py \
		--metrics_dir artifacts \
		--out artifacts/drift_report.json

paranoid-smoke:
	@echo "🚨 Running paranoid smoke test..."
	cd web && node tests/e2e/paranoid.smoke.cjs

paranoid-debug:
	@echo "🔧 Debug mode data acquisition..."
	export PARANOID_DEBUG=true && \
	python3 scripts/merge_wgi_gdelt.py \
		--out data/paranoid_debug.csv \
		--debug

paranoid-temporal:
	@echo "⏰ Training with temporal cross-validation..."
	export PARANOID_TEMPORAL_CV=1 && \
	make paranoid-train

paranoid-complete: paranoid-full paranoid-humint paranoid-drift
	@echo "🎉 COMPLETE PARANOID INTELLIGENCE PIPELINE!"
	@echo "📊 Metrics: artifacts/metrics.json"
	@echo "🚨 Signal: artifacts/signal.raw.json"
	@echo "📰 Newswire: artifacts/report.enriched.json"
	@echo "🕵️ HUMINT: artifacts/humint_profile.json"
	@echo "📈 Drift: artifacts/drift_report.json"
	@echo "🎯 All intelligence products ready!"

# ===== ENTERPRISE DEPLOYMENT =====

paranoid-deploy:
	@echo "☁️ Deploying artifacts to cloud storage..."
	python3 scripts/deploy_artifacts.py \
		--provider auto \
		--artifacts_dir artifacts

paranoid-deploy-force:
	@echo "☁️ Force deploying artifacts (bypass quality gates)..."
	python3 scripts/deploy_artifacts.py \
		--provider auto \
		--artifacts_dir artifacts \
		--force

paranoid-rollback:
	@echo "🔄 Rolling back to previous backup..."
	python3 scripts/deploy_artifacts.py --rollback

paranoid-report:
	@echo "🎭 Generating comprehensive Playwright report..."
	cd web && node tests/e2e/playwright.report.cjs

paranoid-monitor:
	@echo "📊 Setting up Grafana monitoring..."
	@echo "📁 Import monitoring/grafana-paranoid-dashboard.json to Grafana"
	@echo "🔗 Dashboard URL: http://localhost:3000/dashboard/import"

paranoid-enterprise: paranoid-complete paranoid-deploy paranoid-report
	@echo "🏢 ENTERPRISE PARANOID DEPLOYMENT COMPLETE!"
	@echo "☁️ Artifacts deployed to cloud storage"
	@echo "📄 HTML test reports generated" 
	@echo "📊 Grafana dashboard ready for import"
	@echo "🎯 Production intelligence pipeline operational!"

# ===== PRODUCTION OPERATIONS =====

paranoid-health-check:
	@echo "🏥 Running production health check..."
	@python3 -c "\
import requests, json, sys; \
try: \
    r = requests.get('$(PROD_URL)/health', timeout=10); \
    health = r.json(); \
    print(f'✅ API Health: {health[\"status\"]}'); \
    print(f'📊 Model: {health[\"model_version\"]}'); \
    print(f'⏰ Uptime: {health[\"uptime_seconds\"]//3600}h'); \
    sys.exit(0 if health['status'] == 'healthy' else 1); \
except Exception as e: \
    print(f'❌ Health check failed: {e}'); \
    sys.exit(1) \
"

paranoid-production-check: paranoid-health-check paranoid-smoke paranoid-drift
	@echo "✅ Production validation complete"

# ===== PROMETHEUS & MONITORING =====

paranoid-prometheus:
	@echo "📊 Exporting metrics to Prometheus..."
	python3 scripts/prometheus_exporter.py \
		--artifacts_dir artifacts

paranoid-prometheus-push:
	@echo "📊 Pushing metrics to Prometheus Gateway..."
	python3 scripts/prometheus_exporter.py \
		--artifacts_dir artifacts \
		--pushgateway_url $(PROMETHEUS_PUSHGATEWAY_URL)

# ===== S3 LIFECYCLE MANAGEMENT =====

setup-s3-lifecycle:
	@echo "🗂️ Setting up S3 lifecycle policies..."
	python3 scripts/setup_s3_lifecycle.py \
		--bucket $(S3_BUCKET) \
		--region $(AWS_REGION) \
		--production-retention 365 \
		--backup-retention 90

setup-s3-costs:
	@echo "💰 Estimating S3 storage costs..."
	python3 scripts/setup_s3_lifecycle.py \
		--bucket $(S3_BUCKET) \
		--estimate-costs

# ===== STAGING → PRODUCTION PROMOTION =====

paranoid-staging-validate:
	@echo "🚦 Validating staging for promotion..."
	python3 scripts/staging_promote.py \
		--staging-artifacts staging_artifacts \
		--dry-run

paranoid-promote:
	@echo "🚀 Promoting staging to production..."
	python3 scripts/staging_promote.py \
		--staging-artifacts staging_artifacts

paranoid-promote-force:
	@echo "⚠️ FORCE promoting staging to production..."
	python3 scripts/staging_promote.py \
		--staging-artifacts staging_artifacts \
		--force

# ===== ULTIMATE ENTERPRISE PIPELINE =====

paranoid-cloud-run:
	PROJECT_ID=${PROJECT_ID} REGION=${REGION} SERVICE_NAME=${SERVICE_NAME} ./scripts/deploy_cloud_run.sh

paranoid-prod-check:
	@echo "🏥 Health check Cloud Runille"
	@URL=$$(gcloud run services describe $(SERVICE_NAME) --region $(REGION) --format="value(status.url)"); \
	curl -fsS $$URL/health && echo " ✅ OK" || (echo " ❌ FAIL"; exit 1)

deploy-paranoid:
	@echo "🚀 Starting self-healing PARANOID V5 deployment pipeline..."
	bash scripts/deploy_paranoid_full.sh

deploy-paranoid-with-image:
	@echo "🚀 Deploying PARANOID V5 with new container image..."
	IMAGE=$(IMAGE) bash scripts/deploy_paranoid_full.sh

rollback-paranoid:
	@echo "🔄 Executing manual rollback..."
	bash scripts/rollback_paranoid.sh

# Finnish newswire commands
fi-ingest:
	@echo "🇫🇮 Ingesting Finnish news sources..."
	python -m src.ingest_fi --output artifacts/signal.fi.json --limit 50

fi-enrich:
	@echo "🇫🇮 Enriching Finnish content..."
	python -m src.cli enrich --signal artifacts/signal.fi.json --schema artifacts/newswire_schema.json --out artifacts/report.fi.enriched.json

fi-validate:
	@echo "🇫🇮 Validating Finnish enriched content..."
	python scripts/validate_enriched.py artifacts/report.fi.enriched.json --verbose

fi-smoke:
	@echo "🇫🇮 Running Finnish newswire smoke tests..."
	cd web && PROD_URL="https://paranoid-api-2q3ac3ofma-lz.a.run.app" node tests/e2e/prod.fi.smoke.cjs

fi-e2e:
	@echo "🇫🇮 Running Finnish E2E tests..."
	cd web && PROD_URL="https://paranoid-api-2q3ac3ofma-lz.a.run.app" npx playwright test tests/e2e/fi-newswire.spec.ts --retries=1

fi-full:
	@echo "🇫🇮 Full Finnish pipeline: ingest → enrich → validate"
	make fi-ingest
	make fi-enrich  
	make fi-validate

# Hybrid LLM System (DeepSeek + GPT-5)
hybrid-enrich:
	@echo "🤖 Hybrid enrichment: DeepSeek + GPT-5"
	python -m src.paranoid_model.hybrid_llm --signal artifacts/signal.fi.json --schema artifacts/newswire_schema.json --output artifacts/report.hybrid.json

hybrid-cost:
	@echo "💰 Monthly cost summary:"
	python -m src.paranoid_model.hybrid_llm --cost-summary

hybrid-setup:
	@echo "⚙️  Setting up hybrid LLM environment..."
	@echo "1. Set DEEPSEEK_API_KEY in your environment"
	@echo "2. Set CURSOR_API_KEY in your environment"
	@echo "3. Budget: €30/month = €20 DeepSeek + €10 GPT-5"
	@echo "4. Expected volume: ~1000 articles/month mixed routing"

hybrid-test:
	@echo "🧪 Testing hybrid routing..."
	@python -c "from src.paranoid_model.hybrid_llm import HybridEnricher, ContentRouter, CostTracker; import json; tracker = CostTracker(); router = ContentRouter(tracker); test_signals = [{'title': 'Suomen Pankki nostaa korkoja', 'origin_country': 'FI', 'category_guess': 'talous'}, {'title': 'Federal Reserve signals rate pause', 'origin_country': 'US', 'category_guess': 'finance'}, {'title': 'Tech startup raises funding', 'origin_country': 'US', 'category_guess': 'technology'}]; [print(f'📰 \"{signal[\"title\"][:40]}...\" → {router.route_content(signal).value}') for signal in test_signals]; enricher = HybridEnricher(); summary = enricher.get_cost_summary(); print('\n💰 Current usage:'); [print(f'   {provider}: \${data[\"cost\"]:.2f}/\${data[\"budget\"]:.2f} ({data[\"utilization\"]*100:.1f}%)') for provider, data in summary['providers'].items()]"

hybrid-fi:
	@echo "🇫🇮 Finnish content with hybrid routing"
	make fi-ingest
	make hybrid-enrich
	make fi-validate

paranoid-ultimate: paranoid-complete paranoid-prometheus paranoid-deploy paranoid-report
	@echo "🏢 ULTIMATE PARANOID ENTERPRISE PIPELINE COMPLETE!"
	@echo "📊 Metrics exported to Prometheus"
	@echo "☁️ Artifacts deployed with lifecycle management"
	@echo "📄 Comprehensive reports generated"
	@echo "🚀 Ready for global enterprise deployment!"

# ===== SANITY CHECKS & VALIDATION =====

paranoid-sanity:
	@echo "✅ Running pre-deployment sanity checks..."
	python3 scripts/sanity_check.py

paranoid-setup-alerts:
	@echo "🚨 Setting up Prometheus alerts..."
	@echo "📁 Import monitoring/prometheus-alert-rules.yaml to Prometheus"
	@echo "📁 Import monitoring/grafana-alerts-config.json to Grafana"
	@echo "🔗 Prometheus: /etc/prometheus/rules/ or via API"
	@echo "🔗 Grafana: /api/provisioning/alert-rules"

paranoid-validate-alerts:
	@echo "🧪 Testing alert configurations..."
	@if [ -n "$(PROMETHEUS_URL)" ]; then \
		curl -s "$(PROMETHEUS_URL)/api/v1/rules" | jq '.data.groups[] | select(.name=="paranoid-model-alerts") | .rules | length'; \
	else \
		echo "⚠️ Set PROMETHEUS_URL to validate alert rules"; \
	fi

paranoid-test-alerts:
	@echo "🚨 Running alert fire tests..."
	python3 scripts/test_alerts.py \
		--pushgateway_url $(PROMETHEUS_PUSHGATEWAY_URL) \
		--slack_webhook $(SLACK_WEBHOOK_URL) \
		--test all \
		--wait_time 30

paranoid-test-alert-auc:
	@echo "🚨 Testing AUC drop alert..."
	python3 scripts/test_alerts.py \
		--test auc \
		--auc_value 0.75 \
		--wait_time 60

paranoid-test-alert-bias:
	@echo "⚖️ Testing bias violation alert..."
	python3 scripts/test_alerts.py \
		--test bias \
		--delta_auc 0.15 \
		--wait_time 60

paranoid-check-prometheus-rules:
	@echo "📋 Checking Prometheus rules syntax..."
	@if command -v promtool >/dev/null 2>&1; then \
		promtool check rules monitoring/prometheus-alert-rules.yaml; \
	else \
		echo "⚠️ promtool not found - install Prometheus toolkit"; \
	fi

# ===== GO-LIVE SEQUENCE =====

paranoid-go-live: paranoid-sanity setup-s3-lifecycle paranoid-ultimate paranoid-setup-alerts
	@echo "🎉 PARANOID V5 GO-LIVE SEQUENCE COMPLETE!"
	@echo "✅ Sanity checks passed"
	@echo "🗂️ S3 lifecycle configured"
	@echo "🚀 Enterprise pipeline deployed"
	@echo "🚨 Alert rules ready for import"
	@echo ""
	@echo "🔧 MANUAL STEPS REMAINING:"
	@echo "1. Import monitoring/prometheus-alert-rules.yaml to Prometheus"
	@echo "2. Import monitoring/grafana-paranoid-dashboard.json to Grafana" 
	@echo "3. Import monitoring/grafana-alerts-config.json to Grafana"
	@echo "4. Configure notification channels (Slack/PagerDuty)"
	@echo "5. Run: make paranoid-production-check"
	@echo ""
	@echo "🎯 PRODUCTION READY!"

# ===== LEGACY FERTILITY MODEL =====
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
		  S="$$SUMMARY"; L="$$LEDE"; \
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
