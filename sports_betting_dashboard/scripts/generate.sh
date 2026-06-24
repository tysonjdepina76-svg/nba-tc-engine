#!/usr/bin/env bash
# Generate today's picks
set -euo pipefail
echo "→ Generating picks for $(date +%Y-%m-%d)..."
python3 /home/workspace/Projects/daily_picks.py WNBA MLB 'WORLD CUP'
echo "✓ Done — check /home/workspace/Daily_Log/$(date +%Y-%m-%d)/picks.json"
