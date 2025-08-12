#!/usr/bin/env bash
set -euo pipefail

# Minimal, idempotent bootstrap for GCP + GitHub secrets and workflow fix.
# Recommended to run in Google Cloud Shell.

NEW_PROJECT_ID="paranoidmodels-$(date +%s | tail -c 5)"
REPO="joetuotto/cursor-ml-starter"  # change if your repo slug differs
REGION="europe-north1"
# Use WORKFLOW_REF to select which ref to run the workflow on; defaults to main.
# This allows running the updated workflow from a feature branch before merging.
WORKFLOW_REF="${WORKFLOW_REF:-main}"
BUCKET="${NEW_PROJECT_ID}-cursor-bucket"
SA_NAME="github-actions-sa"
SA_EMAIL="${SA_NAME}@${NEW_PROJECT_ID}.iam.gserviceaccount.com"
KEY_PATH="${HOME}/.gcloud-keys/${NEW_PROJECT_ID}-sa-key.json"

echo "################################################################"
echo "Project:      ${NEW_PROJECT_ID}"
echo "Bucket:       ${BUCKET}"
echo "Repo:         ${REPO}"
echo "Region:       ${REGION}"
echo "Workflow ref: ${WORKFLOW_REF}"
echo "################################################################"

echo "[INFO] Ensuring gcloud is authenticated..."
gcloud auth list | grep -q "ACTIVE" || {
  echo "No active gcloud account found. Run: gcloud auth login";
  exit 1;
}

echo "[INFO] Creating project..."
gcloud projects create "${NEW_PROJECT_ID}" --name="Cursor AI Project" || true
gcloud config set project "${NEW_PROJECT_ID}"

echo "[INFO] Linking billing..."
BILLING_ACCOUNT=$(gcloud billing accounts list --format='value(ACCOUNT_ID)' --filter='OPEN=true' | head -n 1)
if [[ -z "${BILLING_ACCOUNT}" ]]; then
  echo "[ERROR] No open billing account found." && exit 1
fi
gcloud billing projects link "${NEW_PROJECT_ID}" --billing-account="${BILLING_ACCOUNT}" || true

echo "[INFO] Enabling APIs..."
gcloud services enable iam.googleapis.com storage-component.googleapis.com --project="${NEW_PROJECT_ID}" || true

echo "[INFO] Creating GCS bucket..."
gcloud storage buckets create "gs://${BUCKET}" --location="${REGION}" --project="${NEW_PROJECT_ID}" || true
echo "[INFO] Making bucket contents public..."
gsutil iam ch allUsers:objectViewer "gs://${BUCKET}"

echo "[INFO] Creating Service Account..."
gcloud iam service-accounts create "${SA_NAME}" --display-name="GitHub Actions Runner" --project="${NEW_PROJECT_ID}" || true

echo "[INFO] Granting bucket permissions to the Service Account..."
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --project="${NEW_PROJECT_ID}" || true

echo "[INFO] Creating JSON key..."
mkdir -p "$(dirname "${KEY_PATH}")"
if [[ ! -f "${KEY_PATH}" ]]; then
  gcloud iam service-accounts keys create "${KEY_PATH}" --iam-account="${SA_EMAIL}" --project="${NEW_PROJECT_ID}"
else
  echo "Key already exists at ${KEY_PATH}"
fi

echo "[INFO] Checking for GitHub CLI (gh)..."
if ! command -v gh >/dev/null 2>&1; then
  echo "[INFO] Installing GitHub CLI..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y && sudo apt-get install -y gh || {
      echo "[ERROR] Failed to install gh. Install manually and re-run secrets step."; exit 1; }
  else
    echo "[ERROR] gh not found and apt-get unavailable. Install gh manually and re-run secrets step."; exit 1
  fi
fi

echo "[INFO] Ensure you're authenticated to GitHub (gh auth login)."
gh auth status || gh auth login

echo "[INFO] Setting GitHub secrets for ${REPO}..."
gh secret set GCP_CREDENTIALS_JSON -R "${REPO}" < "${KEY_PATH}"
gh secret set GCP_PROJECT_ID -R "${REPO}" --body "${NEW_PROJECT_ID}"
gh secret set GCS_BUCKET -R "${REPO}" --body "${BUCKET}"

echo "[INFO] Triggering workflow once to verify setup..."
gh workflow run "newswire.yml" -R "${REPO}" --ref "${WORKFLOW_REF}" || true
sleep 10 || true
RUN_ID=$(gh run list -R "${REPO}" --branch "${WORKFLOW_REF}" -w "newswire.yml" -L 1 --json databaseId -q '.[0].databaseId' || echo "")
if [[ -n "${RUN_ID}" ]]; then
  gh run watch -R "${REPO}" "${RUN_ID}" --exit-status || {
    echo "[WARN] Workflow failed. Fetching logs...";
    gh run view -R "${REPO}" "${RUN_ID}" --log-failed || true;
  }
else
  echo "[WARN] Could not determine run id. Check workflow runs in GitHub UI."
fi

echo "[SUCCESS] Bootstrap completed. Project=${NEW_PROJECT_ID}, Bucket=${BUCKET}"


