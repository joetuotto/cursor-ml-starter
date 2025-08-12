#!/usr/bin/env bash
set -euo pipefail

BUCKET="${BUCKET:-paranoidmodels.com}"
IMG_DIR="artifacts/images/out"
DUOTONE_DIR="artifacts/newswire/img/card"
OG_DIR="artifacts/images/og"

echo "[img-publish] Publishing images to GCS..."

if ! command -v gsutil >/dev/null 2>&1; then
  echo "[ERROR] gsutil not found. Install gcloud SDK." >&2
  exit 1
fi

HAS_CLASSIC=0
HAS_DUOTONE=0
[[ -d "$IMG_DIR" ]] && HAS_CLASSIC=1 || echo "[WARN] Classic image dir not found: $IMG_DIR"
[[ -d "$DUOTONE_DIR" ]] && HAS_DUOTONE=1 || echo "[WARN] Duotone image dir not found: $DUOTONE_DIR (run 'make images-duotone')"

if [[ $HAS_CLASSIC -eq 0 && $HAS_DUOTONE -eq 0 ]]; then
  echo "[ERROR] No image outputs to publish. Run 'make images-duotone' or 'make images-build' first." >&2
  exit 1
fi

if [[ ! -d "$OG_DIR" ]]; then
  echo "[WARN] OG directory not found: $OG_DIR" >&2
  echo "Run 'make og-build' to generate OG images." >&2
fi

# Sync image sizes
if [[ $HAS_CLASSIC -eq 1 ]]; then
  for size in hero card thumb; do
    local_dir="$IMG_DIR/$size"
    remote_path="gs://$BUCKET/newswire/img/$size"
    
    if [[ -d "$local_dir" ]]; then
      echo "[img-publish] Uploading $size images (classic)..."
      gsutil -m rsync -r "$local_dir" "$remote_path"
      
      # Long cache for immutable assets (1 year)
      gsutil -m setmeta -h "Cache-Control:public,max-age=31536000,immutable" "$remote_path/**" 2>/dev/null || true
      gsutil -m setmeta -h "Content-Type:image/jpeg" "$remote_path/**" 2>/dev/null || true
    else
      echo "[WARN] Size directory not found: $local_dir"
    fi
  done
fi

# Publish duotone WebP variants (480/768/1200)
if [[ $HAS_DUOTONE -eq 1 ]]; then
  remote_duo="gs://$BUCKET/newswire/img/card"
  echo "[img-publish] Uploading duotone WebP images..."
  gsutil -m rsync -r "$DUOTONE_DIR" "$remote_duo"
  gsutil -m setmeta -h "Cache-Control:public,max-age=31536000,immutable" "$remote_duo/**" 2>/dev/null || true
  # Attempt to set correct content-type for .webp
  gsutil -m setmeta -h "Content-Type:image/webp" "$remote_duo/**.webp" 2>/dev/null || true
fi

# Sync OG images  
if [[ -d "$OG_DIR" ]]; then
  echo "[img-publish] Uploading OG images..."
  gsutil -m rsync -r "$OG_DIR" "gs://$BUCKET/newswire/og"
  
  # Short cache headers (5 minutes for faster updates)
  gsutil -m setmeta -h "Cache-Control:public,max-age=300" "gs://$BUCKET/newswire/og/**" 2>/dev/null || true
  gsutil -m setmeta -h "Content-Type:image/png" "gs://$BUCKET/newswire/og/**" 2>/dev/null || true
else
  echo "[WARN] OG directory not found: $OG_DIR"
fi

# Make bucket publicly readable
echo "[img-publish] Ensuring public read access..."
gsutil iam ch allUsers:objectViewer "gs://$BUCKET" >/dev/null 2>&1 || true

echo "[img-publish] Smoke test..."

if [[ $HAS_CLASSIC -eq 1 ]]; then
  # Test classic URLs
  for size in hero card thumb; do
    url="https://storage.googleapis.com/$BUCKET/newswire/img/$size/"
    echo -n "  $size: "
    curl -Is "$url" 2>/dev/null | head -n 1 || echo "N/A"
  done
fi

if [[ $HAS_DUOTONE -eq 1 ]]; then
  duo_url="https://storage.googleapis.com/$BUCKET/newswire/img/card/"
  echo -n "  duotone-card: "
  curl -Is "$duo_url" 2>/dev/null | head -n 1 || echo "N/A"
fi

og_url="https://storage.googleapis.com/$BUCKET/newswire/og/"
echo -n "  og: "
curl -Is "$og_url" 2>/dev/null | head -n 1 || echo "N/A"

echo "[img-publish] ✅ Image publishing complete!"
echo ""
echo "📸 Image URLs:"
echo "   Duotone card (srcset base): https://storage.googleapis.com/$BUCKET/newswire/img/card/SLUG-{480,768,1200}.webp"
echo "   (classic) Hero:  https://storage.googleapis.com/$BUCKET/newswire/img/hero/IMAGE_ID.jpg"
echo "   (classic) Card:  https://storage.googleapis.com/$BUCKET/newswire/img/card/IMAGE_ID.jpg"  
echo "   (classic) Thumb: https://storage.googleapis.com/$BUCKET/newswire/img/thumb/IMAGE_ID.jpg"
echo "   OG:              https://storage.googleapis.com/$BUCKET/newswire/og/IMAGE_ID.png"
