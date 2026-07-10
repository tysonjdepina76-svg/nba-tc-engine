"""Sports data fetchers with tiered fallback (ESPN -> SportsData.io -> cache).

Path bootstrap: any public source in this package can be imported from any
working directory. We ensure the project root is on sys.path so sibling
modules (e.g. `from sources.odds_api_client import ...`) resolve cleanly
even when the caller is sitting in /tmp or any unrelated cwd.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Make this package discoverable as `sources` from any cwd. Without this,
# running `from sources.odds_api_client import ...` from outside
# /home/workspace/Projects fails because Python only searches the cwd
# (plus installed packages) by default.
_PARENT = os.path.dirname(PROJECT_ROOT)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
