#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${DOMAIN:?set DOMAIN}"
URLMAP="${URLMAP:-paranoid-umap}"
TARGET_PROXY="${TARGET_PROXY:-paranoid-https-proxy}"
CR_BACKEND="${CR_BACKEND:-cr-backend}"
GCS_BACKEND="${GCS_BACKEND:-gcs-backend}"
REGION="${REGION:-europe-north1}"

echo "== DNS =="
echo "A $(dig +short A $DOMAIN | tr '\n' ' ')"
echo "AAAA $(dig +short AAAA $DOMAIN | tr '\n' ' ')"
LBIP=$(gcloud compute forwarding-rules list --global --filter="name~https" --format='value(IP_ADDRESS)' | head -1 || true)
echo "LB IP: ${LBIP:-<none>}"

echo
echo "== Managed certs (global) =="
gcloud compute ssl-certificates list --global --project "$PROJECT_ID" \
  --format='table(NAME, TYPE, MANAGED_STATUS, CREATION_TIMESTAMP)'
echo
for c in $(gcloud compute ssl-certificates list --global --project "$PROJECT_ID" --format='value(NAME)'); do
  echo "--- $c"
  gcloud compute ssl-certificates describe "$c" --global --project "$PROJECT_ID" \
   --format='value(name,managed.status,managed.domainStatus)'
done

echo
echo "== Forwarding rules (global) =="
gcloud compute forwarding-rules list --global --project "$PROJECT_ID" \
  --format='table(NAME,IP_ADDRESS,PORT_RANGE,TARGET)'

echo
echo "== Target HTTPS proxy =="
gcloud compute target-https-proxies describe "$TARGET_PROXY" --project "$PROJECT_ID" \
  --format='yaml' | sed -n '1,120p'

echo
echo "== URL map (export) =="
gcloud compute url-maps export "$URLMAP" --global --project "$PROJECT_ID" --destination=- | sed -n '1,220p'

echo
echo "== Backend buckets =="
gcloud compute backend-buckets list --project "$PROJECT_ID" \
  --format='table(NAME,BUCKET_NAME,ENABLE_CDN)'

echo
echo "== Backend services (global) =="
gcloud compute backend-services list --global --project "$PROJECT_ID" \
  --format='table(NAME,PROTOCOL,LOAD_BALANCING_SCHEME)'

echo
echo "== Serverless NEG (Cloud Run) =="
gcloud compute network-endpoint-groups list --project "$PROJECT_ID" \
  --filter="networkEndpointType=SERVERLESS" \
  --format='table(NAME,REGION,DEFAULT_PORT)'

echo
echo "== Cloud Run service (ingress & auth) =="
SERVICE="${SERVICE:-paranoid-api}"
gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --format='value(metadata.name,spec.template.metadata.annotations."run.googleapis.com/ingress",status.url)'
echo "IAM (expect allUsers: roles/run.invoker):"
gcloud run services get-iam-policy "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --format='table(bindings.role, bindings.members)'

echo
echo "== Live path probe via LB IP (Host header) =="
if [[ -n "${LBIP:-}" ]]; then
  for p in / /health /feeds/trends.en.json /feeds/trends.fi.json /report /report.enriched.json; do
    printf "%-28s " "$p"
    (curl -sSI --max-time 8 --resolve "$DOMAIN:443:$LBIP" "https://$DOMAIN$p" | head -n1) || echo "ERR"
  done
else
  echo "No LB IP resolved."
fi

echo
echo "== Summary hints =="
echo "- If cert managed.status!=ACTIVE or domainStatus=FAILED_NOT_VISIBLE → DNS A must point to LB IP; remove AAAA unless IPv6 is enabled."
echo "- If URL map defaultService != $CR_BACKEND → set-default-service to Cloud Run backend."
echo "- If /feeds/* or /newswire/img/* not routed to $GCS_BACKEND → add pathRules to URL map."
echo "- If Cloud Run IAM lacks allUsers:roles/run.invoker → add-iam-policy-binding."
echo "- If serverless NEG missing → create cr-neg and add to $CR_BACKEND."



