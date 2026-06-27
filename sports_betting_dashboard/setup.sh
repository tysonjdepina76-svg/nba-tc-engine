#!/usr/bin/env bash
# TC Pipeline Setup — one-time install
# Usage: bash setup.sh

set -euo pipefail

echo "============================================"
echo " TC PIPELINE SETUP"
echo "============================================"

WORKSPACE="/home/workspace"
DASHBOARD_DIR="${WORKSPACE}/sports_betting_dashboard"

# 1. Ensure directory structure
echo "→ Creating directory structure..."
mkdir -p "${DASHBOARD_DIR}"/{data,logs,models,scripts}
mkdir -p "${DASHBOARD_DIR}"/data/{account,events,odds,props,picks,sports,historical,business_scan}
mkdir -p "${WORKSPACE}/Daily_Log/backtests/30day"

# 2. Check Python dependencies
echo "→ Checking Python..."
python3 --version
python3 -c "import streamlit, pandas, numpy, requests" 2>/dev/null && echo "  ✓ Core packages OK" || echo "  ⚠ Some packages missing — pip install streamlit pandas numpy requests"

# 3. Make scripts executable
echo "→ Setting permissions..."
chmod +x "${DASHBOARD_DIR}/scan.sh" 2>/dev/null || true
chmod +x "${DASHBOARD_DIR}/setup.sh" 2>/dev/null || true
chmod +x "${DASHBOARD_DIR}/fix_pipeline.py" 2>/dev/null || true
chmod +x "${DASHBOARD_DIR}/scripts/"*.sh 2>/dev/null || true

# 4. Check environment
echo "→ Checking environment..."
if [ -f "/root/.zo/secrets.env" ]; then
    echo "  ✓ Secrets file found"
else
    echo "  ⚠ No /root/.zo/secrets.env — odds APIs may fail"
fi

# 5. Initialize data files if missing
echo "→ Initializing data files..."
if [ ! -f "${DASHBOARD_DIR}/models/algorithm_weights.json" ]; then
    cat > "${DASHBOARD_DIR}/models/algorithm_weights.json" << 'EOF'
{
  "ensemble": {
    "tc_base": 0.45,
    "dk_derived": 0.25,
    "consensus": 0.20,
    "momentum": 0.10
  },
  "sport_overrides": {
    "WNBA": { "tc_base": 0.50, "dk_derived": 0.20, "consensus": 0.20, "momentum": 0.10 },
    "MLB": { "tc_base": 0.40, "dk_derived": 0.30, "consensus": 0.15, "momentum": 0.15 },
    "WORLD CUP": { "tc_base": 0.35, "dk_derived": 0.15, "consensus": 0.20, "momentum": 0.30 }
  },
  "min_confidence": 0.55,
  "updated": "2026-06-24"
}
EOF
    echo "  ✓ Created algorithm_weights.json"
fi

# 6. Verify pipeline
echo "→ Verifying pipeline..."
python3 -c "
import sys
sys.path.insert(0, '${WORKSPACE}/Projects')
try:
    from daily_picks import main
    print('  ✓ daily_picks.py importable')
except Exception as e:
    print(f'  ⚠ daily_picks.py: {e}')
try:
    from consensus_engine import main
    print('  ✓ consensus_engine.py importable')
except Exception as e:
    print(f'  ⚠ consensus_engine.py: {e}')
"

# 7. Run initial health scan
echo "→ Running health scan..."
bash "${DASHBOARD_DIR}/scan.sh" 2>/dev/null || echo "  ⚠ Scan had issues (normal on first run)"

echo ""
echo "============================================"
echo " SETUP COMPLETE"
echo "============================================"
echo ""
echo " Quick Start:"
echo "   python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'"
echo "   bash sports_betting_dashboard/scan.sh"
echo "   bash sports_betting_dashboard/scan.sh --fix"
echo ""
echo " Dashboard: http://localhost:8510"
echo " Space:     https://true.zo.space/nba-tc"
echo "============================================"
