#!/usr/bin/env sh
set -eu

ORIGIN="${ORIGIN:-https://api.paranoidmodels.com}"

echo "== /health =="
curl -fsSL -D - "$ORIGIN/health" -o /tmp/health.json | sed -n '1,20p' || true
if ! jq -e '.status=="healthy"' /tmp/health.json >/dev/null 2>&1; then
  echo "Health not healthy"; exit 1;
fi

echo "== /newswire (no slash) HEAD: expect HTTPS, no downgrade =="
hdr="$(curl -sI "$ORIGIN/newswire")"
echo "$hdr" | sed -n '1,20p'
# If 307, ensure it keeps https in Location
if echo "$hdr" | grep -qi '^HTTP/.* 307'; then
  if ! echo "$hdr" | grep -qi 'location: https://'; then
    echo "Redirect not https → https (still http). Failing."; exit 1;
  fi
fi

echo "== CSP header allows Google Fonts =="
csp="$(curl -sI "$ORIGIN/newswire" | grep -i '^content-security-policy' || true)"
echo "$csp"
echo "$csp" | grep -q 'fonts.googleapis.com' || { echo "CSP missing fonts.googleapis.com"; exit 1; }
echo "$csp" | grep -q 'fonts.gstatic.com'    || { echo "CSP missing fonts.gstatic.com"; exit 1; }

echo "== API endpoints =="
curl -fsSL "$ORIGIN/api/paranoid/feed"   >/dev/null
curl -fsSL "$ORIGIN/api/paranoid/trends" >/dev/null
echo "Smoke OK"
