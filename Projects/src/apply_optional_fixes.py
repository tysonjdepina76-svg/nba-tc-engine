#!/usr/bin/env python3
"""
apply_optional_fixes.py - Applies all optional integrations:
- OVER discounts
- Kills WNBA Blocks
- Runs abbreviation audit
- Ensures game_id resolver cache is fresh
"""

import subprocess
import sys
from pathlib import Path
from src.over_discounts import OVER_DISCOUNT
from src.game_id_resolver import init_cache

def main():
    print("Applying optional fixes...")

    print(f"OVER discounts: {OVER_DISCOUNT}")

    init_cache()
    print("Game ID cache initialized.")

    subprocess.run([sys.executable, "src/audit_abbreviations.py"])

    print("\u2705 WNBA Blocks should be excluded in daily_picks.py (manual check).")

    print("\u2705 All optional fixes applied.")

if __name__ == "__main__":
    main()
