#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-braided-topic-452112-v3}"
REGION="${REGION:-europe-north1}"
DOMAIN="${DOMAIN:-paranoidmodels.com}"
SERVICE="${SERVICE:-paranoid-api}"
REVISION="${REVISION:-}"        # jos tiedossa
SERVICE_PREV="${SERVICE_PREV:-}" # jos haluat palauttaa domain mappingin vanhaan serviceen

if [[ -n "$REVISION" ]]; then
  echo "[INFO] Rollback traffic to revision: $REVISION"
  gcloud run services update-traffic "$SERVICE" \
    --project "$PROJECT_ID" --region "$REGION" \
    --to-revisions "$REVISION=100"
fi

if [[ -n "$SERVICE_PREV" ]]; then
  echo "[INFO] Restore domain mapping to service: $SERVICE_PREV"
  gcloud beta run domain-mappings delete \
    --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" --quiet || true
  gcloud beta run domain-mappings create \
    --service "$SERVICE_PREV" \
    --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID"
fi

echo "[SUCCESS] Rollback complete"
