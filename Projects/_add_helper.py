#!/usr/bin/env python3
"""Insert normalize_source helper at line 238 in daily_picks.py"""
import re
from pathlib import Path

p = Path("/home/workspace/Projects/daily_picks.py")
src = p.read_text()

helper = '''
def normalize_source(s):
    """Collapse pipeline-specific source labels to canonical DK/SGO/MOCK/SELF_EDGE."""
    s = (s or "").lower()
    if "draftkings" in s or s == "dk" or "sdio" in s:
        return "DK"
    if "sgo" in s or "oddsapi" in s:
        return "SGO"
    if "mock" in s:
        return "MOCK"
    if "self" in s or "edge" in s:
        return "SELF_EDGE"
    return s.upper() or "UNKNOWN"


'''

marker = "def extract_picks(projection, sport, matchup):"
if marker in src and "def normalize_source" not in src:
    src = src.replace(marker, helper + marker, 1)
    p.write_text(src)
    print("Inserted normalize_source")
else:
    print("Already present or marker not found")
