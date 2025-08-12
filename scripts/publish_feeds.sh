#!/usr/bin/env bash
set -euo pipefail

BUCKET="${BUCKET:-${GCS_BUCKET:-paranoidmodels.com}}"
SRC_EN="${SRC_EN:-artifacts/feeds/trends.en.json}"
SRC_FI="${SRC_FI:-artifacts/feeds/trends.fi.json}"
DST_EN="gs://$BUCKET/newswire/trends.en.json"
DST_FI="gs://$BUCKET/newswire/trends.fi.json"

if ! command -v gsutil >/dev/null 2>&1; then
  echo "[ERROR] gsutil not found. Install gcloud SDK or run in CI with gcloud." >&2
  exit 1
fi

echo "[publish] Ensuring bucket public read + short TTL for feeds…"
gsutil iam ch allUsers:objectViewer "gs://$BUCKET" >/dev/null 2>&1 || true

echo "[publish] Upload EN → $DST_EN"
gsutil -h "Content-Type: application/json" \
       -h "Cache-Control: public, max-age=300" \
       cp "$SRC_EN" "$DST_EN"

echo "[publish] Upload FI → $DST_FI"
gsutil -h "Content-Type: application/json" \
       -h "Cache-Control: public, max-age=300" \
       cp "$SRC_FI" "$DST_FI"

# ALSO publish under /feeds/ for LB routing
FEEDS_EN="gs://$BUCKET/feeds/trends.en.json"
FEEDS_FI="gs://$BUCKET/feeds/trends.fi.json"

echo "[publish] Upload EN → $FEEDS_EN"
gsutil -h "Content-Type: application/json" \
       -h "Cache-Control: public, max-age=300" \
       cp "$SRC_EN" "$FEEDS_EN"

echo "[publish] Upload FI → $FEEDS_FI"
gsutil -h "Content-Type: application/json" \
       -h "Cache-Control: public, max-age=300" \
       cp "$SRC_FI" "$FEEDS_FI"

# Ensure cache headers on the feeds path
 gsutil -m setmeta -h "Cache-Control:public,max-age=300" gs://$BUCKET/feeds/** 2>/dev/null || true

echo "[publish] Smoke:"
curl -Is "https://storage.googleapis.com/${BUCKET}/newswire/trends.en.json" | head -n 1 || true
curl -Is "https://storage.googleapis.com/${BUCKET}/newswire/trends.fi.json" | head -n 1 || true
curl -Is "https://storage.googleapis.com/${BUCKET}/feeds/trends.en.json" | head -n 1 || true
curl -Is "https://storage.googleapis.com/${BUCKET}/feeds/trends.fi.json" | head -n 1 || true
echo "[publish] OK"
