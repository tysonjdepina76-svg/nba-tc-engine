#!/usr/bin/env bash
# Daily run: WNBA + MLB + World Cup for today (offline, self-edge projections)
set -euo pipefail
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)
cd /home/workspace

echo "=== TC Daily Run — $TODAY ==="
for sport in WNBA MLB WORLD_CUP; do
    echo ""
    echo "--- $sport ---"
    python3 Projects/daily_picks.py --sport "$sport" --date "$TODAY" 2>&1 | grep -E "Done:|self-edge picks written|valid picks|games count" | head -8
done

echo ""
echo "=== Done. picks.csv at Daily_Log/$TODAY/ ==="
