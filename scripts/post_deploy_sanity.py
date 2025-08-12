#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from urllib.parse import urljoin

import requests


def get_service_url() -> str:
    url = os.getenv("SERVICE_URL", "").strip()
    if url:
        return url
    service = os.getenv("SERVICE", "").strip()
    region = os.getenv("REGION", "").strip()
    if not service:
        raise RuntimeError("SERVICE (or SERVICE_URL) env is required")
    try:
        cmd = [
            "gcloud",
            "run",
            "services",
            "describe",
            service,
            "--format=value(status.url)",
        ]
        if region:
            cmd.append(f"--region={region}")
        url = subprocess.check_output(cmd, text=True).strip()
        if not url:
            raise RuntimeError("Empty URL from gcloud")
        return url
    except Exception as exc:
        raise RuntimeError(f"Failed to derive service URL: {exc}")


def head(url: str, path: str, timeout: int = 10) -> tuple[bool, int]:
    try:
        resp = requests.head(urljoin(url + "/", path.lstrip("/")), timeout=timeout)
        return (200 <= resp.status_code < 400, resp.status_code)
    except Exception:
        return (False, 0)


def get_json(url: str, path: str, timeout: int = 10) -> tuple[bool, int, dict]:
    try:
        resp = requests.get(urljoin(url + "/", path.lstrip("/")), timeout=timeout)
        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {}
        return (200 <= resp.status_code < 400, resp.status_code, data)
    except Exception:
        return (False, 0, {})


def validate_enriched() -> bool:
    # Use existing validator if present
    script = os.path.join("scripts", "validate_enriched.py")
    target = os.path.join("artifacts", "report.enriched.json")
    if not os.path.exists(target):
        return True  # skip if not generated yet
    if os.path.exists(script):
        try:
            subprocess.check_call([sys.executable, script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
    # Fallback: basic JSON load
    try:
        json.load(open(target, "r", encoding="utf-8"))
        return True
    except Exception:
        return False


def push_metrics():
    try:
        from src.hybrid.budget import push_prom, push_prom_daily

        push_prom()
        push_prom_daily()
    except Exception:
        pass


def notify_slack(text: str):
    try:
        from src.hybrid.budget import notify_slack as _notify

        _notify(text)
    except Exception:
        pass


def main() -> int:
    ok = True
    url = get_service_url()

    root_ok, root_code = head(url, "/")
    health_ok, health_code, health_body = get_json(url, "/health")
    enriched_ok = validate_enriched()

    push_metrics()

    summary = {
        "url": url,
        "root": {"ok": root_ok, "code": root_code},
        "health": {"ok": health_ok, "code": health_code, "body": health_body},
        "enriched_schema_ok": enriched_ok,
    }

    msg = (
        f"✅ Deploy OK: root={root_ok}({root_code}), health={health_ok}({health_code}), enriched_ok={enriched_ok} — {url}"
        if (root_ok and health_ok and enriched_ok)
        else f"⚠️ Deploy checks: root={root_ok}({root_code}), health={health_ok}({health_code}), enriched_ok={enriched_ok}) — {url}"
    )
    print(json.dumps(summary, indent=2))
    notify_slack(msg)
    # Push post-deploy sanity metric to Pushgateway if configured
    try:
        pgw = os.getenv("PROMETHEUS_PUSHGATEWAY_URL", "").strip()
        if pgw:
            env = os.getenv("ALERT_ENV", "prod")
            body = f"paranoid_post_deploy_sanity_ok{{env=\"{env}\"}} {1 if (root_ok and health_ok and enriched_ok) else 0}\n"
            import urllib.request
            req = urllib.request.Request(
                f"{pgw}/metrics/job/paranoid_sanity/env/{env}",
                data=body.encode("utf-8"),
                method="POST",
                headers={"Content-Type": "text/plain"},
            )
            urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass
    return 0 if (root_ok and health_ok and enriched_ok) else 1


if __name__ == "__main__":
    sys.exit(main())


