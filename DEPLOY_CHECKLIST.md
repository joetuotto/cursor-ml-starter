# PARANOID V5 – Deploy Checklist (Cloud Run + Self-healing)

**Goal:** zero-downtime deploy with automatic rollback if health checks fail.  
**Scope:** paranoid-api + paranoidmodels.com (custom domain) + static backup (GCS).

---

## 0) Prereqs

**gcloud auth set and project selected:**

```bash
gcloud auth login
gcloud config set project braided-topic-452112-v3
```

**Tools:** gcloud, gsutil, docker (if you build locally), make

**Environment:**

```bash
export PROJECT_ID="braided-topic-452112-v3"
export REGION="europe-north1"
export DOMAIN="paranoidmodels.com"
export SERVICE="paranoid-api"
# optional (for metrics)
export PROMETHEUS_PUSHGATEWAY_URL="http://prometheus:9091"
```

---

## 1) Preflight sanity

```bash
# repo clean?
git status

# cloud run reachable?
gcloud run services list --region "$REGION" | grep "$SERVICE" || echo "Service will be created"

# domain mapping?
gcloud beta run domain-mappings list --region "$REGION" | grep "$DOMAIN" || echo "Mapping will be created/updated"
```

---

## 2) Build frontend & static backup (GCS)

```bash
npm --prefix web ci
npm --prefix web run build

# create/update static site bucket (backup & emergency)
gsutil mb -l "$REGION" "gs://$DOMAIN" || true
gsutil web set -m index.html -e 404.html "gs://$DOMAIN"
gsutil -m rsync -r web/dist "gs://$DOMAIN"
gsutil iam ch allUsers:objectViewer "gs://$DOMAIN" || true
```

---

## 3) Build & push container image (optional)

If you're shipping a new backend revision:

```bash
export IMAGE="gcr.io/$PROJECT_ID/paranoid-api:$(git rev-parse --short HEAD)"
docker build -t "$IMAGE" .
docker push "$IMAGE"
```

If you aren't changing the image, you can skip to step 5 (mapping), or use the self-healing script to do mapping-only + health.

---

## 4) Self-healing deploy (to Cloud Run URL first)

We never switch custom domain/traffic until health checks pass on the Cloud Run URL.

```bash
# creates new revision (if IMAGE set), updates mapping, runs health checks,
# and auto-rolls back on failure
IMAGE="$IMAGE" \
PROJECT_ID="$PROJECT_ID" REGION="$REGION" DOMAIN="$DOMAIN" SERVICE="$SERVICE" \
bash scripts/deploy_paranoid_full.sh
```

**What this does:**
- Snapshots current revision & domain mapping (for rollback)
- (Optional) Deploys new revision from `$IMAGE`
- Keeps old revision receiving traffic until health passes
- **Health checks:**
  - `GET/HEAD https://<service-hash>.a.run.app/`
  - `GET/HEAD https://<service-hash>.a.run.app/health`
- **On failure:** reverts traffic + restores previous domain mapping

---

## 5) Domain mapping (custom domain)

Only after Cloud Run URL passes health:

```bash
# (re)map custom domain to the service
gcloud beta run domain-mappings delete \
  --domain "$DOMAIN" --region "$REGION" --quiet || true

gcloud beta run domain-mappings create \
  --service "$SERVICE" \
  --domain "$DOMAIN" --region "$REGION"
```

**SSL provisioning:** allow 15–24h on first setup. While waiting, site is reachable at the Cloud Run URL and via the GCS backup:
- **Cloud Run:** `https://<paranoid-api-*-hash>.a.run.app/`
- **Static backup:** `https://storage.googleapis.com/$DOMAIN/index.html`

---

## 6) Post-deploy validation

**Cloud Run URL (authoritative health):**

```bash
# HEAD must be 200
curl -I https://<cloud-run-url>/        --connect-timeout 10 --max-time 15
curl -I https://<cloud-run-url>/health  --connect-timeout 10 --max-time 15

# assets
curl -I https://<cloud-run-url>/assets/index-*.js
```

**Custom domain (once SSL ready):**

```bash
curl -I https://$DOMAIN/        --connect-timeout 10 --max-time 15
curl -I https://$DOMAIN/health  --connect-timeout 10 --max-time 15
```

**Browser checks:**
- Hard refresh (Ctrl/Cmd+Shift+R)
- DevTools Console: no CORS or 404 on `/assets/*`
- DevTools Network: SPA routes resolve `index.html`

---

## 7) Rollback (manual)

If anything looks off after traffic switch:

```bash
# find previous healthy revision
gcloud run services describe "$SERVICE" --region "$REGION" \
  --format='table(status.traffic[].revisionName,status.traffic[].percent)'

# send 100% traffic back
gcloud run services update-traffic "$SERVICE" \
  --region "$REGION" --to-revisions <REVISION_NAME>=100

# optionally restore domain mapping to previous service
SERVICE_PREV="fertility-api" make rollback-paranoid
# or:
SERVICE_PREV="fertility-api" bash scripts/rollback_paranoid.sh
```

---

## 8) Smoke & monitoring

**Playwright/Puppeteer smoke (optional):**

```bash
make paranoid-smoke    # requires Node deps in /web/tests/e2e
```

**Metrics & alerts (optional if configured):**

```bash
# push deploy status to Prometheus Pushgateway
PROMETHEUS_PUSHGATEWAY_URL="http://prometheus:9091" \
python3 scripts/prometheus_exporter.py --artifacts_dir artifacts

# alert tests
make paranoid-test-alert-auc
```

---

## 9) Common issues & fixes

**405 on HEAD**  
Add a global HEAD handler before SPA fallback in your server:

```javascript
app.head('*', (req, res) => res.status(200).end());
```

**SPA routes 404**  
Ensure fallback:

```javascript
app.use('/assets', express.static('web/dist/assets'));
app.get('*', (_, res) => res.sendFile(path.join(__dirname, 'web/dist/index.html')));
```

**CORS errors for assets**  
Allow origin `https://paranoidmodels.com` for static responses. For GCS backup, objects are public.

**SSL pending**  
Domain mapping is fine; use Cloud Run URL or GCS backup until cert is "ACTIVE".

**Custom domain health failing but Cloud Run URL ok**  
Don't use custom domain for health immediately after mapping. Our deploy script already checks Cloud Run URL; keep that.

---

## 10) One-liners

**Full deploy with new image (recommended):**

```bash
export IMAGE="gcr.io/$PROJECT_ID/paranoid-api:$(git rev-parse --short HEAD)"
make deploy-paranoid-with-image
```

**Mapping-only refresh (no new image):**

```bash
make deploy-paranoid
```

**Emergency rollback:**

```bash
REVISION="<paranoid-api-000xx-abc>" make rollback-paranoid
```

---

## 11) Runbook (who does what)

- **On-call (ML-Ops):** run deploy, validate health, watch alerts; rollback if alerts fire
- **App/Frontend:** fix SPA/CORS/asset issues; verify browser console
- **Infra:** DNS/SSL issues, domain mappings, quotas

---

## 12) Appendices

**Self-healing deploy script:** `scripts/deploy_paranoid_full.sh`  
**Manual rollback script:** `scripts/rollback_paranoid.sh`  

**Make targets:**

```makefile
deploy-paranoid:               # mapping + health + auto-rollback
	@bash scripts/deploy_paranoid_full.sh

deploy-paranoid-with-image:    # same + new revision from IMAGE
	@IMAGE=$(IMAGE) bash scripts/deploy_paranoid_full.sh

rollback-paranoid:
	@bash scripts/rollback_paranoid.sh
```

---

**That's it.** Always validate on the Cloud Run URL first, let SSL finish for the custom domain, and keep one healthy revision around for instant rollback.
