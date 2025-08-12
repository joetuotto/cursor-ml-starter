#!/usr/bin/env bash
# Slack notifications for PARANOID V5 deployments

SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
STATUS="${1:-success}"
MESSAGE="${2:-Deployment notification}"

if [[ -z "$SLACK_WEBHOOK" ]]; then
  exit 0
fi

case "$STATUS" in
  "success")
    COLOR="good"
    EMOJI="🎉"
    TITLE="Deployment Successful"
    ;;
  "failure")
    COLOR="danger" 
    EMOJI="🚨"
    TITLE="Deployment Failed"
    ;;
  "rollback")
    COLOR="warning"
    EMOJI="🔄"
    TITLE="Rollback Executed"
    ;;
  *)
    COLOR="warning"
    EMOJI="ℹ️"
    TITLE="Deployment Update"
    ;;
esac

PAYLOAD=$(cat <<EOF
{
  "attachments": [
    {
      "color": "$COLOR",
      "title": "$EMOJI PARANOID V5 - $TITLE",
      "text": "$MESSAGE",
      "fields": [
        {
          "title": "Environment",
          "value": "Production",
          "short": true
        },
        {
          "title": "Service",
          "value": "paranoid-api",
          "short": true
        }
      ],
      "footer": "PARANOID V5 Deployment Bot",
      "ts": $(date +%s)
    }
  ]
}
EOF
)

curl -X POST -H 'Content-type: application/json' \
  --data "$PAYLOAD" \
  "$SLACK_WEBHOOK" >/dev/null 2>&1 || true
