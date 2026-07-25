import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

try:
    from email_config import EMAIL_CONFIG
except ImportError:
    EMAIL_CONFIG = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "tysonjdepina76@gmail.com",
        "password": "",
        "recipients": ["tysonjdepina76@gmail.com"]
    }

def send_email(subject, body, html_body=None):
    if not EMAIL_CONFIG.get("password"):
        return save_report_locally(body)

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{subject} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = EMAIL_CONFIG["recipients"][0]

        part1 = MIMEText(body, 'plain')
        msg.attach(part1)

        if html_body:
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)

        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            server.send_message(msg)

        print(f"Email sent to {EMAIL_CONFIG['recipients'][0]}")
        return True

    except Exception as e:
        print(f"Email failed: {e}")
        return save_report_locally(body)

def save_report_locally(body, filename=None):
    os.makedirs("reports", exist_ok=True)
    if not filename:
        filename = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(body)
    print(f"Report saved to {filename}")
    return False
