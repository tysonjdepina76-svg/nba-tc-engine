#!/usr/bin/env python3
"""
Central configuration for the sports pipeline.
All paths and settings are defined here.
"""
import os
from pathlib import Path

# ---- Project paths ----
BASE_DIR = Path(__file__).parent
OUTPUT_FILE = str(BASE_DIR / "pipeline_output.json")
HEALTH_FILE = str(BASE_DIR / "health_status.json")
DB_PATH = str(BASE_DIR / "pipeline_history.db")
CACHE_DIR = str(BASE_DIR / "cache")
LOG_FILE = str(BASE_DIR / "alert.log")
CRON_LOG = str(BASE_DIR / "logs" / "cron.log")

# ---- Pipeline settings ----
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
SCORE_REFRESH_SECONDS = 60
ODDS_REFRESH_SECONDS = 120
CACHE_TTL_SECONDS = 300
MAX_DATA_AGE_SECONDS = 300

# ---- API keys from environment ----
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_EMAIL_RECIPIENT = os.environ.get("ALERT_EMAIL_RECIPIENT", "admin@example.com")

# ---- Create required directories ----
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
Path(CRON_LOG).parent.mkdir(parents=True, exist_ok=True)
