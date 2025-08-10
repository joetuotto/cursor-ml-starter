# 🚀 PARANOID MODEL V5 - ENTERPRISE GO-LIVE PLAYBOOK

## ⏱️ **15-MINUTE GO-LIVE** (Production Ready)

### **1. Secrets & Environment (2 min)**
```bash
# REQUIRED
export CURSOR_API_KEY="sk-cursor-..."
export PARANOID_RANGE_DAYS=90
export PARANOID_MIN_EVENTS=200000
export PARANOID_TEMPORAL_CV=1

# OPTIONAL (Cloud deployment)
export S3_BUCKET="your-newswire-bucket"
export S3_PREFIX="paranoid-artifacts"

# OPTIONAL (Alerting)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export TG_BOT_TOKEN="123456:ABC-DEF..."
export TG_CHAT_ID="@your_channel"

# OPTIONAL (API endpoint for health checks)
export PROD_URL="https://api.paranoidmodels.com"
```

### **2. Full Pipeline Execution (10 min)**
```bash
# Complete intelligence pipeline
make paranoid-enterprise
```

**This executes:**
- 🌍 **Data acquisition:** WGI + GDELT download & processing
- 🤖 **ML training:** Multitask models + isotonic calibration
- 🚦 **Quality validation:** Performance + fairness + calibration gates
- 🚨 **Signal detection:** 6 paranoid signal categories
- 🤖 **GPT-5 enrichment:** Publication-ready newswire cards
- 🕵️ **HUMINT analysis:** Actor networks + motive hypotheses
- 📊 **Drift monitoring:** Model health + alerts
- ☁️ **Cloud deployment:** S3/Azure/GCS artifact sync
- 📄 **HTML reports:** Comprehensive test documentation
- 📊 **Monitoring setup:** Grafana dashboard ready

### **3. Verification (3 min)**
```bash
# Health check
make paranoid-production-check

# Manual verification
ls -la deploy/production/     # Local artifacts
ls -la test-reports/         # HTML reports
cat artifacts/run_meta.json | jq .quality_gates  # Quality status
```

**Expected outputs:**
- ✅ `deploy/production/report.enriched.json` (newswire feed)
- ✅ `artifacts/humint_profile.json` (intelligence analysis)
- ✅ `artifacts/drift_report.json` (model health)
- ✅ `test-reports/paranoid-*/index.html` (comprehensive report)
- ✅ `monitoring/grafana-paranoid-dashboard.json` (monitoring)

---

## 📊 **QUALITY GATES** (Fail-Fast)

| **Gate** | **Threshold** | **Action on Fail** |
|----------|---------------|-------------------|
| AUC (all targets) | ≥ 0.86 | Block deployment, retrain |
| PR-AUC | ≥ 0.80 | Block deployment |
| ECE (calibration) | ≤ 0.05 | Recalibration required |
| Δ-AUC (fairness) | ≤ 0.10 | Bias investigation |
| GDELT events | ≥ 200k | Wait for more data |
| Why It Matters coverage | ≥ 80% | Enrichment review |

**Override:** Use `--force` flag only for emergencies

---

## 🗓️ **PRODUCTION OPERATIONS**

### **Daily Cron (08:05 UTC)**
```bash
0 8 * * * /bin/bash -lc 'cd /app && make paranoid-enterprise >> logs/paranoid.log 2>&1'
```

### **Health Monitoring**
```bash
# Continuous health check
make paranoid-health-check

# Comprehensive drift analysis
make paranoid-drift

# UI/Frontend validation  
make paranoid-smoke

# Generate detailed reports
make paranoid-report
```

### **Emergency Procedures**
```bash
# Rollback to previous backup
make paranoid-rollback

# Force deployment (bypass gates)
make paranoid-deploy-force

# Debug data acquisition
make paranoid-debug
```

---

## 📈 **MONITORING & ALERTING**

### **Grafana Dashboard**
1. Import `monitoring/grafana-paranoid-dashboard.json`
2. Configure Prometheus data source
3. Set up alert channels (Slack/PagerDuty)

**Key Metrics:**
- 🎯 **Model Performance:** AUC trends, fairness metrics
- 🚨 **Signal Detection:** Rate, severity distribution
- 📊 **Quality Gates:** Pass/fail status over time
- 🕵️ **HUMINT Networks:** Active networks, hypothesis confidence
- 📈 **Concept Drift:** AUC degradation, calibration shift
- 🌍 **Data Pipeline:** GDELT events, enrichment success rate
- 🎭 **UI Metrics:** Load time, coverage, cards rendered

### **Automated Alerts**
- **Critical:** AUC drop > 0.10, quality gate failures
- **Warning:** AUC drop 0.05-0.10, calibration drift
- **Info:** Pipeline completion, daily summaries

---

## 🏢 **ENTERPRISE COMMANDS**

### **Core Operations:**
```bash
make paranoid-complete      # Full intelligence pipeline
make paranoid-enterprise    # Complete + deployment + reporting
make paranoid-deploy        # Cloud artifact deployment
make paranoid-report        # HTML test reports
make paranoid-monitor       # Grafana dashboard setup
```

### **Specialized Analysis:**
```bash
make paranoid-humint        # Actor intelligence & motive analysis
make paranoid-drift         # Concept drift detection
make paranoid-temporal      # Enhanced temporal cross-validation
make paranoid-debug         # Data acquisition debugging
```

### **Production Validation:**
```bash
make paranoid-production-check  # Complete health validation
make paranoid-health-check      # API health only
make paranoid-smoke            # UI/frontend testing
```

---

## 🔄 **ROLLBACK & RECOVERY**

### **Automatic Backup System:**
- **Before deployment:** Current artifacts backed up
- **Timestamped backups:** `backups/YYYY-MM-DDTHH-MM-SS/`
- **Cloud versioning:** S3/Azure with object versioning

### **Rollback Procedures:**
```bash
# Automatic (latest backup)
make paranoid-rollback

# Manual (specific timestamp)
python3 scripts/deploy_artifacts.py --rollback 2024-08-10T08-05-00

# Emergency (local restore)
cp backups/latest/* deploy/production/
```

---

## 🛡️ **GOVERNANCE & COMPLIANCE**

### **Audit Trail** (`artifacts/run_meta.json`):
```json
{
  "deployment": {
    "timestamp": "2024-08-10T08:05:00Z",
    "deployer": "ci-cd-user",
    "commit_hash": "abc123def456",
    "environment": "production"
  },
  "data_sources": {
    "wgi_snapshot_date": "2024-08-09T12:00:00Z",
    "gdelt_range_days": 90,
    "data_version": "sha256:1a2b3c4d..."
  },
  "quality_gates": {
    "overall_status": "PASS",
    "auc_minimum": true,
    "fairness_check": true,
    "calibration_check": true
  },
  "governance": {
    "pii_compliance": "actor_fields_only",
    "bias_monitoring": "enabled",
    "audit_trail": true,
    "retention_days": 90
  }
}
```

### **Bias Minimization:**
- **Residual debiasing:** Automatic fairness corrections
- **Group monitoring:** Regional/actor type AUC tracking
- **Drift detection:** Bias shift alerts
- **Regular audits:** Monthly fairness reports

### **Data Privacy:**
- **No PII collection:** Only public actor fields
- **Anonymization:** Handle/ID masking where needed
- **Retention policy:** 90-day automatic cleanup
- **GDPR compliance:** Right to be forgotten support

---

## 🎯 **SUCCESS CRITERIA**

### **Go-Live Acceptance:**
- ✅ `make paranoid-enterprise` completes successfully
- ✅ All quality gates PASS
- ✅ Why It Matters coverage ≥ 80%
- ✅ Drift status: "stable"
- ✅ Newswire feed published and accessible
- ✅ HTML reports generated
- ✅ Grafana dashboard operational

### **Operational Readiness:**
- ✅ Daily cron job configured
- ✅ Alert channels tested
- ✅ Rollback procedures verified
- ✅ Team trained on operations
- ✅ Documentation accessible

---

## 🚀 **DEPLOYMENT ENVIRONMENTS**

### **Development:**
```bash
export DEPLOYMENT_ENV=development
make paranoid-full-mock    # Use synthetic data
```

### **Staging:**
```bash
export DEPLOYMENT_ENV=staging
export S3_BUCKET=paranoid-staging
make paranoid-enterprise
```

### **Production:**
```bash
export DEPLOYMENT_ENV=production
export S3_BUCKET=paranoid-production
make paranoid-enterprise
```

---

## 📞 **SUPPORT & ESCALATION**

### **Level 1 (Operational):**
- **Issue:** Pipeline failures, quality gate violations
- **Actions:** Check logs, run diagnostics, attempt restart
- **Escalate if:** Multiple consecutive failures

### **Level 2 (Technical):**
- **Issue:** Model performance degradation, bias detection
- **Actions:** Drift analysis, data investigation, model retraining
- **Escalate if:** Systematic bias or security concerns

### **Level 3 (Strategic):**
- **Issue:** Data source compromises, fundamental model issues
- **Actions:** Emergency procedures, stakeholder communication
- **Authority:** Model freeze, external data source integration

---

## 🎉 **PARANOID MODEL V5 - ENTERPRISE READY!**

**Complete Intelligence Pipeline featuring:**
- 🌍 **Real-time data ingestion** (WGI + GDELT)
- 🤖 **Multitask machine learning** (4 paranoid targets)
- 🚦 **Production quality gates** (performance + fairness)
- 🚨 **Signal detection** (6 paranoid categories)
- 🤖 **GPT-5 enrichment** (publication-ready cards)
- 🕵️ **HUMINT analysis** (actor networks + motives)
- 📊 **Concept drift monitoring** (automated alerts)
- ☁️ **Enterprise deployment** (S3/Azure/GCS)
- 📄 **Comprehensive reporting** (HTML + JSON)
- 📊 **Grafana monitoring** (production dashboards)

**Ready to detect the undetectable at enterprise scale. 🏢🚨🎯**
