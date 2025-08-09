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
