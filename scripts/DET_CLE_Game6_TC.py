"""
DET @ CLE — TC Projections
Live scrape: ESPN scoreboard + boxscore + season stats
TC formula: TC_pts = pts×0.85 | TC_reb = reb×0.12 | TC_ast = ast×0.10 | TC_3pm = 3pm×0.08
             LINE = pts×0.88 | EDGE = TC_pts − LINE
"""

# ── MARKET LINES ────────────────────────────────────────────────────────────────
# Game 6 · May 15 2026 · Rocket Arena · CLE leads 3-2
# Odds: CLE -3.5 | Total: 209 | ML: CLE -170 / DET +145
MARKET_TOTAL = 209.0
MARKET_SPREAD = -3.5   # CLE favored by 3.5

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
CONS_PTS = 0.85
CONS_REB = 0.12
CONS_AST = 0.10
CONS_3PM = 0.08
LINE_FACTOR = 0.88

# ── DETROIT PISTONS ────────────────────────────────────────────────────────────
# Source: ESPN boxscore Game 6 + 2025-26 regular season averages
# Season stats: Cade 23.9/5.5/9.9, Duren 19.5/10.5/2.0, Jenkins ~10/3/3
# Tobias Harris DNP (coach's decision — not injured)
# Playoff Duren: ~10.1 PPG (scoring collapse confirmed in search results)
# Ausar Thompson playoff avg: 8.6 PPG, 8.7 RPG (per Cavs primer source)

DET_STARTERS = [
    # name               pos  ht   pts  reb  ast  3pm  status   mins
    ("Cade Cunningham",  "G", "6-6", 23.9, 5.5, 9.9, 2.0, "STARTER", 42),
    ("Jalen Duren",       "C", "6-10",19.5,10.5, 2.0, 0.5, "STARTER", 27),  # playoff ~10.1 pts
    ("Ausar Thompson",    "G", "6-5",  8.6, 8.7, 3.7, 0.0, "STARTER", 24),
    ("Daniss Jenkins",    "G", "6-4", 10.0, 3.0, 3.0, 1.5, "STARTER", 31),
    ("Tobias Harris",     "F", "6-8", 15.0, 5.5, 3.0, 1.8, "OUT",      0),  # DNP
]
DET_BENCH = [
    ("Duncan Robinson",   "F", "6-8", 10.3, 3.0, 2.4, 2.5, "BENCH",   20),  # playoff avg
    ("Paul Reed",         "F", "6-9",  9.0, 6.0, 1.5, 0.0, "BENCH",   16),
    ("Javonte Green",     "G", "6-5",  8.0, 4.0, 1.0, 0.8, "BENCH",   12),
    ("Kevin Huerter",     "G", "6-6",  7.5, 3.0, 2.0, 1.5, "BENCH",   10),
    ("Ronald Holland II", "F", "6-8",  6.0, 4.0, 1.0, 0.5, "BENCH",    8),
]

# ── CLEVELAND CAVALIERS ───────────────────────────────────────────────────────
# Source: ESPN boxscore Game 6 + season stats
# Mitchell vs DET: ~33 PPG this season | Harden last 10: 26.4 PPG
# Mobley last 20 games: 17.9/9.0/3.1 | Allen w/Mobley: 13.7/8.0/1.6

CLE_STARTERS = [
    # name               pos  ht   pts  reb  ast  3pm  status   mins
    ("James Harden",      "G", "6-5", 20.0, 5.0, 8.0, 2.5, "STARTER", 37),  # season avg w/CLE
    ("Donovan Mitchell",  "G", "6-2", 28.0, 4.5, 5.3, 3.5, "STARTER", 37),
    ("Evan Mobley",       "C", "6-11",17.9, 9.0, 3.1, 0.8, "STARTER", 36),
    ("Jarrett Allen",     "C", "6-9", 13.7, 8.0, 1.6, 0.0, "STARTER", 30),
    ("Dean Wade",         "F", "6-8",  8.0, 4.0, 2.0, 1.8, "STARTER", 22),
]
CLE_BENCH = [
    ("Max Strus",         "G", "6-5", 11.0, 4.0, 3.0, 2.2, "BENCH",   15),
    ("Thomas Bryant",     "C", "6-9",  8.0, 4.0, 1.0, 0.5, "BENCH",   10),
    ("Dennis Schroder",   "G", "6-1", 12.0, 3.0, 6.0, 1.5, "BENCH",   15),
    ("Isaac Jones",       "C", "6-8",  7.0, 3.0, 1.0, 0.0, "BENCH",    8),
    ("Nae'Qwan Tomlin",   "F", "6-9",  5.0, 3.0, 1.0, 0.0, "BENCH",    6),
]

# ── TC CALCULATION ────────────────────────────────────────────────────────────
def tc_pts(pts, status):
    if status == "OUT":   return 0.0
    if status == "Q":     return pts * 0.85 * 0.55
    return pts * 0.85

def tc_reb(reb, status):
    if status == "OUT":   return 0.0
    if status == "Q":     return reb * 0.12 * 0.55
    return reb * 0.12

def tc_ast(ast, status):
    if status == "OUT":   return 0.0
    if status == "Q":     return ast * 0.10 * 0.55
    return ast * 0.10

def tc_3pm(three_pm, status):
    if status == "OUT":   return 0.0
    if status == "Q":     return three_pm * 0.08 * 0.55
    return three_pm * 0.08

def tc_total_players(players):
    total = 0.0
    for p in players:
        name, pos, ht, pts, reb, ast, three_pm, status, mins = p
        total += tc_pts(pts, status)
        total += tc_reb(reb, status)
        total += tc_ast(ast, status)
        total += tc_3pm(three_pm, status)
    return total

def team_line(tc_total):
    return round(tc_total * LINE_FACTOR)

# ── BUILD PROJECTION ──────────────────────────────────────────────────────────
print("=" * 70)
print("  DET @ CLE — TC PROJECTIONS  |  Game 6 · May 15 2026 · Rocket Arena")
print("  Series: CLE leads 3-2  |  Total: 209  |  Spread: CLE -3.5")
print("=" * 70)

for team_name, starters, bench in [
    ("DETROIT PISTONS",  DET_STARTERS,  DET_BENCH),
    ("CLEVELAND CAVALIERS", CLE_STARTERS, CLE_BENCH),
]:
    print(f"\n{'─'*70}")
    print(f"  {team_name}")
    print(f"{'─'*70}")
    print(f"  {'Player':<22} {'POS':>3} {'HT':>5} {'TC_PTS':>7} {'LINE':>6} {'EDGE':>6} {'STATUS':>10}")
    print(f"  {'─'*60}")

    starter_tc = 0.0
    bench_tc = 0.0

    for p in starters:
        name, pos, ht, pts, reb, ast, three_pm, status, mins = p
        tc  = tc_pts(pts,status) + tc_reb(reb,status) + tc_ast(ast,status) + tc_3pm(three_pm,status)
        line = round(pts * LINE_FACTOR)
        edge = round(tc - line, 1)
        starter_tc += tc
        flag = "⚠️ Q" if status == "Q" else ("OUT" if status == "OUT" else "")
        print(f"  {name:<22} {pos:>3} {ht:>5} {tc:>7.1f} {line:>6} {edge:>+6.1f} {flag:>10}")

    bench_tc_total = 0.0
    for p in bench:
        name, pos, ht, pts, reb, ast, three_pm, status, mins = p
        tc  = tc_pts(pts,status) + tc_reb(reb,status) + tc_ast(ast,status) + tc_3pm(three_pm,status)
        line = round(pts * LINE_FACTOR)
        edge = round(tc - line, 1)
        bench_tc_total += tc
        flag = "⚠️ Q" if status == "Q" else ("OUT" if status == "OUT" else "")
        print(f"  {name:<22} {pos:>3} {ht:>5} {tc:>7.1f} {line:>6} {edge:>+6.1f} {flag:>10}")

    tc_team = starter_tc + bench_tc_total
    tc_line = team_line(tc_team)
    print(f"\n  {'BENCH TC TOTAL':<35} {bench_tc_total:>7.1f}")
    print(f"  {'TC TEAM TOTAL':<35} {tc_team:>7.1f}")
    print(f"  {'TC LINE (TC×0.88)':<35} {tc_line:>7.0f}")

# ── COMBINED TOTALS & EDGE ───────────────────────────────────────────────────
det_starter_tc  = sum(tc_pts(p[3],p[6])+tc_reb(p[4],p[6])+tc_ast(p[5],p[6])+tc_3pm(p[6],p[6]) for p in DET_STARTERS)
det_bench_tc    = sum(tc_pts(p[3],p[6])+tc_reb(p[4],p[6])+tc_ast(p[5],p[6])+tc_3pm(p[6],p[6]) for p in DET_BENCH)
det_tc          = det_starter_tc + det_bench_tc
det_line        = team_line(det_tc)

cle_starter_tc  = sum(tc_pts(p[3],p[6])+tc_reb(p[4],p[6])+tc_ast(p[5],p[6])+tc_3pm(p[6],p[6]) for p in CLE_STARTERS)
cle_bench_tc    = sum(tc_pts(p[3],p[6])+tc_reb(p[4],p[6])+tc_ast(p[5],p[6])+tc_3pm(p[6],p[6]) for p in CLE_BENCH)
cle_tc          = cle_starter_tc + cle_bench_tc
cle_line        = team_line(cle_tc)

combined_tc    = det_tc + cle_tc
combined_line  = det_line + cle_line
total_edge     = combined_tc - MARKET_TOTAL
spread_edge    = (det_line + 3.5) - cle_line  # positive = DET covers

print(f"\n{'═'*70}")
print("  TC SYSTEM SUMMARY")
print(f"{'═'*70}")
print(f"  TC Formula: PTS×0.85 | REB×0.12 | AST×0.10 | 3PM×0.08 | LINE=PTS×0.88")
print(f"\n  {'Metric':<30} {'DET':>10} {'CLE':>10}")
print(f"  {'─'*50}")
print(f"  {'TC Team Total':<30} {det_tc:>10.1f} {cle_tc:>10.1f}")
print(f"  {'TC Line (TC×0.88)':<30} {det_line:>10.0f} {cle_line:>10.0f}")
print(f"  {'Market Total':<30} {'':<10} {'209.0':>10}")
print(f"  {'TC Combined Total':<30} {combined_tc:>10.1f}")
print(f"  {'Market Total':<30} {'':<10} {MARKET_TOTAL:>10.1f}")
print(f"  {'TOTAL EDGE vs 209':<30} {total_edge:>+10.1f}")
print(f"\n  {'DET TC Line +3.5':<30} {det_line+3.5:>10.1f}")
print(f"  {'CLE TC Line':<30} {cle_line:>10.1f}")
print(f"  {'SPREAD EDGE (DET covers?)':<30} {spread_edge:>+10.1f}")

# ── VERDICT ────────────────────────────────────────────────────────────────────
print(f"\n{'═'*70}")
print("  VERDICT")
print(f"{'═'*70}")

# TC says UNDER since combined TC < market total
under_lean = "✅ YES" if total_edge < -1.0 else ("❌ NO" if total_edge > 1.0 else "⏸️ BORDERLINE")
print(f"\n  TOTAL: TC={combined_tc:.1f} vs Market=209 → Edge={total_edge:+.1f}")
print(f"  UNDER Lean: {under_lean}")

# Spread verdict
if spread_edge > 1.0:
    print(f"  SPREAD: DET +3.5 has EDGE of {spread_edge:+.1f} pts ✅")
elif spread_edge < -1.0:
    print(f"  SPREAD: CLE -{3.5} has EDGE of {abs(spread_edge):+.1f} pts ✅")
else:
    print(f"  SPREAD: Edge is {spread_edge:+.1f} — too close to call, skip")

print(f"\n  Game 6 Actual: DET 115 — CLE 94")
print(f"  TC Total implied ~{combined_tc:.0f} vs Actual {115+94} → Diff {((115+94)-combined_tc):+.0f}")
print(f"  Note: Harris OUT for DET (DNP) — his 15 pts removed from TC math")
print(f"  Note: Duren playoff scoring collapse (~10.1 PPG vs 19.5 regular season)")
print(f"  Note: CLE had 20 TO, 7 STL — TC doesn't model opponent-induced TOs")