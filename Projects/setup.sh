#!/usr/bin/env bash
# TC Pipeline — first-time setup (offline, no API calls)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== TC Pipeline Setup ==="

# Create required directories
mkdir -p /home/workspace/Projects/scripts
mkdir -p /home/workspace/Daily_Log
mkdir -p /home/workspace/Archives

# Create .env from .env.template if missing
if [ ! -f /home/workspace/Projects/.env ] && [ -f /home/workspace/Projects/.env.template ]; then
    cp /home/workspace/Projects/.env.template /home/workspace/Projects/.env
    echo "  Created .env from template (set API keys in Zo Settings → Advanced)"
fi

# Create .env.template if missing
if [ ! -f /home/workspace/Projects/.env.template ]; then
    cat > /home/workspace/Projects/.env.template <<'EOF'
ODDS_API_KEY=
SPORTSGAMEODDS_API_KEY=
SPORTS_DATA_API_KEY=
DK_USERNAME=
DK_PASSWORD=
EOF
    echo "  Created .env.template"
fi

# Make all shell scripts executable
chmod +x /home/workspace/Projects/scripts/*.sh 2>/dev/null || true
chmod +x /home/workspace/Projects/*.sh 2>/dev/null || true

# Clear pycache
find /home/workspace/Projects -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "  Setup complete. Add API keys in Zo Settings → Advanced before running with --live."
