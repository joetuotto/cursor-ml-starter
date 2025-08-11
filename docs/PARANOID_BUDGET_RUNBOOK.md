# PARANOID – Budget & Throttling Runbook

Owners: ML-Ops (@oncall)
Environment: prod

## 1) Symptoms
- Grafana alert “Daily spend threshold” (warning or critical)
- Slack: “Daily soft cap reached” / “Daily HARD cap reached”
- Increased throttling, GPT-5 usage drops, potential quality shifts

## 2) Quick triage (5–10 min)
```bash
# Overall status
make budget-status
# Push both daily and monthly metrics to Prometheus
make budget-prom && make budget-prom-daily
# Inspect recent cost events
tail -n 50 artifacts/billing/costs.jsonl
```

Open Grafana dashboard “Paranoid Budget & Throttling”.

## 3) If SOFT cap (warning)
Goal: keep production running cheaper, preserve quality for critical FI content.
- Ensure throttling is active (panel “Requests throttled (today)” > 0)
- Optional: reduce GPT-5 priority for non-FI/non-critical topics
- Keep `LLM_PROVIDER_MODE=hybrid`
- Ensure router keeps FI/critical on GPT-5, others to DeepSeek
- Tighten bursts by lowering `BUDGET_DAILY_BURST` (e.g., 3 → 1) if needed

## 4) If HARD cap (critical)
Goal: stop further cost immediately, keep minimum service level.
```bash
LLM_PROVIDER_MODE=deepseek_only make enrich-hybrid
```
- Confirm in Slack: “HARD cap – switched to DeepSeek only”
- If quality drop is too high on critical FI content, consider rebalancing within monthly cap later
- Temporarily schedule GPT-5 for critical batches off-peak

## 5) Root cause / optimization (30–60 min)
- Look for spikes in `costs.jsonl`: sort by topic/lang/provider
- Check “Provider split (today)” – is GPT-5 share climbing?
- Check prompt sizes and max tokens
- Consider increasing cache TTL for recurring themes (72h → 96h)

## 6) Return to normal
- At day rollover: throttle counters reset automatically
- Restore `LLM_PROVIDER_MODE=hybrid`
- Verify panel “Daily HARD cap hit?” → No

## 7) FAQ
- Why prioritize Finnish? Quality requirements and local nuance → GPT-5
- Can I bypass soft throttle? Only FI/critical content bypasses soft (within burst). Hard caps never.
- Why metric not updating? Run `make budget-prom-daily` (cron recommended every 10 min)

## 8) Useful commands
```bash
make budget-status
make budget-prom && make budget-prom-daily
make enrich-hybrid
LLM_PROVIDER_MODE=cursor_only make enrich-hybrid
LLM_PROVIDER_MODE=deepseek_only make enrich-hybrid
```

## Import instructions
1) Dashboard: import the provided JSON in Grafana (Dashboards → Import → Upload JSON).
2) Alerts: use Grafana alerting or Prometheus rules for thresholds.
3) Link this runbook in alert annotations as `runbook`.
4) Heartbeat: add cron `*/10 * * * * make budget-prom-daily`.


