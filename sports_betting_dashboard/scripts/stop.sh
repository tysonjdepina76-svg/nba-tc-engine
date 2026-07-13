#!/usr/bin/env bash
# Stop all TC services — Streamlit + Python processes
set -euo pipefail

echo "→ Stopping TC services..."

# Streamlit
if pkill -f "streamlit run.*dashboard" 2>/dev/null; then
    sleep 1
    echo "✓ Streamlit stopped"
else
    echo "  Streamlit not running"
fi

# Any daily_picks.py processes
if pkill -f "daily_picks\.py" 2>/dev/null; then
    sleep 1
    echo "✓ daily_picks stopped"
else
    echo "  daily_picks not running"
fi

# Any hung fix_pipeline
pkill -f "fix_pipeline\.py" 2>/dev/null || true

echo "✓ All TC services stopped"
