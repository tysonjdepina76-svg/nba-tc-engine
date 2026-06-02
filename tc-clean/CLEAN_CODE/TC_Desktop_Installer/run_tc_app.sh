#!/bin/bash
# TC Desktop — Triple Conservative Sports App
# Triple Conservative engine for NBA, WNBA, NCAAB, MLB, NHL
# Runs locally on Chromebook via Crostini Linux
# Opens browser to http://localhost:8501 when ready

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔════════════════════════════════════════════════════╗"
echo "║   TC Triple Conservative — Sports Betting App      ║"
echo "║   NBA · WNBA · NCAAB · MLB · NHL                   ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# 1) Check Python
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 not found. Enable Linux on your Chromebook:"
  echo "   Settings → Advanced → Developers → Linux development environment"
  exit 1
fi

# 2) Install pip + dependencies (first run only)
if ! python3 -m pip --version >/dev/null 2>&1; then
  echo "Installing pip..."
  sudo apt update -qq
  sudo apt install -y python3-pip python3-venv
fi

# 3) Use a venv so we don't fight with system Python
if [ ! -d "venv" ]; then
  echo "Setting up Python environment (one-time)..."
  python3 -m venv venv
fi
source venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4) Launch Streamlit
echo ""
echo "✅ Starting TC app at http://localhost:8501"
echo "   (Press Ctrl+C in this window to stop)"
echo ""
exec python3 -m streamlit run SportsTC_Streamlit_App.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
