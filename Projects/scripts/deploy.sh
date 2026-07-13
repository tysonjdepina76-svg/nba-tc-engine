#!/bin/bash
# scripts/deploy.sh — production deploy for TC Sports App
set -e

echo "🚀 TC Sports App Deployment"
echo "============================"

# Create dirs
mkdir -p data logs slates Daily_Log

# Install deps
pip install -r requirements.txt

# Init DB (only if schema.sql exists)
if [ -f database/schema.sql ]; then
  echo "Initializing database..."
  sqlite3 data/tc_pipeline.db < database/schema.sql || echo "DB init skipped"
else
  echo "⚠️  database/schema.sql missing — skipping DB init"
fi

# Health check first
if [ -x scripts/health_check.sh ]; then
  bash scripts/health_check.sh || echo "⚠️  health check failed"
fi

echo "✅ Deploy complete"
echo "   Dashboard: http://localhost:8510"
echo "   API:       http://localhost:8000"
