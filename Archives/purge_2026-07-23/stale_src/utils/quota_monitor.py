"""Monitor and manage API quota."""

import json
from pathlib import Path
from datetime import datetime


class QuotaMonitor:
    """Track and manage API quota."""

    def __init__(self, max_calls: int = 10):
        self.quota_file = Path("/home/workspace/Projects/cache/quota.json")
        self.quota_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_calls = max_calls

    def get_usage(self) -> dict:
        today = datetime.now().strftime('%Y-%m-%d')

        if not self.quota_file.exists():
            return {"date": today, "calls": 0, "remaining": self.max_calls}

        try:
            with open(self.quota_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"date": today, "calls": 0, "remaining": self.max_calls}

        if data.get('date') != today:
            return {"date": today, "calls": 0, "remaining": self.max_calls}

        calls = int(data.get('calls', 0))
        return {
            "date": today,
            "calls": calls,
            "remaining": max(0, self.max_calls - calls),
        }

    def increment(self):
        today = datetime.now().strftime('%Y-%m-%d')
        usage = self.get_usage()
        with open(self.quota_file, 'w') as f:
            json.dump({"date": today, "calls": usage['calls'] + 1}, f)

    def can_call(self) -> bool:
        return self.get_usage()['remaining'] > 0
