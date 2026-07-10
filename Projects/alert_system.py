"""Email + Slack alerts for high-value MLB signals."""
import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.adapters.mlb_pipeline import MLBPipeline

logger = logging.getLogger(__name__)


class AlertSystem:
    def __init__(self, threshold: float = -22.0, picks_csv: str = "picks.csv"):
        self.threshold = threshold
        self.pipeline = MLBPipeline(picks_csv)
        self.last_alert_time = None

    def check_and_alert(self) -> int:
        bets = self.pipeline.get_best_bets(min_cross_edge=self.threshold)
        if not bets:
            logger.info("No bets above threshold %.1f", self.threshold)
            return 0
        msg = self.format_alert(bets)
        self.send_email_alert(msg)
        self.send_slack_alert(msg)
        self.last_alert_time = datetime.now()
        logger.info("Sent alerts for %d bets", len(bets))
        return len(bets)

    @staticmethod
    def format_alert(bets: list) -> str:
        lines = [
            f"🚨 STRONG MLB SIGNALS - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
            "",
        ]
        for b in bets[:5]:
            lines.append(f"⭐ {b['game']} | Cross: {b['cross_score']:.1f} | "
                         f"Pitch: {b['pitching_score']:.1f} | Bat: {b['batting_score']:.1f}")
            for leg in b.get("top_legs", [])[:3]:
                lines.append(
                    f"   • {leg['player']} {leg['stat']} {leg['direction']} "
                    f"{leg['line']} (edge {leg['edge']:+.1f})"
                )
            lines.append("")
        return "\n".join(lines)

    def send_email_alert(self, message: str) -> None:
        sender = os.environ.get("ALERT_EMAIL")
        password = os.environ.get("ALERT_EMAIL_PASSWORD")
        recipient = os.environ.get("ALERT_RECIPIENT", sender)
        if not (sender and password and recipient):
            logger.debug("email creds not set — skipping email alert")
            return
        try:
            smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", 587))
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"MLB Betting Alerts - {datetime.now():%Y-%m-%d}"
            msg.attach(MIMEText(message, "plain"))
            with smtplib.SMTP(smtp_server, smtp_port) as srv:
                srv.starttls()
                srv.login(sender, password)
                srv.send_message(msg)
            logger.info("email alert sent")
        except Exception as e:
            logger.error("email send failed: %s", e)

    def send_slack_alert(self, message: str) -> None:
        url = os.environ.get("SLACK_WEBHOOK_URL")
        if not url:
            return
        try:
            import requests
            r = requests.post(url, json={"text": message}, timeout=10)
            if r.status_code == 200:
                logger.info("slack alert sent")
            else:
                logger.error("slack error %s", r.status_code)
        except Exception as e:
            logger.error("slack send failed: %s", e)

    def close(self):
        self.pipeline.close()


if __name__ == "__main__":
    a = AlertSystem(threshold=-22.0)
    a.check_and_alert()
    a.close()
