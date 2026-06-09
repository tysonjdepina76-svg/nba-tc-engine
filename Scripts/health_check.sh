#!/bin/bash
# health_check.sh - Pipeline health check CLI
# Usage: bash /home/workspace/Scripts/health_check.sh [--rerun]
echo "TC Pipeline Health Check"
echo "======================="
echo ""
echo "1. /api/health endpoint:"
HEALTH=$(curl -s https://true.zo.space/api/health 2>&1)
echo "$HEALTH" | python3 -m json.tool 2>/dev/null | head -20
echo ""
echo "2. Live slate (NBA + WNBA):"
NBA=$(curl -s 'https://true.zo.space/api/tc?sport=NBA&mode=live-stats' -H 'Accept: application/json')
WNBA=$(curl -s 'https://true.zo.space/api/tc?sport=WNBA&mode=live-stats' -H 'Accept: application/json')
echo "  NBA games: $(echo $NBA | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d.get("games",[])))' 2>/dev/null)"
echo "  WNBA games: $(echo $WNBA | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d.get("games",[])))' 2>/dev/null)"
echo ""
if [ "$1" = "--rerun" ]; then
  echo "3. Re-running daily_picks.py..."
  cd /home/workspace && python3 Projects/daily_picks.py NBA WNBA 2>&1 | tail -5
  echo ""
  echo "4. Re-running build_pregame_combos.py..."
  cd /home/workspace && python3 Projects/build_pregame_combos.py 2>&1 | tail -10
fi
echo "Done."
