#!/usr/bin/env bash
# Stop TC dashboard
pkill -f "streamlit run /home/workspace/sports_betting_dashboard/dashboard.py" && echo "TC dashboard stopped" || echo "TC dashboard not running"
