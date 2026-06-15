#!/bin/bash
# ============================================================
# NBA TC Prop Engine v2.0 — Shell Runner
# ============================================================
# Usage: bash nba_tc_workflow.sh [GAME_ID]
# Example: bash nba_tc_workflow.sh LAL_OKC_G1
#
# Generates:
#   - Full TC projections (PTS, REB, AST, 3PT)
#   - Pick card with confidence ratings
#   - Parlay builder
#   - Diagnostic report
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$SCRIPT_DIR/nba_tc_prop_engine.py"
OUTPUT_DIR="$SCRIPT_DIR/game_files"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR"

echo "================================================"
echo "NBA TC PROP ENGINE v2.0 — RUNNER"
echo "================================================"
echo "Timestamp: $TIMESTAMP"
echo "Engine: $ENGINE"
echo "Output: $OUTPUT_DIR"
echo ""

# Step 1: Run Diagnostic
echo "[STEP 1] Running diagnostic on backtest data..."
python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from nba_tc_prop_engine import DiagnosticEngine
DiagnosticEngine.run()
"

# Step 2: Generate Round 2 Game Files
echo ""
echo "[STEP 2] Generating Round 2 projections..."

python3 -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR')

from nba_tc_prop_engine import NBATCPropApp, PlayerStats, TeamRoster

app = NBATCPropApp()

# ── Register OKC Thunder ──────────────────────────────────────
okc = TeamRoster(name='OKC Thunder', avg_pace=101.2, avg_DEF_RTG=106.4)
okc.players = [
    PlayerStats('Shai Gilgeous-Alexander','PG',30.3,5.8,7.0,1.8,38,1,'ACTIVE'),
    PlayerStats('Chet Holmgren','C',24.0,7.8,2.1,2.4,32,1,'ACTIVE'),
    PlayerStats('Ajay Mitchell','SG',22.5,4.2,4.8,2.1,34,1,'ACTIVE'),
    PlayerStats('Isaiah Hartenstein','C',17.8,9.4,3.9,0.8,28,2,'ACTIVE'),
    PlayerStats('Luguentz Dort','SF',8.4,3.2,1.8,1.6,26,2,'ACTIVE'),
    PlayerStats('Alex Caruso','PG',14.2,4.1,5.2,2.3,24,2,'ACTIVE'),
    PlayerStats('Cason Wallace','SG',10.3,2.8,2.4,1.9,20,3,'ACTIVE'),
    PlayerStats('Aaron Wiggins','SF',9.6,3.4,1.6,1.4,16,3,'ACTIVE'),
]
app.register_team(okc)

# ── Register LA Lakers (Luka OUT) ─────────────────────────────
lal = TeamRoster(name='LA Lakers', avg_pace=99.8, avg_DEF_RTG=110.2)
lal.players = [
    PlayerStats('LeBron James','SF',23.2,7.2,8.3,1.8,38,1,'ACTIVE'),
    PlayerStats('Austin Reaves','SG',15.0,4.2,5.1,2.0,34,2,'ACTIVE'),
    PlayerStats('Rui Hachimura','PF',12.6,4.8,1.2,1.2,30,2,'ACTIVE'),
    PlayerStats('Dorian Finney-Smith','SF',8.4,3.6,1.8,1.4,28,3,'ACTIVE'),
    PlayerStats('Deandre Ayton','C',16.2,11.2,1.8,0.4,32,2,'ACTIVE'),
    PlayerStats('Marcus Smart','PG',9.2,3.4,4.2,1.2,24,3,'ACTIVE'),
    PlayerStats('Gabe Vincent','PG',7.1,2.0,2.4,0.8,18,4,'ACTIVE'),
    PlayerStats('Max Christie','SG',6.2,2.1,1.4,0.8,16,4,'ACTIVE'),
]
app.register_team(lal)

# ── Build LAL vs OKC G1 (OKC home) ────────────────────────────
ctx = app.build_game('OKC Thunder', 'LA Lakers', series_game=1, a_is_home=True)

okc_mins = {
    'Shai Gilgeous-Alexander': 38,
    'Chet Holmgren': 34,
    'Ajay Mitchell': 35,
    'Isaiah Hartenstein': 29,
    'Luguentz Dort': 27,
    'Alex Caruso': 26,
    'Cason Wallace': 22,
    'Aaron Wiggins': 18,
}

lal_mins = {
    'LeBron James': 38,
    'Austin Reaves': 34,
    'Rui Hachimura': 30,
    'Dorian Finney-Smith': 28,
    'Deandre Ayton': 32,
    'Marcus Smart': 24,
}

app.run_full_report(ctx, okc_mins, lal_mins)

# Save to file
import io, sys
buffer = io.StringIO()
old_stdout = sys.stdout
sys.stdout = buffer

app.run_full_report(ctx, okc_mins, lal_mins)

sys.stdout = old_stdout
content = buffer.getvalue()

output_path = '$OUTPUT_DIR/LAL_vs_OKC_TC_Game1_generated.txt'
with open(output_path, 'w') as f:
    f.write(content)

print(f'Saved: {output_path}')
"

echo ""
echo "================================================"
echo "RUN COMPLETE"
echo "================================================"
echo ""
echo "Generated files:"
ls -lh "$OUTPUT_DIR/"
echo ""
echo "Next steps:"
echo "  1. Review pick card in generated file"
echo "  2. Check diagnostic report above for model health"
echo "  3. Update player stats after each game"
echo "  4. Re-run after each game for next-day picks"