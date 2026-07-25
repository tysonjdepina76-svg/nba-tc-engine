import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import time
import random

class Scheduler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.last_run = {}
        self.cache = None
        self.steam = None
        self._setup_logging()

    def _setup_logging(self):
        log_dir = "logs"
        import os
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/scheduler_{datetime.now().strftime('%Y-%m-%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_daily_schedule(self):
        return {
            "morning": {"time": "09:00", "action": self.pull_morning_lines, "ttl": 1800, "priority": "MEDIUM"},
            "midday": {"time": "12:00", "action": self.pull_midday_lines, "ttl": 1800, "priority": "MEDIUM"},
            "pre_afternoon": {"time": "14:00", "action": self.pull_pre_afternoon, "ttl": 900, "priority": "HIGH"},
            "sharp_detection": {"time": "16:00", "action": self.detect_sharp_moves, "ttl": 120, "priority": "HIGH"},
            "evening": {"time": "18:00", "action": self.pull_evening_lines, "ttl": 60, "priority": "HIGH"},
            "prime_time": {"time": "20:00", "action": self.pull_prime_time, "ttl": 30, "priority": "CRITICAL"},
            "late": {"time": "22:00", "action": self.pull_late_games, "ttl": 60, "priority": "HIGH"},
        }

    def pull_morning_lines(self):
        self.logger.info("Pulling morning lines...")

    def pull_midday_lines(self):
        self.logger.info("Pulling midday lines...")

    def pull_pre_afternoon(self):
        self.logger.info("Pulling pre-afternoon lines...")

    def detect_sharp_moves(self):
        self.logger.info("Detecting sharp moves...")
        if self.steam:
            alerts = self.steam.get_steam_alerts(minutes=10)
            if alerts:
                for alert in alerts:
                    self.logger.info(f"  STEAM: {alert['game_key']} - {alert['direction']} ({alert['confidence']}%)")
            else:
                self.logger.info("  No steam detected")

    def pull_evening_lines(self):
        self.logger.info("Pulling evening lines...")

    def pull_prime_time(self):
        self.logger.info("Pulling prime time lines...")

    def pull_late_games(self):
        self.logger.info("Pulling late games...")

    def run(self):
        self.running = True
        schedule = self.get_daily_schedule()
        self.logger.info("Scheduler started")
        self.logger.info(f"{len(schedule)} scheduled actions loaded")

        while self.running:
            now = datetime.now()
            current_time = now.strftime("%H:%M")

            for action_name, action_config in schedule.items():
                if current_time == action_config["time"]:
                    self.logger.info(f"Running: {action_name}")
                    try:
                        action_config["action"]()
                        self.last_run[action_name] = now.isoformat()
                    except Exception as e:
                        self.logger.error(f"{action_name} failed: {e}")
                    time.sleep(5)

            time.sleep(10)

    def stop(self):
        self.running = False
        self.logger.info("Scheduler stopped")
