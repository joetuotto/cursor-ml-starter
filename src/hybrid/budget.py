import os, json, time
from pathlib import Path
from datetime import datetime, timedelta

BUDGET = float(os.getenv("BUDGET_MONTH_EUR", "30"))
SOFT  = float(os.getenv("BUDGET_SOFT_RATIO", "0.85"))
HARD  = float(os.getenv("BUDGET_HARD_RATIO", "1.25"))
WIN_D = int(os.getenv("BUDGET_WINDOW_DAYS", "30"))
COST_FILE = Path(os.getenv("BUDGET_COST_BUCKET", "artifacts/billing/costs.jsonl"))

# Päiväkohtainen maksimi
DAILY_MAX_EUR = float(os.getenv("BUDGET_DAILY_MAX_EUR", "5.0"))

COST_CURSOR = float(os.getenv("COST_EUR_PERK_TOK_CURSOR","0.0065"))
COST_DEEP   = float(os.getenv("COST_EUR_PERK_TOK_DEEPSEEK","0.0008"))

def _month_key(dt=None):
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m")

def _today_key(dt=None):
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m-%d")

def _read_all():
    if not COST_FILE.exists(): return []
    return [json.loads(l) for l in COST_FILE.read_text().splitlines() if l.strip()]

def _write_event(ev):
    COST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with COST_FILE.open("a") as f:
        f.write(json.dumps(ev, ensure_ascii=False)+"\n")

def estimate_cost_eur(provider:str, input_tok:int, output_tok:int)->float:
    perk = COST_CURSOR if provider.startswith("gpt5") or "cursor" in provider else COST_DEEP
    # karkea arvio: laskutetaan input+output
    return ((input_tok + output_tok)/1000.0)*perk

def stats():
    rows = _read_all()
    mk = _month_key()
    tk = _today_key()
    
    month_rows = [r for r in rows if r.get("month")==mk]
    today_rows = [r for r in rows if r.get("ts","").startswith(tk)]
    
    spent = sum(r.get("eur",0) for r in month_rows)
    daily_spent = sum(r.get("eur",0) for r in today_rows)
    
    soft = BUDGET*SOFT
    hard = BUDGET*HARD
    days_left = max(1, WIN_D - (datetime.utcnow().day-1))  # likimääräinen
    daily_allow = max(0.0, (BUDGET - spent)/days_left)
    
    return {
        "spent": spent,
        "daily_spent": daily_spent,
        "daily_max": DAILY_MAX_EUR,
        "daily_remaining": max(0.0, DAILY_MAX_EUR - daily_spent),
        "soft": soft,
        "hard": hard,
        "daily_allow": daily_allow,
        "month": mk,
        "today": tk
    }

def should_throttle()->bool:
    s = stats()
    return s["spent"]>=s["soft"] and s["spent"]<s["hard"]

def hard_cap_hit()->bool:
    s = stats()
    return s["spent"]>=s["hard"]

def should_daily_throttle()->bool:
    """Check if daily spending should be throttled (80% of daily max)"""
    s = stats()
    return s["daily_spent"] >= (s["daily_max"] * 0.8)

def daily_hard_cap_hit()->bool:
    """Check if daily hard cap is hit"""
    s = stats()
    return s["daily_spent"] >= s["daily_max"]

def record_usage(provider:str, input_tok:int, output_tok:int, eur:float=None, meta:dict=None):
    # Add today key for daily tracking
    today_key = _today_key()
    
    ev = {
        "ts": datetime.utcnow().isoformat()+"Z",
        "month": _month_key(),
        "today": today_key,
        "provider": provider,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "eur": eur if eur is not None else estimate_cost_eur(provider,input_tok,output_tok),
        "_meta": meta or {}
    }
    _write_event(ev)
    return ev

# Prometheus push (optional)
def push_prom():
    url = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
    if not url: return
    s = stats()
    payload = (
        f'paranoid_budget_spent_eur {s["spent"]}\n'
        f'paranoid_budget_soft_eur {s["soft"]}\n'
        f'paranoid_budget_hard_eur {s["hard"]}\n'
        f'paranoid_daily_spent_eur {s["daily_spent"]}\n'
        f'paranoid_daily_max_eur {s["daily_max"]}\n'
        f'paranoid_daily_remaining_eur {s["daily_remaining"]}\n'
    ).encode()
    try:
        import urllib.request
        urllib.request.urlopen(f"{url}/metrics/job/paranoid_budget", data=payload, timeout=3)
    except Exception:
        pass

def push_prom_daily():
    """Push daily-specific metrics"""
    url = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
    if not url: return
    s = stats()
    
    # Daily cap alerts
    daily_soft_hit = 1 if should_daily_throttle() else 0
    daily_hard_hit = 1 if daily_hard_cap_hit() else 0
    
    payload = (
        f'paranoid_daily_soft_cap_hit {daily_soft_hit}\n'
        f'paranoid_daily_hard_cap_hit {daily_hard_hit}\n'
        f'paranoid_daily_spend_rate {{today="{s["today"]}"}} {s["daily_spent"]}\n'
    ).encode()
    try:
        import urllib.request
        urllib.request.urlopen(f"{url}/metrics/job/paranoid_budget_daily", data=payload, timeout=3)
    except Exception:
        pass

# Slack notification (optional)
def notify_slack(msg:str):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url: return
    import json, urllib.request
    data = json.dumps({"text": msg}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    try: 
        urllib.request.urlopen(req, timeout=3)
    except Exception: 
        pass