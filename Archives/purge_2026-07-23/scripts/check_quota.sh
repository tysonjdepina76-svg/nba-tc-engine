#!/usr/bin/env bash
# check_quota.sh — Check Odds API quota and pipeline health.
# Usage: bash scripts/check_quota.sh
set -euo pipefail

echo "=== Odds API Quota Check ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Health check on local services
echo "--- Local Services ---"
for url in "http://localhost:8510" "http://localhost:8510/_stcore/health"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  echo "  $url -> HTTP $code"
done

echo ""
echo "--- Quota Hints ---"
echo "  Business tier: ~50k requests/month, 500/hr"
echo "  Check usage: https://the-odds-api.com/account/"

echo ""
echo "--- Pipeline Counts ---"
python3 -c "
import csv
from pathlib import Path
total = 0
for f in Path('/home/workspace/Daily_Log').rglob('picks.csv'):
    try:
        with f.open() as fp:
            total += sum(1 for _ in fp) - 1
    except: pass
print(f'  Total picks rows: {total}')
" 2>/dev/null || echo "  (could not count)"

echo ""
echo "=== Done ==="
