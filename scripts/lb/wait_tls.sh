#!/usr/bin/env bash
set -euo pipefail
CERT_NAME="${CERT_NAME:-paranoid-cert}"
DOMAIN="${DOMAIN:-paranoidmodels.com}"
LBIP="${LBIP:-34.149.20.14}"
TIMEOUT="${TIMEOUT:-900}"   # 15 min
SLEEP="${SLEEP:-10}"

echo "[lb-wait] Waiting for managed cert '$CERT_NAME' to become ACTIVE for $DOMAIN (timeout ${TIMEOUT}s)"
start=$(date +%s)
while true; do
  status=$(gcloud compute ssl-certificates describe "$CERT_NAME" --global --format='value(managed.status)' 2>/dev/null || echo "")
  dom=$(gcloud compute ssl-certificates describe "$CERT_NAME" --global --format='value(managed.domainStatus)' 2>/dev/null || echo "")
  now=$(date +%s); elapsed=$((now - start))
  echo "  status=$status  domainStatus=$dom  elapsed=${elapsed}s"
  if [[ "$status" == "ACTIVE" ]]; then
    echo "[lb-wait] ACTIVE 🎉  running quick smoke via --resolve"
    curl -sSI --resolve "${DOMAIN}:443:${LBIP}" "https://${DOMAIN}/health" | head -n1 || true
    exit 0
  fi
  if (( elapsed > TIMEOUT )); then
    echo "[lb-wait] TIMEOUT: cert is not ACTIVE yet."
    exit 1
  fi
  sleep "$SLEEP"
done



