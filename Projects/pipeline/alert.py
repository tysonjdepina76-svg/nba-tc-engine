import logging

def send_alert(message: str, severity: str = "INFO") -> None:
    logger = logging.getLogger("pipeline.alerts")
    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, message)
    try:
        import json, os
        webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        if webhook:
            import requests
            requests.post(webhook, json={"text": f"[{severity}] {message}"}, timeout=5)
    except Exception:
        pass
