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
