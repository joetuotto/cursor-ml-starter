# 🚀 Drop-in Hybrid LLM System

**PARANOID V5 — DeepSeek + GPT-5 Budget Optimization**

## ✅ Quick Start (2 commands)

```bash
make hybrid-setup && make hybrid-test
```

## 🎯 What You Get

**€30/month budget optimally split:**
- **DeepSeek R1**: €20 for volume work (800-1200 articles)
- **GPT-5**: €10 for premium analysis (80-120 articles)
- **Total capacity**: 1000-1300 articles/month

## 🧠 Smart Routing

**Automatic GPT-5 routing for:**
- 🇫🇮 Finnish content (better localization)
- 🏛️ Critical topics (Fed, ECB, Suomen Pankki)
- 📊 Complex financial analysis
- 🔍 Quality control validation

**DeepSeek for everything else:**
- Standard news analysis
- Category detection
- Volume processing

## 📁 File Structure

```
├─ env.example                  # Copy to .env
├─ config/hybrid.yaml          # Routing rules & budgets
├─ src/hybrid/
│  ├─ router.py                # Smart content routing
│  ├─ models.py                # DeepSeek + GPT-5 wrappers
│  ├─ cache.py                 # 72h duplicate protection
│  ├─ validate.py              # Quality validation
│  └─ pipeline.py              # Main processing pipeline
├─ scripts/
│  ├─ hybrid_test.py           # Test with 3 sample items
│  └─ hybrid_budget.py         # Cost tracking
└─ artifacts/
   └─ report.enriched.json     # Output (UI-ready format)
```

## 🚀 Usage

### Basic Commands:
```bash
# Setup (creates cache dir, checks .env)
make hybrid-setup

# Test routing with 3 sample items
make hybrid-test

# Full batch processing
make hybrid-run

# Check monthly costs
make hybrid-cost
```

### Sample Output:
```bash
$ make hybrid-test
📰 "Suomen Pankki nostaa korkoja..." → GPT-5 (Finnish)
📰 "Fed signals rate pause..." → GPT-5 (Critical)
📰 "Tech startup funding..." → DeepSeek (Standard)
✅ Saved → artifacts/report.enriched.json
```

## ⚙️ Configuration

### Environment (.env):
```bash
DEEPSEEK_API_KEY=sk-deepseek-...
CURSOR_API_KEY=sk-cursor-...
DEEPSEEK_MONTHLY_EUR=20
GPT5_MONTHLY_EUR=10
```

### Routing Rules (config/hybrid.yaml):
```yaml
routing:
  force_gpt5_languages: ["fi"]
  critical_topics: ["federal reserve", "ecb", "suomen pankki"]
  complexity_threshold: 0.50
  risk_threshold: 0.40

budget:
  deepseek_monthly: 20
  gpt5_monthly: 10
```

## 📊 Cost Protection

- **Real-time budget tracking** (.cache/hybrid/usage.json)
- **72-hour caching** (prevents duplicate processing)
- **Quality validation** (failed DeepSeek → GPT-5 retry)
- **Monthly reset** (automatic budget rollover)

## 🔌 Integration

The system outputs standard `artifacts/report.enriched.json` format:

```json
[
  {
    "kicker": "Paranoid Analysis",
    "headline": "News title",
    "lede": "Analysis content",
    "why_it_matters": "Impact explanation",
    "cta": {"href": "source-url", "label": "Lähde"},
    "model": "gpt5|deepseek",
    "confidence": 0.86,
    "lang": "fi|en",
    "country": "FI|US|EU"
  }
]
```

**UI Integration:**
- Existing newswire UI reads `artifacts/report.enriched.json`
- No UI changes needed
- Works with current deployment pipeline

## 🎯 ROI Analysis

**vs GPT-5 only (€30):**
- GPT-5 only: ~240 articles/month
- **Hybrid**: ~1000+ articles/month
- **4x more content** for same budget

**vs DeepSeek only:**
- Better quality for critical Finnish content
- Professional-grade analysis for key stories
- Smart quality control with GPT-5 validation

## 🛠️ Customization

### Add New Critical Topics:
```yaml
# config/hybrid.yaml
routing:
  critical_topics:
    - "your keyword"
    - "another topic"
```

### Adjust Budget Split:
```yaml
budget:
  deepseek_monthly: 25  # More volume
  gpt5_monthly: 5       # Less premium
```

### Change Cache Duration:
```yaml
cache:
  ttl_hours: 24  # Shorter cache (more API calls)
```

## 🧪 Testing

```bash
# Test routing logic
make hybrid-test

# Check budget status
make hybrid-cost

# Validate output format
jq '.[] | keys' artifacts/report.enriched.json
```

## 🔄 Production Pipeline

Replace existing enrichment step:
```bash
# Old way
make fi-enrich

# New hybrid way  
make hybrid-run
```

**Result**: Same output format, 4x more capacity, budget-optimized! 🎉

---

**Ready for production deployment with existing PARANOID infrastructure!** 🇫🇮🚀
