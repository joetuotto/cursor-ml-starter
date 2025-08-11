#!/usr/bin/env bash
set -euo pipefail

# PARANOID V5 - Cloud Run Deployment Script

PROJECT_ID="${PROJECT_ID:?missing}"
REGION="${REGION:-europe-north1}"
SERVICE_NAME="${SERVICE_NAME:-paranoid-api}"
IMAGE_NAME="${IMAGE_NAME:-paranoid-api:latest}"

echo "🚀 PARANOID V5 - Cloud Run Deployment"
echo "====================================="
echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"
echo "  Image: $IMAGE_NAME"

gcloud config set project "$PROJECT_ID"

# Build & push
echo "🏗️ Building and pushing container..."
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --max-instances=10 \
  --memory=512Mi \
  --timeout=600 \
  --set-env-vars=CURSOR_API_KEY=${CURSOR_API_KEY:-},PROMETHEUS_PUSHGATEWAY_URL=${PROMETHEUS_PUSHGATEWAY_URL:-} \
  --ingress all

# Get URL and test
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format="value(status.url)")

echo "✅ Deployment successful!"
echo "🌐 Service URL: $SERVICE_URL"

# Test the deployment
echo "🧪 Testing deployment..."
if curl -f -s "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

echo "🎉 PARANOID V5 deployed successfully!"
echo "🔗 Access your API at: $SERVICE_URL"
echo "📊 Health endpoint: $SERVICE_URL/health"
echo "🔮 Predict endpoint: $SERVICE_URL/predict"
