#!/usr/bin/env python3
"""
Alert module - sends notifications via Slack, email, and logs to file.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import requests

from config import (
    SLACK_WEBHOOK_URL, SMTP_HOST, SMTP_PORT, SMTP_USER,
    SMTP_PASSWORD, ALERT_EMAIL_RECIPIENT, LOG_FILE
)

logger = logging.getLogger("alert")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

def send_slack(message: str) -> bool:
    if not SLACK_WEBHOOK_URL:
        return False
    try:
        payload = {"text": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"}
        r = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Slack failed: {e}")
        return False

def send_email(subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = ALERT_EMAIL_RECIPIENT
        msg["Subject"] = f"[Sports Pipeline] {subject}"
        msg.attach(MIMEText(body, "plain"))
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False

def send_alert(message: str, severity: str = "INFO") -> None:
    """Send alert to all configured channels."""
    print(f"[ALERT:{severity}] {message}")
    logger.warning(f"{severity}: {message}")
    if send_slack(message):
        logger.debug("Slack sent")
    if severity in ["CRITICAL", "WARNING"]:
        if send_email(f"{severity} Alert", message):
            logger.debug("Email sent")
