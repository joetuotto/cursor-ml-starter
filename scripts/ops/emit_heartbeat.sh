#!/usr/bin/env bash
set -euo pipefail

STATUS="${1:-}"
JOB="${2:-}"
ENV_NAME="${3:-}"
BRANCH="${4:-}"
SHA="${5:-}"
RUN_ID="${6:-}"
PROM_HEARTBEAT_URL="${PROM_HEARTBEAT_URL:-}"

if [[ -z "$STATUS" || -z "$JOB" || -z "$ENV_NAME" || -z "$BRANCH" || -z "$SHA" || -z "$RUN_ID" ]]; then
  echo "Usage: $0 <status> <job> <env> <branch> <sha> <run_id>"
  exit 1
fi

TS="$(date -u +%FT%TZ)"
PAYLOAD=$(jq -nc \
  --arg status "$STATUS" \
  --arg job "$JOB" \
  --arg env "$ENV_NAME" \
  --arg branch "$BRANCH" \
  --arg sha "$SHA" \
  --arg run_id "$RUN_ID" \
  --arg ts "$TS" \
  '{status:$status,job:$job,env:$env,branch:$branch,sha:$sha,run_id:$run_id,ts:$ts}' 2>/dev/null || \
  printf '{"status":"%s","job":"%s","env":"%s","branch":"%s","sha":"%s","run_id":"%s","ts":"%s"}' \
    "$STATUS" "$JOB" "$ENV_NAME" "$BRANCH" "$SHA" "$RUN_ID" "$TS" )

if [[ -z "$PROM_HEARTBEAT_URL" ]]; then
  echo "[heartbeat] PROM_HEARTBEAT_URL missing → skip"
  echo "[heartbeat] payload: $PAYLOAD"
  exit 0
fi

echo "[heartbeat] POST $PROM_HEARTBEAT_URL"
echo "[heartbeat] payload: $PAYLOAD"

# Fire and don’t fail pipeline on heartbeat problems
curl -sS -X POST "$PROM_HEARTBEAT_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --max-time 10 \
  -w "\n[heartbeat] http_status=%{http_code}\n" \
  || echo "[heartbeat] curl error (ignored)"


