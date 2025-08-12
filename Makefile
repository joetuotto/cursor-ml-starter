# Optional: Run Grafana locally with provisioning
.PHONY: grafana-up

grafana-up:
	@docker run --rm -d --name grafana \
		-p 3000:3000 \
		-e GF_SECURITY_ADMIN_USER=admin \
		-e GF_SECURITY_ADMIN_PASSWORD=admin \
		-e GF_PATHS_PROVISIONING=/etc/grafana/provisioning \
		-v $$(pwd)/monitoring/provisioning/datasources:/etc/grafana/provisioning/datasources \
		-v $$(pwd)/monitoring/provisioning/dashboards:/etc/grafana/provisioning/dashboards \
		-v $$(pwd)/monitoring/dashboards:/app/monitoring/dashboards \
		grafana/grafana:latest
	@echo "Grafana ↗ http://localhost:3000  (admin/admin)"

.PHONY: obs-up obs-down obs-reload
obs-up:
	@docker compose up -d

obs-down:
	@docker compose down

obs-reload:
	@docker compose restart grafana prometheus

.PHONY: alerts-smoke cap-gauge-push
alerts-smoke:
	@echo "🚨 Firing test alerts via Pushgateway..."
	@test -n "$(PROMETHEUS_PUSHGATEWAY_URL)" || (echo "Set PROMETHEUS_PUSHGATEWAY_URL" && exit 1)
	@echo 'paranoid_daily_soft_cap_hit{env="prod"} 1' | curl -sS --data-binary @- "$(PROMETHEUS_PUSHGATEWAY_URL)/metrics/job/paranoid_budget/env/prod" >/dev/null
	@echo 'paranoid_daily_hard_cap_hit{env="prod"} 1' | curl -sS --data-binary @- "$(PROMETHEUS_PUSHGATEWAY_URL)/metrics/job/paranoid_budget/env/prod" >/dev/null
	@echo 'paranoid_quality_gates_passed{env="prod"} 0' | curl -sS --data-binary @- "$(PROMETHEUS_PUSHGATEWAY_URL)/metrics/job/paranoid_quality/env/prod" >/dev/null
	@echo 'paranoid_post_deploy_sanity_ok{env="prod"} 0' | curl -sS --data-binary @- "$(PROMETHEUS_PUSHGATEWAY_URL)/metrics/job/paranoid_sanity/env/prod" >/dev/null
	@echo 'paranoid_drift_alerts_critical{env="prod"} 1' | curl -sS --data-binary @- "$(PROMETHEUS_PUSHGATEWAY_URL)/metrics/job/paranoid_drift/env/prod" >/dev/null
	@echo "✅ Pushed test series"

cap-gauge-push:
	@echo "📏 Pushing monthly cap gauge..."
	@test -n "$(PROMETHEUS_PUSHGATEWAY_URL)" || (echo "Set PROMETHEUS_PUSHGATEWAY_URL" && exit 1)
	@CAP=$${CAP:-30}; echo "paranoid_budget_month_cap_eur $$CAP" | curl -sS --data-binary @- "$(PROMETHEUS_PUSHGATEWAY_URL)/metrics/job/paranoid_budget/env/prod" >/dev/null && echo "cap=$$CAP€"

# ===== QUICK SECRETS SETUP (writes .env) =====
.PHONY: set-deepseek set-cursor show-env-keys

set-deepseek:
	@KEY=$${KEY:-}; \
	if [ -z "$$KEY" ]; then echo "Usage: KEY=sk-... make set-deepseek"; exit 1; fi; \
	touch .env; \
	if grep -q '^DEEPSEEK_API_KEY=' .env; then \
		sed -i.bak -e "s|^DEEPSEEK_API_KEY=.*|DEEPSEEK_API_KEY=$$KEY|" .env; \
	else \
		printf "DEEPSEEK_API_KEY=%s\n" "$$KEY" >> .env; \
	fi; \
	rm -f .env.bak; \
	echo "✅ Wrote DEEPSEEK_API_KEY to .env"

set-cursor:
	@KEY=$${KEY:-}; \
	if [ -z "$$KEY" ]; then echo "Usage: KEY=sk-... make set-cursor"; exit 1; fi; \
	touch .env; \
	if grep -q '^CURSOR_API_KEY=' .env; then \
		sed -i.bak -e "s|^CURSOR_API_KEY=.*|CURSOR_API_KEY=$$KEY|" .env; \
	else \
		printf "CURSOR_API_KEY=%s\n" "$$KEY" >> .env; \
	fi; \
	rm -f .env.bak; \
	echo "✅ Wrote CURSOR_API_KEY to .env"

show-env-keys:
	@for k in CURSOR_API_KEY DEEPSEEK_API_KEY PROMETHEUS_PUSHGATEWAY_URL SLACK_WEBHOOK_URL; do \
	  v=$${!k}; if [ -n "$$v" ]; then echo "$$k: set"; else echo "$$k: (.env will be used at runtime)"; fi; \
	done; \
	echo "Note: .env values are loaded by your process manager/container env. Export in shell or set in Cloud Run as needed."

# ===== CLOUD RUN JOB + SCHEDULER =====
.PHONY: enrich-job-deploy enrich-job-run enrich-cron-create enrich-cron-delete

enrich-job-deploy:
	@test -n "$(REGION)" || (echo "Set REGION" && exit 1)
	@test -n "$(IMAGE)" || (echo "Set IMAGE (e.g. gcr.io/$$PROJECT_ID/paranoid-api:TAG)" && exit 1)
	@echo "🚀 Deploying Cloud Run Job 'enrich-hybrid' in $(REGION) with image $(IMAGE)"
	@gcloud run jobs deploy enrich-hybrid \
		--region "$(REGION)" \
		--image "$(IMAGE)" \
		--max-retries 0 \
		--task-timeout 900s \
		--set-env-vars CURSOR_API_KEY="$(CURSOR_API_KEY)",DEEPSEEK_API_KEY="$(DEEPSEEK_API_KEY)",PROMETHEUS_PUSHGATEWAY_URL="$(PROMETHEUS_PUSHGATEWAY_URL)",ALERT_ENV="$(ALERT_ENV)",ALERT_CHANNEL="$(ALERT_CHANNEL)" \
		--command bash \
		--args -lc,"make enrich-hybrid && make budget-prom-daily" 
	@echo "✅ Cloud Run Job deployed"

enrich-job-run:
	@test -n "$(REGION)" || (echo "Set REGION" && exit 1)
	@echo "🏃 Executing Cloud Run Job 'enrich-hybrid' in $(REGION)"
	@gcloud run jobs execute enrich-hybrid --region "$(REGION)"

enrich-cron-create:
	@test -n "$(PROJECT_ID)" || (echo "Set PROJECT_ID" && exit 1)
	@test -n "$(REGION)" || (echo "Set REGION" && exit 1)
	@test -n "$(SCHEDULER_SA)" || (echo "Set SCHEDULER_SA (service account email with run.jobs.run perms)" && exit 1)
	@SCHED=$${SCHED:-enrich-hybrid-hourly}; CRON=$${CRON:-"0 * * * *"}; \
	echo "⏰ Creating Scheduler job $$SCHED @ $$CRON → Cloud Run Job execute"; \
	gcloud scheduler jobs create http "$$SCHED" \
		--location "$(REGION)" \
		--schedule "$$CRON" \
		--http-method POST \
		--uri "https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/enrich-hybrid:run" \
		--oauth-service-account-email "$(SCHEDULER_SA)"
	@echo "✅ Scheduler job created"

enrich-cron-delete:
	@test -n "$(REGION)" || (echo "Set REGION" && exit 1)
	@SCHED=$${SCHED:-enrich-hybrid-hourly}; \
	echo "🗑️ Deleting Scheduler job $$SCHED"; \
	gcloud scheduler jobs delete "$$SCHED" --location "$(REGION)" -q || true
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
	@echo "🧹 Normalizing enriched report for validation..."
	python3 scripts/normalize_enriched.py || true

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

# Original hybrid system (for reference)
hybrid-enrich-orig:
	@echo "🤖 Original hybrid enrichment: DeepSeek + GPT-5"
	python -m src.paranoid_model.hybrid_llm --signal artifacts/signal.fi.json --schema artifacts/newswire_schema.json --output artifacts/report.hybrid.json

hybrid-fi-orig:
	@echo "🇫🇮 Finnish content with original hybrid routing"
	make fi-ingest
	make hybrid-enrich-orig
	make fi-validate

# Drop-in Hybrid System
.PHONY: hybrid-setup hybrid-test hybrid-run hybrid-cost

hybrid-setup:
	@python3 -c "import os, pathlib; pathlib.Path('.cache/hybrid').mkdir(parents=True, exist_ok=True)"
	@[ -f .env ] || cp env.example .env || echo "📝 Copy env.example to .env and fill in API keys"
	@echo "✅ Hybrid setup ready"

hybrid-test:
	@python3 scripts/hybrid_test.py

hybrid-run:
	@echo "🚀 Running hybrid batch processing..."
	@python3 scripts/hybrid_test.py
	@echo "✅ Hybrid batch → artifacts/report.enriched.json"

hybrid-cost:
	@python3 scripts/hybrid_budget.py

# Self-Learning System
.PHONY: selflearn-setup selflearn-daily selflearn-report selflearn-test selflearn-backfill

selflearn-setup:
	@python3 -c "import os, pathlib; pathlib.Path('artifacts/feedback').mkdir(parents=True, exist_ok=True); pathlib.Path('artifacts/selflearn').mkdir(parents=True, exist_ok=True)"
	@pip install pyyaml numpy || echo "⚠️  Install dependencies: pip install pyyaml numpy"
	@echo "✅ Self-learning system ready"

selflearn-daily:
	@echo "🧠 Running daily self-learning cycle..."
	@python3 scripts/self_learn_daily.py --cfg config/selflearn.yaml

selflearn-report:
	@echo "📊 Generating self-learning report..."
	@python3 scripts/self_learn_report.py --out artifacts/selflearn/report.html
	@echo "🌐 Report: artifacts/selflearn/report.html"

selflearn-test:
	@echo "🧪 Testing self-learning system..."
	@python3 scripts/self_learn_test.py

selflearn-backfill:
	@echo "⏪ Backfilling historical data..."
	@python3 scripts/self_learn_daily.py --cfg config/selflearn.yaml --dry-run
	@echo "✅ Backfill completed"

# Live LLM Testing
.PHONY: hybrid-live-setup hybrid-live-test-gpt5 hybrid-live-test-deepseek

hybrid-live-setup:
	@python3 -c "import jsonschema" 2>/dev/null || pip install jsonschema
	@python3 -c "import tiktoken" 2>/dev/null || pip install tiktoken
	@python3 -c "import requests" 2>/dev/null || pip install requests
	@echo "✅ Live LLM dependencies ready"

hybrid-live-test-gpt5:
	@echo "🚀 Testing GPT-5 route..."
	@TEST_ROUTE=gpt5 MOCK_MODE=true python3 scripts/hybrid_live_test.py
	@echo "📄 Generated content:"
	@cat artifacts/report.enriched.json

hybrid-live-test-deepseek:
	@echo "🚀 Testing DeepSeek route..."
	@TEST_ROUTE=deepseek MOCK_MODE=true python3 scripts/hybrid_live_test.py
	@echo "📄 Generated content:"
	@cat artifacts/report.enriched.json

hybrid-live-test-real-gpt5:
	@echo "🚀 Testing GPT-5 route (REAL API)..."
	@TEST_ROUTE=gpt5 MOCK_MODE=false python3 scripts/hybrid_live_test.py
	@echo "📄 Generated content:"
	@cat artifacts/report.enriched.json

hybrid-live-test-real-deepseek:
	@echo "🚀 Testing DeepSeek route (REAL API)..."
	@TEST_ROUTE=deepseek MOCK_MODE=false python3 scripts/hybrid_live_test.py
	@echo "📄 Generated content:"
	@cat artifacts/report.enriched.json

# Cursor Pro Testing
.PHONY: hybrid-cursor-test

hybrid-cursor-test:
	@echo "🧪 Testing Cursor GPT-5 provider..."
	@python3 -c "import os, sys; sys.path.append('.'); from src.hybrid.providers.cursor_gpt5 import CursorGpt5Provider; p = CursorGpt5Provider(base_url=os.getenv('CURSOR_BASE_URL','https://api.cursor.sh/v1'), api_key=os.getenv('CURSOR_API_KEY','test-key'), model=os.getenv('CURSOR_GPT5_MODEL','gpt-5-thinking'), timeout_s=int(os.getenv('CURSOR_TIMEOUT_S','45'))); print('✅ Cursor provider created successfully')"

# Enhanced hybrid run with real routing
hybrid-run-enhanced:
	@echo "🚀 Running enhanced hybrid processing..."
	@python3 scripts/hybrid_run.py
	@echo "📄 Generated enhanced content:"
	@head -20 artifacts/report.enriched.json

.PHONY: enrich-hybrid
enrich-hybrid:
	@echo "👉 Running hybrid enrichment → artifacts/report.enriched.json"
	@python3 scripts/test_hybrid_enrich.py

# Budget Management
.PHONY: budget-status budget-reset budget-test budget-prom budget-prom-daily daily-guard-enable daily-guard-open-burst

budget-status:
	@python3 -c "import sys; sys.path.append('.'); from src.hybrid.budget import stats; print('💰 Budget Status:', stats())"

budget-reset:
	@rm -f artifacts/billing/costs.jsonl && echo "✅ Budget reset - costs cleared"

budget-test:
	@echo "🧪 Testing budget tracking..."
	@python3 -c "import sys; sys.path.append('.'); from src.hybrid.budget import record_usage, stats; print('Before:', stats()); [record_usage('gpt5_cursor', 1500, 800, eur=0.02, meta={'test':True}) for i in range(5)]; print('After 5 GPT-5 calls:', stats())"

budget-prom:
	@python3 -c "import sys; sys.path.append('.'); from src.hybrid.budget import push_prom; push_prom(); print('📊 Pushed metrics to Prometheus (if PROMETHEUS_PUSHGATEWAY_URL set)')"

budget-prom-daily:
	@python3 -c "import sys; sys.path.append('.'); from src.hybrid.budget import push_prom_daily; push_prom_daily(); print('📊 Pushed daily metrics (if PROMETHEUS_PUSHGATEWAY_URL set)')"

# Daily guard controls for Cloud Run Job
daily-guard-enable:
	@test -n "$(PROJECT_ID)" || (echo "Set PROJECT_ID" && exit 1)
	@test -n "$(REGION)" || (echo "Set REGION" && exit 1)
	@echo "🔒 Enabling daily hard guard on Cloud Run Job (removing budget overrides) in $(REGION)"
	@IMG=$$(gcloud run jobs describe enrich-hybrid --project "$(PROJECT_ID)" --region "$(REGION)" --format='value(spec.template.spec.template.spec.containers[0].image)'); \
	  echo "Using image: $$IMG"; \
	  gcloud run jobs deploy enrich-hybrid \
	    --project "$(PROJECT_ID)" --region "$(REGION)" \
	    --image "$$IMG" \
	    --max-retries 0 --task-timeout 900s \
	    --remove-env-vars BUDGET_MONTH_EUR,BUDGET_DAILY_RATIO,BUDGET_DAILY_HARD_RATIO,BUDGET_SOFT_RATIO,BUDGET_HARD_RATIO \
	    >/dev/null && echo "✅ Daily guard enabled (defaults restored)"

daily-guard-open-burst:
	@test -n "$(PROJECT_ID)" || (echo "Set PROJECT_ID" && exit 1)
	@test -n "$(REGION)" || (echo "Set REGION" && exit 1)
	@echo "🚧 Temporarily opening daily guard (high caps) in $(REGION)"
	@IMG=$$(gcloud run jobs describe enrich-hybrid --project "$(PROJECT_ID)" --region "$(REGION)" --format='value(spec.template.spec.template.spec.containers[0].image)'); \
	  echo "Using image: $$IMG"; \
	  gcloud run jobs deploy enrich-hybrid \
	    --project "$(PROJECT_ID)" --region "$(REGION)" \
	    --image "$$IMG" \
	    --max-retries 0 --task-timeout 900s \
	    --set-env-vars BUDGET_MONTH_EUR=1000,BUDGET_DAILY_RATIO=1.0,BUDGET_DAILY_HARD_RATIO=1.0,BUDGET_SOFT_RATIO=0.99,BUDGET_HARD_RATIO=0.999 \
	    >/dev/null && echo "✅ Daily guard temporarily opened (remember to 'make daily-guard-enable')"

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

.PHONY: prod-go-live
prod-go-live:
	@echo "\n🚀 PROD GO-LIVE: smoke → deploy → health → metrics → alert sanity"
	@echo "🔧 LLM smoke..."
	@$(MAKE) hybrid-cursor-test
	@$(MAKE) hybrid-run-enhanced
	@echo "📦 Deploying API image..."
	@IMAGE=$${IMAGE:-gcr.io/$${PROJECT_ID}/paranoid-api:$$(date +%Y%m%d%H%M)} $(MAKE) deploy-paranoid-with-image
	@echo "🏥 Production checks..."
	@$(MAKE) paranoid-production-check || true
	@echo "📊 Pushing metrics..."
	@$(MAKE) budget-prom
	@$(MAKE) budget-prom-daily
	@echo "🚨 Alert sanity (AUC drop)..."
	@$(MAKE) paranoid-test-alert-auc || true
	@echo "✅ prod-go-live complete"

.PHONY: post-deploy-sanity
post-deploy-sanity:
	@echo "🔎 Post-deploy sanity..."
	@python3 scripts/post_deploy_sanity.py || true

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


# ===== HERSH-STYLE FEEDS =====
.PHONY: feeds validate style-check fe-dev fe-build fe-deploy

# 1) Generoi ENG/FI feedit
feeds:
	python3 scripts/build_trends_feeds.py

# 2) Validoi dark tolerance / paranoid -säännöt
validate:
	python3 scripts/validate_trends.py

# 3) Pika-tyylitesti (ajaa enrichin → feedit → validoinnin)
style-check: enrich-hybrid feeds validate
	@echo "✅ Hersh-style + dark tolerance OK"

# 4) Frontend dev ja build
fe-dev:
	cd web && npm i && npm run dev

fe-symlink-feeds:
	mkdir -p web/public/newswire && cp artifacts/feeds/trends.*.json web/public/newswire/ 2>/dev/null || true

fe-build: fe-symlink-feeds
	cd web && npm i && npm run build

# 5) (valinnainen) Publikointi GCS:ään
fe-deploy: fe-build
	gsutil -m rsync -r web/dist gs://paranoidmodels.com

# ---------- Newswire: publish to GCS ----------
.PHONY: publish-feeds
publish-feeds:
	@BUCKET=$(GCS_BUCKET) bash scripts/publish_feeds.sh

.PHONY: prod-news-cycle
prod-news-cycle:
	@echo "[news] Enrich → Validate (dark-tolerance) → Build feeds → Publish"
	@make -s style-check
	@make -s feeds
	@make -s validate
	@make -s publish-feeds
	@echo "[news] DONE"

.PHONY: newswire-smoke
newswire-smoke:
	@curl -Is https://storage.googleapis.com/paranoidmodels.com/newswire/trends.en.json | head -n 1 || true
	@curl -Is https://storage.googleapis.com/paranoidmodels.com/newswire/trends.fi.json | head -n 1 || true

# ---------- Image Pipeline ----------
.PHONY: images-fetch images-build og-build images-publish news-with-images

images-fetch:
	python3 scripts/images_fetch.py

images-build:
	node scripts/images_build.js || node scripts/images_build_simple.js

og-build:
	node scripts/og_generate.js || node scripts/og_generate_simple.js

images-publish:
	bash scripts/publish_images.sh

news-with-images: style-check feeds remediate-feeds validate-news images-duotone publish-feeds images-publish
	@echo "✓ News (EN/FI), duotone images & feeds published."

.PHONY: images-duotone
images-duotone:
	@echo "🎨 Generating duotone images (WebP 480/768/1200)..."
	@node scripts/images/duotone.js || true

.PHONY: validate-news
validate-news:
	@node scripts/validate/news_feed_check.js artifacts/feeds/trends.en.json artifacts/feeds/trends.fi.json

.PHONY: remediate-feeds
remediate-feeds:
	@node scripts/remediate/feeds.js

news-with-images-duotone: style-check feeds images-duotone publish-feeds images-publish
	@echo "✓ News (EN/FI), duotone images & feeds published."

# ===== SMOKE / SAVUPIIPPU TESTIT =====
.PHONY: smoke-gcs smoke-domain job-exec e2e-smoke

# GCS-smoke: feedit + yksi kuva
smoke-gcs:
	@BUCKET=$${BUCKET:-paranoidmodels.com}; \
	echo "[GCS] Feeds:"; \
	curl -Is "https://storage.googleapis.com/$$BUCKET/feeds/trends.en.json" | head -n1; \
	curl -Is "https://storage.googleapis.com/$$BUCKET/feeds/trends.fi.json" | head -n1; \
	echo "[GCS] Sample image:"; \
	if command -v gsutil >/dev/null 2>&1; then \
	  OBJ=$$(gsutil ls gs://$$BUCKET/newswire/img/card | head -n1); \
	  if [ -n "$$OBJ" ]; then BASE=$$(basename $$OBJ); echo " -> $$BASE"; curl -Is "https://storage.googleapis.com/$$BUCKET/newswire/img/card/$$BASE" | head -n1; else echo "(no images found)"; fi; \
	else \
	  echo "(gsutil not found; skipping image HEAD)"; \
	fi

# Domain-smoke: root, health, feedit, kuva
smoke-domain:
	@DOMAIN=$${DOMAIN:-paranoidmodels.com}; \
	echo "[DOMAIN] Root & health:"; \
	curl -Is "https://$$DOMAIN/" | head -n1; \
	curl -Is "https://$$DOMAIN/health" | head -n1; \
	echo "[DOMAIN] Feeds:"; \
	curl -Is "https://$$DOMAIN/feeds/trends.en.json" | head -n1; \
	curl -Is "https://$$DOMAIN/feeds/trends.fi.json" | head -n1; \
	echo "[DOMAIN] Sample image:"; \
	if command -v gsutil >/dev/null 2>&1; then \
	  OBJ=$$(gsutil ls gs://$${BUCKET:-paranoidmodels.com}/newswire/img/card | head -n1); \
	  if [ -n "$$OBJ" ]; then BASE=$$(basename $$OBJ); echo " -> $$BASE"; curl -Is "https://$$DOMAIN/newswire/img/card/$$BASE" | head -n1; else echo "(no images found)"; fi; \
	else \
	  echo "(gsutil not found; provide a known image name via IMG_BASENAME=...)"; \
	fi

# Execute Cloud Run Job and show latest execution summary
job-exec:
	@PROJECT_ID=$${PROJECT_ID:?Set PROJECT_ID}; REGION=$${REGION:?Set REGION}; JOB=$${JOB_NAME:-enrich-hybrid}; \
	echo "[RUN] Executing job: $$JOB in $$REGION / $$PROJECT_ID"; \
	gcloud run jobs execute "$$JOB" --region "$$REGION" --project "$$PROJECT_ID"; \
	sleep 10; \
	EXEC=$$(gcloud run jobs executions list --project "$$PROJECT_ID" --region "$$REGION" --job "$$JOB" --format='value(name)' | head -n1); \
	echo "[RUN] Latest execution: $$EXEC"; \
	gcloud run jobs executions describe "$$EXEC" --project "$$PROJECT_ID" --region "$$REGION" | sed -n '1,120p'

# End-to-end quick smoke
e2e-smoke: style-check feeds validate-news images-duotone publish-feeds images-publish
	@echo "✓ E2E smoke complete"

.PHONY: deploy-all
deploy-all:
	@echo "[1/6] Remediate feeds"
	@make remediate-feeds
	@echo "[2/6] Validate content"
	@make validate-news
	@echo "[3/6] Publish feeds & images"
	@make publish-feeds
	@make images-publish
	@echo "[4/6] GCS smoke"
	@make smoke-gcs
	@echo "[5/6] TLS wait (noop if already ACTIVE)"
	@make lb-wait || true
	@echo "[6/6] Domain smoke (pre)"
	@make smoke-domain || true
	@if [ "$${LB_AUTOFIX:-0}" = "1" ]; then \
		echo "[LB] Auto-fix enabled (LB_AUTOFIX=1). Running lb-auto-fix…"; \
		make lb-auto-fix; \
		echo "[LB] Re-run domain smoke"; \
		make smoke-domain || true; \
	else \
		echo "[LB] Auto-fix skipped (set LB_AUTOFIX=1 to enable)"; \
	fi

.PHONY: deploy-all
deploy-all:
	@echo "[deploy] Remediate → Validate → Publish → Smoke (GCS) → TLS wait → Smoke (domain)"
	@$(MAKE) -s news-with-images
	@$(MAKE) -s smoke-gcs
	@$(MAKE) -s lb-wait
	@$(MAKE) -s smoke-domain

.PHONY: lb-verify lb-fix

.PHONY: lb-wait
lb-wait:
	@bash scripts/lb/wait_tls.sh

.PHONY: lb-auto-fix
lb-auto-fix:
	@bash scripts/lb/auto_fix.sh

# One-shot LB diagnosis
.PHONY: lb-diagnose
lb-diagnose:
	@PROJECT_ID=$(PROJECT_ID) DOMAIN=$(DOMAIN) REGION=$(REGION) \
	URLMAP=$(URLMAP) TARGET_PROXY=$(TARGET_PROXY) CR_BACKEND=$(CR_BACKEND) GCS_BACKEND=$(GCS_BACKEND) \
	bash scripts/lb/diagnose.sh

# Setup helper for Cloud Run auth + NEG + backend service
.PHONY: lb-prod-setup
lb-prod-setup:
	@echo "[Cloud Run auth]" && \
	gcloud run services add-iam-policy-binding $(SERVICE) --project $(PROJECT_ID) --region $(REGION) \
	  --member="allUsers" --role="roles/run.invoker" || true && \
	echo "[NEG + backend]" && \
	gcloud compute network-endpoint-groups create cr-neg --project $(PROJECT_ID) --region $(REGION) \
	  --network-endpoint-type=serverless --cloud-run-service=$(SERVICE) || true && \
	gcloud compute backend-services create cr-backend --project $(PROJECT_ID) --global \
	  --load-balancing-scheme=EXTERNAL_MANAGED --protocol=HTTP || true && \
	gcloud compute backend-services add-backend cr-backend --project $(PROJECT_ID) --global \
	  --network-endpoint-group=cr-neg --network-endpoint-group-region=$(REGION) || true

# Tulostaa URL mapin ja target proxy -sidonnat
lb-verify:
	@PROJECT_ID=$${PROJECT_ID:?Set PROJECT_ID}; \
	URLMAP=$${URLMAP:?Set URLMAP}; TARGET_PROXY=$${TARGET_PROXY:?Set TARGET_PROXY}; \
	echo "[VERIFY] URL Map:"; \
	gcloud compute url-maps describe "$$URLMAP" --project "$$PROJECT_ID" | sed -n '1,120p'; \
	echo "\n[VERIFY] Target HTTPS Proxy:"; \
	gcloud compute target-https-proxies describe "$$TARGET_PROXY" --project "$$PROJECT_ID" --format='value(urlMap, sslCertificates)'

# Lisää/korjaa URL Map -reititykset ja kohdistaa certin/proxyn, sitten domain-smoke
lb-fix:
	@set -e; \
	PROJECT_ID=$${PROJECT_ID:?Set PROJECT_ID}; REGION=$${REGION:?Set REGION}; DOMAIN=$${DOMAIN:?Set DOMAIN}; \
	BUCKET_BACKEND=$${BUCKET_BACKEND:?Set BUCKET_BACKEND}; CR_BACKEND=$${CR_BACKEND:?Set CR_BACKEND}; \
	URLMAP=$${URLMAP:?Set URLMAP}; TARGET_PROXY=$${TARGET_PROXY:?Set TARGET_PROXY}; CERT_NAME=$${CERT_NAME:?Set CERT_NAME}; \
	echo "[LB] Add/Update path-matcher (GCS routes, default -> Cloud Run)"; \
	gcloud compute url-maps add-path-matcher "$$URLMAP" --project "$$PROJECT_ID" \
	  --path-matcher-name gcs-routes \
	  --default-service "$$CR_BACKEND" \
	  --backend-bucket-path-rules="/feeds/*=$$BUCKET_BACKEND,/newswire/img/*=$$BUCKET_BACKEND,/report=$$BUCKET_BACKEND,/report.enriched.json=$$BUCKET_BACKEND" \
	|| true; \
	echo "[LB] Add host rule -> gcs-routes"; \
	gcloud compute url-maps add-host-rule "$$URLMAP" --project "$$PROJECT_ID" \
	  --hosts "$$DOMAIN" --path-matcher-name gcs-routes \
	|| true; \
	echo "[LB] Update target HTTPS proxy (cert + url-map)"; \
	gcloud compute target-https-proxies update "$$TARGET_PROXY" --project "$$PROJECT_ID" \
	  --ssl-certificates "$$CERT_NAME" --url-map "$$URLMAP" \
	|| true; \
	echo "[LB] Waiting for propagation..."; \
	sleep 10; \
	echo "[SMOKE] Domain"; \
	DOMAIN="$$DOMAIN" $(MAKE) smoke-domain || true; \
	echo "[DONE] lb-fix complete"
