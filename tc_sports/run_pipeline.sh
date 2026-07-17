#!/bin/bash
# run_pipeline.sh — Scheduled execution script for tc_sports
set -e

echo "=== TC Sports Pipeline $(date) ==="

cd /home/workspace/tc_sports
source config.env

echo "Running EV Pipeline..."
python pipeline/ev_pipeline.py

echo "Pipeline complete. Launch dashboard with:"
echo "  streamlit run /home/workspace/tc_sports/dashboard/dashboard.py --server.port 8510"
