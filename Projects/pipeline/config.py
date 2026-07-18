import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = str(BASE_DIR / "pipeline_output.json")
HEALTH_FILE = str(BASE_DIR / "pipeline" / "health_status.json")
DB_PATH = str(BASE_DIR / "data" / "picks.db")
CACHE_DIR = str(BASE_DIR / "cache")
LOG_FILE = str(BASE_DIR / "pipeline" / "alerts.log")
CRON_LOG = str(BASE_DIR / "pipeline" / "cron.log")
MAX_DATA_AGE_SECONDS = int(os.getenv("MAX_DATA_AGE_SECONDS", "86400"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "2.0"))
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
