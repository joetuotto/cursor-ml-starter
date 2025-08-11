#!/usr/bin/env bash
# Savupiippu-testi: e2e + domain + GCS HEAD -tarkistukset
# Usage:
#   BUCKET=paranoidmodels.com DOMAIN=paranoidmodels.com ./scripts/smoke.sh
#   RUN_JOB=true PROJECT_ID=... REGION=... ./scripts/smoke.sh
# Env:
#   PROJECT_ID / REGION optional; set RUN_JOB=true to execute job and assert Succeeded

set -uo pipefail

BUCKET=${BUCKET:-paranoidmodels.com}
DOMAIN=${DOMAIN:-}
RUN_JOB=${RUN_JOB:-false}
JOB_NAME=${JOB_NAME:-enrich-hybrid}
PROJECT_ID=${PROJECT_ID:-}
REGION=${REGION:-}

failures=()

log() { printf "\n== %s ==\n" "$*"; }
ok()  { echo "[OK]  $*"; }
err() { echo "[ERR] $*"; failures+=("$*"); }

check_url() {
  local url="$1"; local label="$2"
  if curl -fsS -o /dev/null -I "$url"; then ok "$label: 200"; else err "$label: FAIL ($url)"; fi
}

main() {
  log "Content validation"
  make style-check || failures+=("style-check failed")
  make feeds       || failures+=("feeds failed")
  make validate-news || failures+=("validate-news failed")

  log "Images & publish"
  make images-duotone || echo "(images) duotone skipped"
  make publish-feeds  || failures+=("publish-feeds failed")
  make images-publish || failures+=("images-publish failed")

  log "GCS HEAD checks"
  check_url "https://storage.googleapis.com/${BUCKET}/feeds/trends.en.json" "GCS feed EN"
  check_url "https://storage.googleapis.com/${BUCKET}/feeds/trends.fi.json" "GCS feed FI"

  # Sample image check
  if command -v gsutil >/dev/null 2>&1; then
    SAMPLE=$(gsutil ls gs://${BUCKET}/newswire/img/card | head -n1 || true)
    if [ -n "$SAMPLE" ]; then
      BASE=$(basename "$SAMPLE")
      check_url "https://storage.googleapis.com/${BUCKET}/newswire/img/card/${BASE}" "GCS image ${BASE}"
    else
      echo "(no images found under gs://${BUCKET}/newswire/img/card)"
    fi
  else
    echo "(gsutil not found; skipping dynamic image pick)"
  fi

  if [ -n "$DOMAIN" ]; then
    log "Domain HEAD checks (${DOMAIN})"
    check_url "https://${DOMAIN}/" "domain root"
    check_url "https://${DOMAIN}/health" "domain health"
    check_url "https://${DOMAIN}/feeds/trends.en.json" "domain feed EN"
    check_url "https://${DOMAIN}/feeds/trends.fi.json" "domain feed FI"
    # Try reuse sample
    if [ -n "$BASE" ]; then
      check_url "https://${DOMAIN}/newswire/img/card/${BASE}" "domain image ${BASE}"
    fi
  fi

  if [ "$RUN_JOB" = true ] && command -v gcloud >/dev/null 2>&1 && [ -n "$PROJECT_ID" ] && [ -n "$REGION" ]; then
    log "Cloud Run Job execution"
    if gcloud run jobs execute "$JOB_NAME" --region "$REGION" --project "$PROJECT_ID"; then
      ok "job executed"
      # wait and verify status
      sleep 20
      EXEC=$(gcloud run jobs executions list --project "$PROJECT_ID" --region "$REGION" --job "$JOB_NAME" --format='value(name)' | head -n1)
      if [ -n "$EXEC" ]; then
        DESC=$(gcloud run jobs executions describe "$EXEC" --project "$PROJECT_ID" --region "$REGION")
        echo "$DESC" | sed -n '1,80p'
        if echo "$DESC" | grep -qi 'Succeeded'; then
          ok "job status: Succeeded ($EXEC)"
        else
          err "job status not Succeeded ($EXEC)"
        fi
      else
        err "no execution found after job trigger"
      fi
    else
      err "job execute failed"
    fi
  fi

  log "Summary"
  if [ ${#failures[@]} -eq 0 ]; then
    echo "PASS: all checks green"
    exit 0
  else
    printf "FAIL (%d):\n" "${#failures[@]}"
    for f in "${failures[@]}"; do echo " - $f"; done
    exit 1
  fi
}

main "$@"
