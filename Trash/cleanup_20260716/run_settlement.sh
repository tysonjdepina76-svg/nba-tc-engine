#!/usr/bin/env bash
# Settlement runner: grade pending picks for a given date using ESPN + fallbacks.
#
# Usage:
#   ./run_settlement.sh                  # settle today
#   ./run_settlement.sh 2026-07-10       # settle specific date
#   ./run_settlement.sh 2026-07-10 --dry-run
set -euo pipefail

cd "$(dirname "$0")"

DATE="${1:-$(TZ=America/New_York date +%Y-%m-%d)}"
DRY_FLAG="${2:-}"

echo "==============================================="
echo "  TC Settlement Runner"
echo "  Date: $DATE"
echo "  Mode: ${DRY_FLAG:-LIVE}"
echo "  Time: $(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z')"
echo "==============================================="

# Step 1: Fetch results from ESPN
echo ""
echo "[1/4] Fetching ESPN results for $DATE ..."
python3 -c "
from espn_odds_fallback import get_game_results
for sport in ('MLB', 'WNBA', 'WORLD_CUP', 'NBA', 'NHL'):
    results = get_game_results(sport, '$DATE')
    completed = [r for r in results if r['completed']]
    print(f'  {sport}: {len(results)} games, {len(completed)} completed')
" || echo "  (ESPN fetch had issues, continuing)"

# Step 2: Grade picks
echo ""
echo "[2/4] Grading picks ..."
python3 grade_daily_picks.py --date "$DATE" ${DRY_FLAG}

# Step 3: Settle positions
echo ""
echo "[3/4] Settling positions ..."
python3 settle_positions.py --date "$DATE" ${DRY_FLAG}

# Step 4: Hit-rate report
echo ""
echo "[4/4] Generating hit-rate report ..."
python3 hit_rate_report.py --date "$DATE" || true

echo ""
echo "==============================================="
echo "  ✓ Settlement complete for $DATE"
echo "==============================================="
