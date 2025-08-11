#!/usr/bin/env bash
set -euo pipefail

# --------- CONFIG ----------
PROJECT_ID="${PROJECT_ID:-braided-topic-452112-v3}"
REGION="${REGION:-europe-north1}"
DOMAIN="${DOMAIN:-paranoidmodels.com}"
SERVICE="${SERVICE:-paranoid-api}"

# (valinnainen) jos annat IMAGE:n, tehdään uusi revisioni; muuten vain päivitetään mapping
IMAGE="${IMAGE:-}"

BUILD_DIR="${BUILD_DIR:-web/dist}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-15}"
PROM_PUSH="${PROMETHEUS_PUSHGATEWAY_URL:-}"

# --------- LOG UTILS ----------
log()      { echo -e "\033[1;36m[INFO]\033[0m  $*"; }
ok()       { echo -e "\033[1;32m[SUCCESS]\033[0m $*"; }
fail()     { echo -e "\033[1;31m[ERROR]\033[0m  $*"; }

# --------- ROLLBACK STATE ----------
PREV_ROUTE_NAME=""
PREV_MAP_SERVICE=""
PREV_REVISION=""
NEW_REVISION=""

emit_prom() {
  [[ -z "$PROM_PUSH" ]] && return 0
  curl -s --data-binary @- "$PROM_PUSH/metrics/job/paranoid_deploy" <<EOF || true
paranoid_deploy_status 1
paranoid_deploy_ts $(date +%s)
EOF
}

emit_prom_fail() {
  [[ -z "$PROM_PUSH" ]] && return 0
  curl -s --data-binary @- "$PROM_PUSH/metrics/job/paranoid_deploy" <<EOF || true
paranoid_deploy_status 0
paranoid_deploy_ts $(date +%s)
EOF
}

rollback() {
  fail "Deployment failed — executing rollback…"

  # 1) Rollback Cloud Run revision if meillä on aiempi
  if [[ -n "$PREV_REVISION" ]]; then
    log "Reverting traffic to previous revision: $PREV_REVISION"
    gcloud run services update-traffic "$SERVICE" \
      --project "$PROJECT_ID" --region "$REGION" \
      --to-revisions "$PREV_REVISION=100" >/dev/null || true
  fi

  # 2) Palauta domain mapping vanhaan serviceen jos vaihtui
  if [[ -n "$PREV_MAP_SERVICE" ]]; then
    log "Restoring domain-mapping to previous service: $PREV_MAP_SERVICE"
    gcloud beta run domain-mappings delete \
      --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" --quiet || true
    gcloud beta run domain-mappings create \
      --service "$PREV_MAP_SERVICE" \
      --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" >/dev/null || true
  fi

  emit_prom_fail
  exit 1
}

trap 'rollback' ERR

# --------- SNAPSHOT BEFORE ---------
log "Snapshotting current state…"
if gcloud beta run domain-mappings describe --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" >/tmp/domain.yaml 2>/dev/null; then
  # routeName on käytännössä Cloud Run service (Knative route)
  PREV_MAP_SERVICE="$(gcloud beta run domain-mappings describe --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" --format='value(routeName)' || true)"
  log "Previous domain mapping → service: ${PREV_MAP_SERVICE:-unknown}"
fi

# ota talteen nykyinen 100% liikennettä saava revision
PREV_REVISION="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.traffic[0].revisionName)' || true)"
log "Previous active revision: ${PREV_REVISION:-none}"

# --------- BUILD & STATIC BACKUP ---------
log "Building frontend…"
npm --prefix web ci
npm --prefix web run build

log "Syncing static backup (Cloud Storage)…"
gsutil mb -l "$REGION" "gs://$DOMAIN" || true
gsutil web set -m index.html -e 404.html "gs://$DOMAIN"
gsutil -m rsync -r "$BUILD_DIR" "gs://$DOMAIN"
gsutil iam ch allUsers:objectViewer "gs://$DOMAIN" || true

# --------- (OPTIONAL) DEPLOY NEW REVISION ---------
if [[ -n "$IMAGE" ]]; then
  log "Deploying new Cloud Run revision from image: $IMAGE"
  gcloud run deploy "$SERVICE" \
    --image "$IMAGE" \
    --project "$PROJECT_ID" --region "$REGION" \
    --platform managed --allow-unauthenticated >/dev/null
  NEW_REVISION="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
    --format='value(status.latestReadyRevisionName)' || true)"
  log "New revision: ${NEW_REVISION:-unknown}"
else
  log "No IMAGE provided → skipping new revision deploy (mapping-only update)."
fi

# --------- UPDATE DOMAIN MAPPING ---------
log "Updating domain mapping → $SERVICE"
gcloud beta run domain-mappings delete \
  --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" --quiet || true
gcloud beta run domain-mappings create \
  --service "$SERVICE" \
  --domain "$DOMAIN" --region "$REGION" --project "$PROJECT_ID" >/dev/null

log "Waiting DNS/edge propagation…"
sleep 15

# --------- HEALTH CHECKS ---------
log "Health checks…"
# Get the Cloud Run service URL for health checks (more reliable than custom domain)
SERVICE_URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
SITE_CODE="$(curl -o /dev/null -s -w "%{http_code}" "$SERVICE_URL/" --connect-timeout 10 --max-time "$HEALTH_TIMEOUT")"
API_CODE="$(curl -o /dev/null -s -w "%{http_code}" "$SERVICE_URL/health" --connect-timeout 10 --max-time "$HEALTH_TIMEOUT")"

[[ "$SITE_CODE" == "200" ]] || { fail "Site check failed ($SITE_CODE) on $SERVICE_URL"; exit 1; }
[[ "$API_CODE"  == "200" ]] || { fail "API check failed ($API_CODE) on $SERVICE_URL"; exit 1; }

ok "Site & API healthy (200/200) ✅"
emit_prom

# --------- CLEAN EXIT ---------
trap - ERR
ok "Deployment complete!"