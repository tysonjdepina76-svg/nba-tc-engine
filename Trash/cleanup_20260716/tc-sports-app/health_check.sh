#!/bin/bash
# health_check.sh — Self-healing cron for TC Sports App
# Add to crontab: */5 * * * * /home/workspace/tc-sports-app/health_check.sh

set -e

BASE="/home/workspace/tc-sports-app"
LOG="${BASE}/logs/health_check.log"
API_URL="http://localhost:8000/api/stats/dashboard"
PROM_URL="http://localhost:9090/api/v1/query?query=up"

mkdir -p "$(dirname "$LOG")"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

# 1. Check FastAPI
if curl -sf --max-time 5 "$API_URL" > /dev/null 2>&1; then
    log_msg "✅ FastAPI alive"
else
    log_msg "❌ FastAPI down — restarting..."
    docker compose -f "$BASE/docker-compose.yml" restart api 2>&1 | tee -a "$LOG"
    log_msg "API restart triggered"
fi

# 2. Check Postgres
if python3 -c "
import psycopg2, os
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        dbname=os.getenv('DB_NAME', 'tc_engine'),
        user=os.getenv('DB_USER', 'tc_user'),
        password=os.getenv('DB_PASSWORD', 'secure')
    )
    conn.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
    log_msg "✅ PostgreSQL alive"
else
    log_msg "❌ PostgreSQL down — restarting..."
    docker compose -f "$BASE/docker-compose.yml" restart postgres 2>&1 | tee -a "$LOG"
fi

# 3. Check Prometheus
if curl -sf --max-time 5 "$PROM_URL" > /dev/null 2>&1; then
    log_msg "✅ Prometheus alive"
else
    log_msg "❌ Prometheus down"
    docker compose -f "$BASE/docker-compose.yml" restart prometheus 2>&1 | tee -a "$LOG"
fi

# 4. Run health check script
cd "$BASE"
python3 runtime_health_check.py >> "$LOG" 2>&1 || true

log_msg "Health check complete"
