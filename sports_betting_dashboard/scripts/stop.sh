#!/usr/bin/env bash
# Stop all TC services
echo "→ Stopping services..."
pkill -f "streamlit run.*dashboard" 2>/dev/null && echo "✓ Streamlit stopped" || echo "Streamlit not running"
pkill -f "daily_picks\.py" 2>/dev/null && echo "✓ daily_picks stopped" || echo "daily_picks not running"
echo "✓ All TC services stopped"
