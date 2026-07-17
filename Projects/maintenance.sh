#!/bin/bash
set -e
echo "TC Pipeline Maintenance — $(date)"
python3 /home/workspace/Projects/runtime_health_check.py
find /home/workspace/Daily_Log -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
find /home/workspace/Projects/src -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null || true
echo "Maintenance complete."
