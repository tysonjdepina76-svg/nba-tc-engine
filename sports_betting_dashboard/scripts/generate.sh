#!/usr/bin/env bash
# Generate today's picks for all active sports
set -euo pipefail
WORKSPACE="/home/workspace"
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)

echo "=== TC Picks Generator — $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

echo "→ WNBA..."
python3 "$WORKSPACE/Projects/daily_picks.py" --sport wnba --date "$TODAY"
echo "→ MLB..."
python3 "$WORKSPACE/Projects/daily_picks.py" --sport mlb --date "$TODAY"
echo "→ WC..."
python3 "$WORKSPACE/Projects/daily_picks.py" --sport wc --date "$TODAY"

PICKS_CSV="$WORKSPACE/Daily_Log/$TODAY/picks.csv"
if [ -f "$PICKS_CSV" ]; then
    echo "✓ Done — picks.csv ($(wc -l < "$PICKS_CSV") lines) at $PICKS_CSV"
else
    echo "⚠ No picks.csv found at $PICKS_CSV"
fi
