import os, json, time
from pathlib import Path
from datetime import datetime, timedelta

BUDGET = float(os.getenv("BUDGET_MONTH_EUR", "30"))
SOFT  = float(os.getenv("BUDGET_SOFT_RATIO", "0.85"))
HARD  = float(os.getenv("BUDGET_HARD_RATIO", "1.25"))
WIN_D = int(os.getenv("BUDGET_WINDOW_DAYS", "30"))
COST_FILE = Path(os.getenv("BUDGET_COST_BUCKET", "artifacts/billing/costs.jsonl"))

COST_CURSOR = float(os.getenv("COST_EUR_PERK_TOK_CURSOR","0.0065"))
COST_DEEP   = float(os.getenv("COST_EUR_PERK_TOK_DEEPSEEK","0.0008"))

# Metrics/alerts config
PROM = os.getenv("PROMETHEUS_PUSHGATEWAY_URL", "")
ALERT_ENV = os.getenv("ALERT_ENV", "prod")

def _month_key(dt=None):
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m")

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
    month_rows = [r for r in rows if r.get("month")==mk]
    spent = sum(r.get("eur",0) for r in month_rows)
    soft = BUDGET*SOFT
    hard = BUDGET*HARD
    days_left = max(1, WIN_D - (datetime.utcnow().day-1))  # likimääräinen
    daily_allow = max(0.0, (BUDGET - spent)/days_left)
    return {"spent":spent,"soft":soft,"hard":hard,"daily_allow":daily_allow,"month":mk}

def should_throttle()->bool:
    s = stats()
    return s["spent"]>=s["soft"] and s["spent"]<s["hard"]

def hard_cap_hit()->bool:
    s = stats()
    return s["spent"]>=s["hard"]

def should_daily_throttle()->bool:
    """Check if daily spending should be throttled"""
    s = stats()
    daily_spent = s["spent"] / max(1, datetime.utcnow().day)  # rough daily average
    daily_soft_limit = s["soft"] / WIN_D  # daily portion of soft limit
    return daily_spent >= daily_soft_limit * 0.8  # throttle at 80% of daily soft limit

def daily_hard_cap_hit()->bool:
    """Check if daily hard cap is hit"""
    s = stats()
    daily_spent = s["spent"] / max(1, datetime.utcnow().day)  # rough daily average
    daily_hard_limit = s["hard"] / WIN_D  # daily portion of hard limit
    return daily_spent >= daily_hard_limit

def record_usage(provider:str, input_tok:int=None, output_tok:int=None, eur:float=None, meta:dict=None, **kwargs):
    # allow alias kwargs for convenience (tokens_in/out, labels)
    if input_tok is None:
        input_tok = int(kwargs.get("tokens_in") or kwargs.get("input_tokens") or 0)
    if output_tok is None:
        output_tok = int(kwargs.get("tokens_out") or kwargs.get("output_tokens") or 0)
    if meta is None and "labels" in kwargs:
        meta = kwargs.get("labels")
    ev = {
        "ts": datetime.utcnow().isoformat()+"Z",
        "month": _month_key(),
        "provider": provider,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "eur": eur if eur is not None else estimate_cost_eur(provider,input_tok,output_tok),
        "_meta": meta or {}
    }
    _write_event(ev)
    # best-effort metric push
    try:
        push_prom()
        push_prom_daily()
    except Exception:
        pass
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
        f'paranoid_budget_spent_month_eur{{env="{ALERT_ENV}"}} {s["spent"]}\n'
    ).encode()
    try:
        import urllib.request
        urllib.request.urlopen(f"{url}/metrics/job/paranoid_budget", data=payload, timeout=3)
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


def _today_key():
    return datetime.utcnow().strftime("%Y-%m-%d")


def _read_all_rows():
    return _read_all()


def today_spent_eur() -> float:
    rows = _read_all_rows()
    today = _today_key()
    try:
        return float(sum(r.get("eur", 0.0) for r in rows if str(r.get("ts", "")).startswith(today)))
    except Exception:
        return 0.0


def _daily_caps():
    try:
        daily_soft_ratio = float(os.getenv("BUDGET_DAILY_RATIO", "0.05"))
        daily_hard_ratio = float(os.getenv("BUDGET_DAILY_HARD_RATIO", "0.08"))
    except Exception:
        daily_soft_ratio = 0.05
        daily_hard_ratio = 0.08
    return {
        "soft": BUDGET * daily_soft_ratio,
        "hard": BUDGET * daily_hard_ratio,
    }


def push_prom_daily():
    if not PROM:
        return
    spent = today_spent_eur()
    caps = _daily_caps()
    body = (
        "# TYPE paranoid_budget_spent_today_eur gauge\n"
        f"paranoid_budget_spent_today_eur{{env=\"{ALERT_ENV}\"}} {spent:.6f}\n"
        f"paranoid_daily_soft_cap_hit{{env=\"{ALERT_ENV}\"}} {1 if spent >= caps['soft'] else 0}\n"
        f"paranoid_daily_hard_cap_hit{{env=\"{ALERT_ENV}\"}} {1 if spent >= caps['hard'] else 0}\n"
    )
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{PROM}/metrics/job/paranoid_budget/env/{ALERT_ENV}/agg/today",
            data=body.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "text/plain"},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass