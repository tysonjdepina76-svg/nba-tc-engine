#!/usr/bin/env python3
"""runtime_health_check.py — Validate all TC system components."""
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.utils.logging import setup_logging

logger = setup_logging("health_check")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "tc_engine")
DB_USER = os.getenv("DB_USER", "tc_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure")


def check() -> int:
    print("\n" + "=" * 50)
    print("  TC RUNTIME HEALTH CHECK")
    print("=" * 50)
    errors = 0

    # 1. core_math_engine import
    try:
        import src.core_math_engine                          # noqa: F401
        print("✅ core_math_engine")
    except Exception as e:
        print(f"❌ core_math_engine: {e}")
        errors += 1

    # 2. line_fetcher import
    try:
        import src.adapters.line_fetcher                     # noqa: F401
        print("✅ line_fetcher")
    except Exception as e:
        print(f"❌ line_fetcher: {e}")
        errors += 1

    # 3. deepseek_enhancer import
    try:
        import src.adapters.deepseek_enhancer                # noqa: F401
        print("✅ deepseek_enhancer")
    except Exception as e:
        print(f"❌ deepseek_enhancer: {e}")
        errors += 1

    # 4. Database connection
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        )
        conn.close()
        print("✅ Database connection")
    except Exception as e:
        print(f"❌ Database connection: {e}")
        errors += 1

    # 5. API endpoint
    try:
        resp = requests.get("http://localhost:8000/api/stats/dashboard", timeout=5)
        if resp.status_code == 200:
            print("✅ API endpoint reachable")
        else:
            print(f"❌ API returned {resp.status_code}")
            errors += 1
    except Exception:
        print("❌ API unreachable")
        errors += 1

    print("=" * 50)
    return errors


if __name__ == "__main__":
    sys.exit(check())
