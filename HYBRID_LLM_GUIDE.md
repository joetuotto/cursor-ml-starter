# PARANOID Hybrid LLM System

## 🎯 Concept: DeepSeek + GPT-5 Budget Optimization

**Budget: €30/month** strategically split for maximum efficiency:

- **DeepSeek R1**: €20/month (~$22) for volume work
- **GPT-5 (Cursor)**: €10/month (~$11) for premium analysis
- **Total capacity**: ~1000-1300 articles/month

## 🧠 Intelligent Routing

### DeepSeek R1 ($0.55/$2.19 per 1M tokens)
**Use for:**
- ✅ Standard news analysis (80% of content)
- ✅ Basic category detection
- ✅ Initial enrichment drafts
- ✅ Non-critical global content
- ✅ Volume processing

**Monthly capacity**: ~800-1200 articles

### GPT-5 ($1.25/$10.0 per 1M tokens)
**Use for:**
- 🎯 Finnish content (better localization)
- 🎯 Critical financial news (Fed, ECB, etc.)
- 🎯 Quality control for DeepSeek output
- 🎯 Complex analysis requiring precision
- 🎯 Final validation and improvement

**Monthly capacity**: ~80-120 articles

## 🤖 Smart Routing Logic

```python
# Auto-routing based on content analysis
if content_is_finnish():
    route_to_gpt5()  # Better Finnish understanding
elif content_is_critical():
    route_to_gpt5()  # Fed, ECB, crisis news
elif content_is_complex_financial():
    route_to_gpt5()  # Multi-variable analysis
else:
    route_to_deepseek()  # Volume processing

# Quality control layer
if used_deepseek() and quality_issues_detected():
    gpt5_quality_improvement()  # Hybrid validation
```

## 💰 Cost Breakdown (€30/month)

| Model | Budget | Cost/1M tokens | Articles/month | Use Case |
|-------|--------|----------------|----------------|----------|
| **DeepSeek R1** | €20 ($22) | $0.55/$2.19 | 800-1200 | Volume work |
| **GPT-5** | €10 ($11) | $1.25/$10.0 | 80-120 | Premium analysis |
| **Total** | €30 | Mixed | 1000-1300 | Full pipeline |

### Example Monthly Distribution:
- 🇫🇮 **Finnish articles**: 100-150 (all GPT-5)
- 🌍 **Global critical**: 50-80 (GPT-5)
- 📊 **Standard analysis**: 800-1000 (DeepSeek)
- 🔍 **Quality controlled**: 300-500 (DeepSeek + GPT-5 validation)

## 🚀 Setup & Usage

### 1. Environment Setup
```bash
# API Keys
export DEEPSEEK_API_KEY="your_deepseek_key"
export CURSOR_API_KEY="your_cursor_key"

# Setup hybrid system
make hybrid-setup
```

### 2. Basic Usage
```bash
# Test routing logic
make hybrid-test

# Process Finnish content
make hybrid-fi

# Check costs
make hybrid-cost

# Full hybrid enrichment
make hybrid-enrich
```

### 3. Production Integration
```python
from src.paranoid_model.hybrid_llm import HybridEnricher

enricher = HybridEnricher()

# Auto-routes to best model based on content
result = enricher.enrich_signal(signal, schema)

# Track costs automatically
summary = enricher.get_cost_summary()
print(f"Monthly cost: ${summary['total_cost']:.2f}")
```

## 📊 Expected Performance

### Quality Levels:
- **DeepSeek**: Good quality, 600+ word analysis
- **GPT-5**: Premium quality, 700+ word analysis + localization
- **Hybrid QC**: DeepSeek + GPT-5 validation = Premium at volume cost

### Volume Estimates:
- **Finnish content**: 100% GPT-5 quality
- **Critical global**: 100% GPT-5 quality  
- **Standard content**: DeepSeek quality with selective GPT-5 improvement
- **Overall**: 90% premium quality at 60% premium cost

## 🎛️ Configuration

Edit `config/hybrid_llm.yaml`:

```yaml
models:
  deepseek:
    monthly_budget_usd: 22.0
    use_cases: ["volume_content", "basic_enrichment"]
  
  gpt5:
    monthly_budget_usd: 11.0
    use_cases: ["finnish_content", "critical_analysis"]

routing_rules:
  finnish_to_gpt5: true
  critical_keywords: ["federal reserve", "ecb", "suomen pankki"]
  quality_control:
    enabled: true
    deepseek_output_validation: true
```

## 🔍 Monitoring & Alerts

### Cost Tracking:
- Real-time budget monitoring
- 80% usage alerts
- Emergency mode at 95% budget
- Monthly reset and reporting

### Quality Metrics:
- Model routing decisions
- Quality control improvements
- Validation pass rates
- User satisfaction scores

## 🎯 ROI Analysis

**Compared to GPT-5 only** (€30 budget):
- GPT-5 only: ~240 articles/month
- Hybrid system: ~1000+ articles/month
- **4x more content** for same budget

**Compared to DeepSeek only**:
- Better quality for critical content
- Finnish localization maintained
- Professional-grade output for key stories

## 🛠️ Implementation Notes

### Fallback Strategy:
1. Try preferred model (based on routing)
2. If over budget, use fallback model
3. Emergency mode: cheapest available option
4. Quality control always attempted if budget allows

### Caching & Optimization:
- Response caching for similar content
- Token counting and optimization
- Batch processing where possible
- Smart prompt engineering for cost efficiency

---

**Result**: Professional-grade news analysis at €30/month, optimized for Finnish market with global coverage. 🇫🇮📰
