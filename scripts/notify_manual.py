import argparse
import json
import os
import re
from pathlib import Path
from typing import Tuple

import requests


def build_summary(paths: Tuple[Path, Path]) -> Tuple[str, str]:
    doc_path, _schema_path = paths
    summary, lede = "Newswire", "—"
    if doc_path.exists():
        doc = json.loads(doc_path.read_text())
        if isinstance(doc, list):
            doc = doc[0] if doc else {}
        summary = (doc.get("kicker") or doc.get("category") or summary)[:80]
        lede_txt = doc.get("lede") or doc.get("summary") or ""
        lede = " ".join(str(lede_txt).split())[:240] or lede
    return summary, lede


def escape_markdown_v2(text: str) -> str:
    return re.sub(r"([_*[\]()~`>#+\-=|{}.!])", r"\\\\\\1", text)


def notify_slack(webhook_url: str, title: str, summary: str, lede: str, run_url: str, dry_run: bool) -> None:
    payload = {
        "text": f"{title}\n*{summary}* — {lede}\nRun: {run_url}\nArtifact: report.enriched.json",
    }
    if dry_run:
        print("[dry-run] Slack payload:")
        print(json.dumps(payload))
        return
    requests.post(webhook_url, json=payload, timeout=20)


def notify_telegram(token: str, chat_id: str, title: str, summary: str, lede: str, run_url: str, dry_run: bool) -> None:
    s = escape_markdown_v2(summary)
    l = escape_markdown_v2(lede)
    text = f"{title}\n*{s}* — {l}\nRun: {run_url}\nArtifact: report.enriched.json"
    if dry_run:
        print("[dry-run] Telegram text:")
        print(text)
        return
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        },
        timeout=20,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()

    doc_path = Path("artifacts/report.enriched.json")
    schema_path = Path("artifacts/feed_item_schema.json")
    summary, lede = build_summary((doc_path, schema_path))

    dry_run = bool(os.environ.get("NOTIFY_DRY_RUN"))

    slack_url = os.environ.get("SLACK_WEBHOOK_URL")
    if slack_url:
        notify_slack(slack_url, "✅ Enrich smoke (manual)", summary, lede, args.run_url, dry_run)

    tg_token = os.environ.get("TG_BOT_TOKEN")
    tg_chat = os.environ.get("TG_CHAT_ID")
    if tg_token and tg_chat:
        notify_telegram(tg_token, tg_chat, "✅ Enrich smoke (manual)", summary, lede, args.run_url, dry_run)

    print("Notified (if channels configured).")


if __name__ == "__main__":
    main()


