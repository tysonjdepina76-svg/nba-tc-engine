#!/bin/bash
ODDS_API_KEY="${ODDS_API_KEY:-}"
if [ -z "$ODDS_API_KEY" ]; then
    echo "ODDS_API_KEY not set — cannot check quota"
    exit 1
fi
curl -s "https://api.the-odds-api.com/v4/sports/?apiKey=$ODDS_API_KEY" \
    -o /tmp/odds_usage.json
REMAINING=$(curl -s -I "https://api.the-odds-api.com/v4/sports/?apiKey=$ODDS_API_KEY" 2>/dev/null | grep -i 'x-requests-remaining' | cut -d: -f2 | tr -d ' \r')
echo "Odds API remaining: ${REMAINING:-unknown}"
