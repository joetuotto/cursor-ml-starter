# Cloud Run Job Update for Hersh-style Newswire

## Update the existing Cloud Run Job to use the new pipeline

```bash
PROJECT_ID="braided-topic-452112-v3"
REGION="europe-north1"
TAG="latest"  # or your specific enricher tag

gcloud run jobs deploy enrich-hybrid \
  --project "$PROJECT_ID" --region "$REGION" \
  --image "gcr.io/$PROJECT_ID/paranoid-enricher:$TAG" \
  --max-retries 0 --task-timeout 900s \
  --set-secrets "DEEPSEEK_API_KEY=deepseek-api-key:latest,CURSOR_API_KEY=cursor-gpt5-api-key:latest" \
  --set-env-vars "LLM_PROVIDER_MODE=hybrid,BUCKET=paranoidmodels.com" \
  --command bash \
  --args -lc,"make prod-news-cycle"
```

## Test execution

```bash
gcloud run jobs execute enrich-hybrid --project "$PROJECT_ID" --region "$REGION"
sleep 20
curl -Is https://storage.googleapis.com/paranoidmodels.com/newswire/trends.en.json | head -n1
curl -Is https://storage.googleapis.com/paranoidmodels.com/newswire/trends.fi.json | head -n1
```

## Setup Scheduler (if not already exists)

```bash
SCHEDULER_SA="scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts create scheduler-invoker --project "$PROJECT_ID" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SCHEDULER_SA" --role="roles/run.invoker"

# Scheduler works in europe-west1
gcloud scheduler jobs create http newswire-daily \
  --project "$PROJECT_ID" --location "europe-west1" \
  --schedule "5 6 * * *" \
  --http-method POST \
  --uri "https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/enrich-hybrid:run" \
  --oauth-service-account-email "$SCHEDULER_SA"
```

## GitHub Secrets needed for CI

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

- `GCP_WIF_PROVIDER`: Workload Identity Provider resource path
- `GCP_SA_EMAIL`: Service account email for publishing

Example setup for Workload Identity Federation:
```bash
gcloud iam workload-identity-pools create github-actions --location="global" --project="$PROJECT_ID"
gcloud iam workload-identity-pools providers create-oidc github-oidc \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --project="$PROJECT_ID" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```
