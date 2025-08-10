# 🚨 PARANOID MODEL V5 - COMPLETE PIPELINE

## 🎯 ONE-COMMAND EXECUTION

### **Full Pipeline with Real Data (WGI + GDELT):**
```bash
export CURSOR_API_KEY="your_cursor_api_key_here"
make paranoid-full
```

### **Quick Test with Mock Data:**
```bash
make paranoid-full-mock
# Then optionally: make paranoid-enrich (requires CURSOR_API_KEY)
```

## 📋 WHAT THE PIPELINE DOES

### 1. **Data Acquisition** (`paranoid-data`)
- Downloads **World Governance Indicators (WGI)** from World Bank
- Downloads **GDELT 2.1 Events** (last 90 days)
- Merges and processes into paranoid feature format
- Fallback to synthetic data if downloads fail

### 2. **Model Training** (`paranoid-train`)
- **Multitask learning:** 4 targets simultaneously
  - `sensitive_class` (binary)
  - `suppression_event_6w` (binary) 
  - `narrative_shift_4w` (binary)
  - `conflict_intensity` (continuous)
- **5-fold temporal cross-validation**
- **Isotonic calibration** for binary targets
- **Feature interactions:** secret_history×SOC, coordination×suppression, etc.

### 3. **Quality Gates** (`paranoid-gates`)
- **Performance thresholds:** AUC ≥ 0.86, PR-AUC ≥ 0.80, ECE ≤ 0.05
- **Fairness validation:** Δ-AUC ≤ 0.10 across groups
- **Bias detection:** Regional/actor group analysis

### 4. **Signal Detection** (`paranoid-signal`) 
- **Real-time monitoring:** Analyzes new data samples
- **Anomaly detection:** Propaganda spikes, coordination patterns
- **Risk assessment:** High/medium/low severity classification
- **Evidence collection:** Specific feature anomalies

### 5. **Enrichment** (`paranoid-enrich`)
- **Cursor GPT-5 processing:** Converts signals → newswire cards
- **FT-style output:** kicker, headline, lede, why_it_matters, CTA
- **Publication ready:** JSON for newswire UI

## 🔍 WHAT THE MODEL DETECTS

### **Paranoid Signal Categories:**
- **Anomalies:** Unusual patterns in time series & networks
- **Coordination Signals:** Astroturf/"same message, different sources"
- **Narrative Shifts:** Sudden framing changes
- **Suppression Indicators:** Publication gaps, silence patterns  
- **Secret History Signals:** Indirect echoes + documentation gaps
- **Tail Risk Triggers:** Rare but high-impact combinations

### **Real-world Applications:**
- Media manipulation detection
- Information warfare monitoring
- Narrative shift early warning
- Suppression event prediction
- Coordination campaign identification

## 📊 EXAMPLE OUTPUT

### **Generated Signal:**
```json
{
  "signal_type": "multitarget_anomaly",
  "severity": "high",
  "risk_factors": ["high_sensitivity", "suppression_imminent", "narrative_manipulation"],
  "evidence": ["propaganda_spike: 4.74"],
  "scores": {
    "sensitive_class": 1.0,
    "suppression_6w": 1.0,
    "narrative_shift": 0.986,
    "conflict_intensity": 0.422
  },
  "confidence": 0.95
}
```

### **Enriched Newswire Card:**
```json
{
  "kicker": "Information Warfare",
  "title": "Coordinated Narrative Campaign Detected in Media Networks",
  "lede": "Advanced detection algorithms identified unusual coordination patterns...",
  "why_it_matters": "This represents a significant escalation in information manipulation...",
  "cta": {"label": "Read Analysis", "url": "/analysis/paranoid_0033"}
}
```

## ⚙️ INDIVIDUAL COMMANDS

```bash
# Data acquisition
make paranoid-data          # Download WGI + GDELT
make paranoid-data-existing # Process existing files

# Model pipeline
make paranoid-setup         # Create directories, generate mock
make paranoid-train         # Train multitask models
make paranoid-gates         # Validate quality gates
make paranoid-signal        # Generate paranoid signal
make paranoid-enrich        # Cursor GPT-5 enrichment

# Legacy fertility model
make enrich                 # Old enrichment process
```

## 📁 FILE STRUCTURE

```
artifacts/
├── paranoid_models.joblib      # Trained multitask models
├── metrics.json                # Performance metrics + fairness
├── feature_importance.json     # Feature importance scores
├── signal.raw.json            # Latest detected signal
└── report.enriched.json       # Enriched newswire cards

data/
├── paranoid.csv               # Real WGI+GDELT data
├── paranoid_mock.csv          # Synthetic fallback data
└── raw/                       # Downloaded WGI/GDELT files

config/
└── paranoid_v5.yaml           # Model configuration

scripts/
├── merge_wgi_gdelt.py         # Data acquisition & processing
├── train_paranoid.py          # Multitask model training
├── quality_gates.py           # Performance validation
├── generate_paranoid_signal.py # Signal detection
└── generate_mock.py           # Synthetic data generation
```

## 🚦 QUALITY GATES

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| AUC | ≥ 0.86 | Classification performance |
| PR-AUC | ≥ 0.80 | Precision-recall balance |
| Brier Score | ≤ 0.19 | Calibration quality |
| ECE | ≤ 0.05 | Expected calibration error |
| Δ-AUC | ≤ 0.10 | Fairness across groups |

## 🔧 REQUIREMENTS

### **Python Dependencies:**
```bash
pip3 install pandas numpy scikit-learn pyyaml joblib requests
```

### **Environment Variables:**
```bash
export CURSOR_API_KEY="your_key"      # For GPT-5 enrichment
export CURSOR_API_BASE="..."          # Optional: custom endpoint
export CURSOR_MODEL="gpt-5"          # Optional: model override
```

### **External Data Sources:**
- **WGI:** https://databank.worldbank.org/source/worldwide-governance-indicators
- **GDELT:** http://data.gdeltproject.org/gdeltv2/

## 🎯 INTEGRATION WITH NEWSWIRE

The pipeline outputs `artifacts/report.enriched.json` which feeds directly into the newswire UI:

1. **Signal Detection** → Raw anomaly data
2. **Cursor GPT-5** → Human-readable news cards  
3. **Newswire UI** → FT-style presentation
4. **Quality Gates** → Reliability validation

## 🚀 DEPLOYMENT

### **Local Development:**
```bash
make paranoid-full-mock  # Test with synthetic data
```

### **Production:**
```bash
export CURSOR_API_KEY="prod_key"
make paranoid-full       # Full pipeline with real data
```

### **CI/CD Integration:**
```yaml
- name: Run Paranoid Pipeline
  run: |
    export CURSOR_API_KEY="${{ secrets.CURSOR_API_KEY }}"
    make paranoid-full
  env:
    CURSOR_API_BASE: ${{ vars.CURSOR_API_BASE }}
```

---

## 🎉 **PARANOID MODEL V5 IS PRODUCTION READY!**

The complete pipeline transforms raw governance and event data into publication-ready paranoid intelligence with full quality validation and automated enrichment.

**Ready to detect the undetectable. 🚨**
