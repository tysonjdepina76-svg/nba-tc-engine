#!/bin/bash
# scripts/maintenance.sh
# Daily maintenance

echo "🔧 Daily Maintenance"
cd /home/workspace/Projects

# Clean cache
find data/cache -type f -mtime +1 -delete 2>/dev/null || true

# Rotate logs
find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true

# Run health check
python3 runtime_health_check.py

echo "✅ Maintenance complete"
