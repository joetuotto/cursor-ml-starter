# 🧠 PARANOID Self-Learning System v1.0

**Production-ready intelligent content routing with automatic quality optimization**

## 🎯 What It Does

The self-learning system automatically improves content quality and cost efficiency over time using:

- **Contextual Bandit**: Smart routing between DeepSeek and GPT-5 based on content type, quality needs, and budget
- **Prompt Optimization**: A/B testing and Bayesian optimization of prompt variants 
- **Budget Management**: Automatic cost control with soft/hard caps to stay within €30/month
- **Quality Gates**: Continuous monitoring with automatic rollback on quality degradation
- **Zero Maintenance**: Daily learning cycles run automatically via cron

## 📊 Key Metrics

After implementation:
- **4x more content** vs GPT-5 only approach
- **€30/month budget** with automatic optimization
- **Finnish content prioritized** with local relevance scoring
- **Quality protection** with automatic rollback

## 🚀 Quick Start

```bash
# Setup (one-time)
make selflearn-setup

# Test the system
make selflearn-test

# Run daily learning (add to cron)
make selflearn-daily

# Generate status report  
make selflearn-report
```

## 🏗️ Architecture

### Core Components

1. **Router** (`src/hybrid/router.py`) - Smart model selection with context awareness
2. **Bandit** (`src/hybrid/bandit.py`) - Thompson sampling for exploration/exploitation
3. **Prompter** (`src/hybrid/prompter.py`) - Automatic prompt variant tuning
4. **Evaluator** (`src/hybrid/evaluator.py`) - Quality assessment and regression detection
5. **Calibrator** (`src/hybrid/calibrator.py`) - Budget management and cost optimization
6. **Collector** (`src/hybrid/collector.py`) - Feedback logging and data collection

### API Endpoints

- `POST /feedback` - Receive user interactions (clicks, time-on-card, shares)
- `GET /selflearn/status` - System status and metrics
- `GET /newswire` - Content with self-learning routing
- `GET /newswire/fi` - Finnish content (automatically prioritizes GPT-5)

## 📈 How It Learns

### 1. Content Routing
- **Finnish content** → Always GPT-5 (cold start rule)
- **Critical topics** (ECB, Fed, Security) → GPT-5
- **High complexity/risk** → GPT-5  
- **Standard content** → DeepSeek (cost efficient)

### 2. Quality Feedback Loop
```
Content Generated → User Interaction → Quality Assessment → Model Update → Better Routing
```

### 3. Budget Optimization
- **Under budget** → Allow more GPT-5 usage
- **Soft cap (110%)** → Reduce GPT-5, increase DeepSeek
- **Hard cap (125%)** → Emergency mode, minimal GPT-5
- **Projected overspend** → Freeze experimentation

### 4. Automatic Rollback
Triggers when:
- Card pass rate < 80%
- Hallucination rate > 5%
- Reference miss rate > 10%
- Coverage (why-it-matters) < 85%

## 🔧 Configuration

Edit `config/selflearn.yaml`:

```yaml
# Budget constraints
calibration:
  target_budget_eur_month: 30
  soft_cap: 1.10    # 110% = start reducing GPT-5
  hard_cap: 1.25    # 125% = emergency mode

# Quality requirements  
quality_gates:
  min_card_pass_rate: 0.80
  max_hallu_rate: 0.05
  
# Learning parameters
routing:
  algorithm: "thompson"  # or "ucb"
  cost_weight: 0.25
  quality_weight: 0.75
```

## 📊 Monitoring

### Real-time Status
```bash
curl http://localhost:8080/selflearn/status
```

### Daily Reports
```bash
make selflearn-report
open artifacts/selflearn/report.html
```

### Key Files
- `artifacts/feedback/events.jsonl` - All user interactions
- `artifacts/selflearn/latest_cycle.json` - Last learning cycle results
- `artifacts/selflearn/bandit_state.json` - Model performance tracking
- `artifacts/selflearn/budget_state.json` - Spending and projections

## 🛡️ Safety Features

### Quality Protection
- Regression detection compares last 7 vs previous 7 days
- Statistical significance testing (binomial test)
- Automatic rollback to conservative settings
- Audit trail of all changes

### Budget Safety
- Hard cap prevents runaway costs
- Emergency mode maintains essential functionality
- Frozen mode stops experimentation when needed
- Real-time spending tracking

### Bias Prevention  
- Segment-specific quality monitoring
- Evidence-required prompts for sensitive topics
- Source grounding validation
- No PII in feedback logs

## 🔗 Integration Examples

### Frontend Feedback
```javascript
// Track user engagement
fetch('/feedback', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    event_id: 'nw_20250811_001234',
    type: 'user',
    data: {
      click: 1,
      time_on_card: 45,
      share: 1,
      feedback: 'useful'
    }
  })
});
```

### Editor Workflow
```javascript
// Track editorial decisions
fetch('/feedback', {
  method: 'POST', 
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    event_id: 'nw_20250811_001234',
    type: 'editor',
    data: {
      accepted: 1,
      edits: 0.1,
      publish: 1
    }
  })
});
```

## 🕐 Production Schedule

### Daily (Cron)
```bash
# Run at 02:10 UTC daily
10 2 * * * cd /app && make selflearn-daily >> logs/selflearn.log 2>&1
```

### Weekly
```bash
# Generate comprehensive report
make selflearn-report
```

### Monthly  
- Budget reset (automatic)
- Review quality trends
- Adjust thresholds if needed

## 🎛️ Advanced Usage

### Manual Override
```bash
# Force conservative mode
echo '{"gpt5_usage_multiplier": 1.0, "frozen_mode": true}' > artifacts/selflearn/routing_adjustments.json
```

### Backfill Historical Data
```bash
make selflearn-backfill
```

### Debug/Test
```bash
# Test with mock data
make selflearn-test

# Dry run daily cycle
python3 scripts/self_learn_daily.py --dry-run
```

## 📞 Support

### Health Check
```bash
# Quick system status
make selflearn-report
tail -f artifacts/selflearn/change_log.jsonl
```

### Common Issues
1. **Low quality scores** → Check `artifacts/selflearn/change_log.jsonl`
2. **Budget overrun** → Review `budget_state.json` and routing adjustments
3. **No learning** → Ensure sufficient data (>50 events)

### Troubleshooting
- All state stored in `artifacts/selflearn/`
- Complete audit trail in `change_log.jsonl`  
- Daily cycle logs via `make selflearn-daily`

---

**🎯 Result**: Intelligent, self-improving content system that maximizes quality while staying within budget, with zero ongoing maintenance required.
