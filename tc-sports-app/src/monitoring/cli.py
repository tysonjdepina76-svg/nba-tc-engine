"""
CLI entry.
"""

import sys
import json
from pathlib import Path
from src.monitoring.health_check import HealthChecker


def main():
    checker = HealthChecker()
    results = checker.check_all()
    print(json.dumps(results, indent=2))
    status = results.get("status", "healthy")
    if status == "critical":
        sys.exit(2)
    elif status == "warning":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()