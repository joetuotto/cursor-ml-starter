## cursor-ml-starter

Pieni regressioprojektin aloituspohja sekä Cursorille valmiit prompt-template:t (katso `prompt_templates.md`).

### Asennus ja ajo

1) Python-ympäristö
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

2) Aja testit
```bash
pytest -q
```

3) Treenaa malli ja tallenna artefaktit
```bash
python -m src.cli train --csv ./data/data.csv
```

Yhden komennon ajo:
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -r requirements.txt && pytest -q && python -m src.cli train --csv ./data/data.csv
```

### FastAPI Server (Local Development)

Projekti sisältää FastAPI-rajapinnan jossa on:
- `/health` - Palvelimen status
- `/schemas/feed_item.json` - JSON-skeema (FileResponse, Cache-Control headers)
- `/predict` - Mallin käyttö (fertility rate prediction)

#### Lokaali ajo:

```bash
# Asenna riippuvuudet
pip install -r requirements.txt

# Käynnistä API
uvicorn app.main:app --reload --port 8000

# Testaa endpoints
curl -sS http://localhost:8000/health
curl -i http://localhost:8000/schemas/feed_item.json
curl -sS -X POST http://localhost:8000/predict -H 'content-type: application/json' \
  -d '{"emf":1.5,"income":2500,"urbanization":0.6}'
```

#### Cloud Run Deployment:

```bash
# Deploy source-based
gcloud run deploy fertility-api \
  --region europe-north1 \
  --source . \
  --update-env-vars SCHEMA_PATH=/app/artifacts/feed_item_schema.json,MODEL_VERSION=gb-1.0.0 \
  --allow-unauthenticated

# Test deployed API
curl -sS https://fertility-api-<hash>-ew.a.run.app/health
```

**Huom:** Schema-endpoint vaatii että `artifacts/feed_item_schema.json` tiedosto on olemassa. Luo se ajamalla malli-training ensin.

### Ops / Runbook

Squash-merge ja prod-smoke yhdellä komennolla

```bash
# 1) Tarkista PR:n checkit
gh pr checks <PR_NUMBER> --watch

# 2) Squash-merge ja poista feature-branch
gh pr merge --squash --delete-branch --admin <PR_NUMBER>

# 3) Aja prod-smoke rikasteelle, avaa run-sivu ja validoi skeema
export CURSOR_API_KEY=...   # required
make enrich-smoke-prod
```

Varmistus
- GitHub Actions run vihreänä: post-merge enrich-smoke
- Slack/TG ilmoitus näkyy (kicker + lede)
- Paikallinen `artifacts/report.enriched.json` skeemavalidoituu [ok]
- Tarkista `/newswire` prod-ympäristössä

Rollback

```bash
gh pr list --state merged --limit 5
gh pr revert <PR_NUMBER>
make enrich-smoke-prod
```

#### Notification Dry-Run

Voit esikatsella Slack- ja Telegram-notifikaatiot ilman lähetystä:

```bash
export CURSOR_API_KEY=...
NOTIFY_DRY_RUN=1 make enrich-smoke-prod-notify
```

Tulostaa notifikaatioiden payloadit konsoliin (Slack/TG), ei lähetä niitä.

#### CI env (CURSOR_*)

Workflows käyttävät CURSOR_* -muuttujia Secrets/Vars-lähteistä:

```yaml
env:
  CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
  CURSOR_API_BASE: ${{ vars.CURSOR_API_BASE || 'https://api.openai.com/v1' }}
  CURSOR_MODEL: ${{ vars.CURSOR_MODEL || 'gpt-4o' }}
```

Manuaalinen enrich-smoke (workflow_dispatch):

```bash
gh workflow run post-merge-enrich-smoke.yml --ref main
sleep 6
RUN_URL=$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json url --jq '.[0].url'); echo "$RUN_URL"
RUN_ID=$(gh run list --workflow post-merge-enrich-smoke.yml --limit 1 --json databaseId --jq '.[0].databaseId')
mkdir -p artifacts && gh run download "$RUN_ID" --name report.enriched.json -D artifacts
jq '{kicker, lede, category, cta}' artifacts/report.enriched.json
```

### UI Smoke (Puppeteer)
- Local:
  ```bash
  cd web
  export PROD_URL="https://api.paranoidmodels.com"
  node tests/e2e/prod.newswire.smoke.cjs
  ```

- Makefile:
  ```bash
  make ui-smoke-prod             # uses PROD_URL or defaults to https://api.paranoidmodels.com
  ```

- CI (manual): Actions → UI Smoke (Puppeteer) → Run workflow
  (Optional prod_url overrides default)

### Multi-Environment Matrix Testing
Post-deploy UI smoke tests run against multiple environments:
- **Production**: `PROD_URL` (vars.PROD_URL or default)
- **Staging**: `STAGING_URL` (vars.STAGING_URL, skipped if empty)

Configure in GitHub repository settings:
- Variables: `PROD_URL`, `STAGING_URL` 
- Secrets: `SLACK_WEBHOOK_URL`, `TG_BOT_TOKEN`, `TG_CHAT_ID` (optional)
