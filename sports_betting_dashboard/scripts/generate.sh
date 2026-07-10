#!/usr/bin/env bash
# Generate today's picks
set -euo pipefail
echo "→ Generating WNBA picks..."
python3 /home/workspace/Projects/daily_picks.py --sport WNBA
echo "→ Generating MLB picks..."
python3 /home/workspace/Projects/daily_picks.py --sport MLB
echo "→ Generating World Cup picks..."
python3 /home/workspace/Projects/daily_picks.py --sport WORLD_CUP
echo "✓ Done — check /home/workspace/Daily_Log/$(date +%Y-%m-%d)/picks.json"
