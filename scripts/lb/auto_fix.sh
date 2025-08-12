#!/usr/bin/env bash
set -euo pipefail

# Required env
: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:?set REGION}"
: "${DOMAIN:?set DOMAIN}"

# Optional (with sane defaults)
URLMAP="${URLMAP:-paranoid-umap}"
TARGET_PROXY="${TARGET_PROXY:-paranoid-https-proxy}"
CERT_NAME="${CERT_NAME:-paranoid-cert}"
CR_BACKEND="${CR_BACKEND:-cr-backend}"
GCS_BACKEND="${GCS_BACKEND:-gcs-backend}"
SERVICE="${SERVICE:-paranoid-api}"

echo "[1/8] Cloud Run make public (unauthenticated)"
gcloud run services add-iam-policy-binding "$SERVICE" \
  --project "$PROJECT_ID" --region "$REGION" \
  --member="allUsers" --role="roles/run.invoker" >/dev/null 2>&1 || true

echo "[2/8] Ensure serverless NEG exists"
NEG_NAME="${SERVICE}-neg"
gcloud compute network-endpoint-groups describe "$NEG_NAME" --region="$REGION" >/dev/null 2>&1 || \
gcloud beta compute network-endpoint-groups create "$NEG_NAME" \
  --project "$PROJECT_ID" --region "$REGION" \
  --network-endpoint-type=serverless  \
  --cloud-run-service="$SERVICE"

echo "[3/8] Ensure Cloud Run backend service: $CR_BACKEND"
gcloud compute backend-services describe "$CR_BACKEND" --global >/dev/null 2>&1 || \
gcloud compute backend-services create "$CR_BACKEND" \
  --project "$PROJECT_ID" --global --protocol HTTP --load-balancing-scheme EXTERNAL_MANAGED

# Attach NEG to CR backend (idempotent)
gcloud compute backend-services add-backend "$CR_BACKEND" --global \
  --network-endpoint-group "$NEG_NAME" --network-endpoint-group-region "$REGION" >/dev/null 2>&1 || true

echo "[4/8] Ensure GCS backend bucket: $GCS_BACKEND → bucket=$DOMAIN (CDN on)"
if ! gcloud compute backend-buckets describe "$GCS_BACKEND" >/dev/null 2>&1; then
  gcloud compute backend-buckets create "$GCS_BACKEND" \
    --project "$PROJECT_ID" --gcs-bucket-name "$DOMAIN" --enable-cdn
else
  gcloud compute backend-buckets update "$GCS_BACKEND" \
    --project "$PROJECT_ID" --gcs-bucket-name "$DOMAIN" --enable-cdn >/dev/null 2>&1 || true
fi

echo "[5/8] Ensure URL map exists: $URLMAP"
gcloud compute url-maps describe "$URLMAP" --global >/dev/null 2>&1 || \
gcloud compute url-maps create "$URLMAP" --project "$PROJECT_ID" --global --default-service "$CR_BACKEND"

# Export, patch, import (idempotent path rules)
TMP=$(mktemp)
gcloud compute url-maps export "$URLMAP" --global --destination="$TMP" >/dev/null || true
# Determine URIs
if grep -q '^defaultService:' "$TMP"; then
  CR_URI=$(grep -m1 '^defaultService:' "$TMP" | awk '{print $2}')
else
  CR_URI="https://www.googleapis.com/compute/v1/projects/$PROJECT_ID/global/backendServices/$CR_BACKEND"
fi
GCS_URI=$(grep -m1 "backendBuckets/$GCS_BACKEND" "$TMP" | awk '{print $2}' || true)
if [[ -z "${GCS_URI:-}" ]]; then
  GCS_URI="https://www.googleapis.com/compute/v1/projects/$PROJECT_ID/global/backendBuckets/$GCS_BACKEND"
fi

cat > "${TMP}.new" <<EOF
name: $URLMAP
defaultService: $CR_URI
hostRules:
- hosts:
  - $DOMAIN
  pathMatcher: gcs-routes
pathMatchers:
- name: gcs-routes
  defaultService: $CR_URI
  pathRules:
  - paths:
    - /report
    - /report.enriched.json
    - /feeds/*
    - /newswire/img/*
    service: $GCS_URI
EOF

echo "[6/8] Import URL map with GCS routes"
gcloud compute url-maps import "$URLMAP" --global --source="${TMP}.new" --quiet

echo "[7/8] Ensure Target HTTPS Proxy uses cert + url-map: $TARGET_PROXY"
gcloud compute target-https-proxies describe "$TARGET_PROXY" >/dev/null 2>&1 || \
gcloud compute target-https-proxies create "$TARGET_PROXY" \
  --project "$PROJECT_ID" --ssl-certificates "$CERT_NAME" --url-map "$URLMAP"

# Update cert/url-map just in case
gcloud compute target-https-proxies update "$TARGET_PROXY" \
  --project "$PROJECT_ID" --ssl-certificates "$CERT_NAME" --url-map "$URLMAP" >/dev/null 2>&1 || true

echo "[8/8] Quick smoke via LB IP + Host header"
LBIP=$(gcloud compute forwarding-rules list --global --format='value(IP_ADDRESS)' | head -1)
echo "LB IP: $LBIP"
set +e
curl -sSI --max-time 10 --resolve "$DOMAIN:443:$LBIP" "https://$DOMAIN/health" | head -n1
curl -sSI --max-time 10 --resolve "$DOMAIN:443:$LBIP" "https://$DOMAIN/feeds/trends.en.json" | head -n1
curl -sSI --max-time 10 --resolve "$DOMAIN:443:$LBIP" "https://$DOMAIN/newswire/img/card/sample-480.webp" | head -n1
set -e

echo "Auto-fix completed. If HTTPS still fails, check DNS A → $LBIP and cert status:"
echo "  gcloud compute ssl-certificates describe $CERT_NAME --global --format='value(managed.status,managed.domainStatus)'"


