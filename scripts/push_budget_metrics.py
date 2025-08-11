#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def push_minimal_daily():
    prom = os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
    env = os.getenv("ALERT_ENV", "prod")
    if not prom:
        return
    body = (
        "# TYPE paranoid_budget_spent_today_eur gauge\n"
        f"paranoid_budget_spent_today_eur{{env=\"{env}\"}} 0\n"
        f"paranoid_daily_soft_cap_hit{{env=\"{env}\"}} 0\n"
        f"paranoid_daily_hard_cap_hit{{env=\"{env}\"}} 0\n"
    )
    try:
        import urllib.request

        req = urllib.request.Request(
            f"{prom}/metrics/job/paranoid_budget/env/{env}/agg/today",
            data=body.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "text/plain"},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


def main() -> int:
    # Ensure project root on path for local imports
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    try:
        from src.hybrid.budget import push_prom, push_prom_daily  # type: ignore

        try:
            push_prom()
        except Exception:
            pass
        try:
            push_prom_daily()
        except Exception:
            pass
        return 0
    except Exception:
        # Fallback minimal heartbeat so dashboards are not empty
        push_minimal_daily()
        return 0


if __name__ == "__main__":
    sys.exit(main())


