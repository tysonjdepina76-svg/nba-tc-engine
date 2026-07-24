#!/bin/bash
# daily.sh — full daily run: scan + picks + combos + push
set -euo pipefail
PROJECT_ROOT="/home/workspace/Projects"
cd "$PROJECT_ROOT"
TODAY="$(date +%F)"

echo "📅 daily run for $TODAY"
python3 orchestrator.py --date "$TODAY"
python3 build_pregame_combos.py --date "$TODAY" || echo "  (combos step skipped/failed)"
echo "✅ daily run done"
