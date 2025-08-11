#!/usr/bin/env bash
set -euo pipefail

# Config (override via env)
: "${PROJECT_ID:=braided-topic-452112-v3}"
: "${REGION:=europe-north1}"

echo "This will securely capture your Cursor API key, update .env, and add a Secret Manager version."
read -s -p "Cursor API key (hidden): " CURSOR_KEY; echo
if [[ -z "${CURSOR_KEY}" ]]; then
  echo "No key entered, aborting." >&2
  exit 1
fi

# 1) Write/update .env (local dev)
touch .env
if grep -q '^CURSOR_API_KEY=' .env; then
  sed -i.bak -e "s|^CURSOR_API_KEY=.*$|CURSOR_API_KEY=${CURSOR_KEY}|" .env && rm -f .env.bak
else
  printf "\nCURSOR_API_KEY=%s\n" "${CURSOR_KEY}" >> .env
fi
if grep -q '^CURSOR_BASE=' .env; then
  sed -i.bak -e "s|^CURSOR_BASE=.*$|CURSOR_BASE=https://api.cursor.sh/v1|" .env && rm -f .env.bak
else
  printf "CURSOR_BASE=https://api.cursor.sh/v1\n" >> .env
fi
echo "✅ Updated .env (CURSOR_API_KEY, CURSOR_BASE)"

# 2) Secret Manager version (prod)
echo "➕ Adding secret version to Secret Manager: cursor-gpt5-api-key (project: ${PROJECT_ID})"
printf "%s" "${CURSOR_KEY}" | gcloud secrets versions add cursor-gpt5-api-key \
  --project "${PROJECT_ID}" --data-file=- >/dev/null 2>&1 || {
  echo "ℹ️  Creating secret cursor-gpt5-api-key (did not exist)"
  gcloud secrets create cursor-gpt5-api-key --project "${PROJECT_ID}" --replication-policy automatic >/dev/null
  printf "%s" "${CURSOR_KEY}" | gcloud secrets versions add cursor-gpt5-api-key \
    --project "${PROJECT_ID}" --data-file=- >/dev/null
}
echo "✅ Secret version added"

# 3) Grant job Service Account access (best‑effort)
SA_EMAIL=$(gcloud run jobs describe enrich-hybrid \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --format='value(spec.template.template.spec.serviceAccountName)' 2>/dev/null || true)
if [[ -n "${SA_EMAIL}" ]]; then
  gcloud secrets add-iam-policy-binding cursor-gpt5-api-key \
    --project "${PROJECT_ID}" \
    --member "serviceAccount:${SA_EMAIL}" \
    --role roles/secretmanager.secretAccessor >/dev/null || true
  echo "✅ Granted secret access to job SA: ${SA_EMAIL}"
else
  echo "ℹ️  Could not detect job SA; skip binding (you can grant later if needed)"
fi

echo "\nNext steps:"
echo "- Local dev: export LLM_PROVIDER_MODE=hybrid (or keep deepseek_only)"
echo "- Cloud Run Job: flip to hybrid when ready, e.g.:"
cat <<EONXT
gcloud run jobs deploy enrich-hybrid \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --image "gcr.io/${PROJECT_ID}/paranoid-enricher:202508111508" \
  --max-retries 0 --task-timeout 900s \
  --set-secrets "DEEPSEEK_API_KEY=deepseek-api-key:latest,CURSOR_API_KEY=cursor-gpt5-api-key:latest" \
  --set-env-vars "LLM_PROVIDER_MODE=hybrid" \
  --command bash \
  --args -lc,"python3 scripts/test_hybrid_enrich.py && gsutil -m rsync -r artifacts gs://paranoidmodels.com"
EONXT
echo "\nDone."


