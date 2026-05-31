"""
NBA/WNBA TC — Halftime & Final Box Score Backtest Engine
=========================================================
Properly handles:
  - HALFTIME games → scale TC by 0.5
  - FINAL games → full TC
  - Market total edge signal
  - Per-game + aggregate hit rate

TC Formula:
  ACTIVE  = stat × CONS (PTS=0.85, REB=0.80, AST=0.75, 3PM=0.70)
  Q       = stat × CONS × 0.55
  OUT/DNP = 0
  Line    = TC × 0.88 (floor)
  Edge    = TC − Line

Halftime rule: TC_combined_halftime = raw_TC × 0.5
Full-game rule: use raw TC
"""

import math, datetime

CONS = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70, "stl": 0.80, "blk": 0.80}
LINE_FAC = 0.88
Q_FAC = 0.55

def status_factor(s):
    u = str(s).upper()
    if "OUT" in u or "DNP" in u: return 0.0
    if any(x in u for x in ["Q","QUESTION","DOUBTFUL","GTD"]): return Q_FAC
    return 1.0

def tc_val(stat, raw, status="ACTIVE"):
    factor = CONS.get(stat, 0.85) * status_factor(status)
    return round(float(raw or 0) * factor, 2)

def tc_line(val):
    return math.floor(float(val or 0) * LINE_FAC)

def team_tc(players, half=1.0):
    """half=0.5 for halftime games, 1.0 for full games"""
    active = [p for p in players if status_factor(p.get("status","ACTIVE")) > 0]
    totals = {}
    for stat in ["pts","reb","ast","tpm"]:
        totals[f"tc_{stat}"] = round(sum(tc_val(stat, p.get(stat,0), p.get("status","ACTIVE")) for p in active) * half, 2)
    return totals

def grade(away_players, home_players, actual_away, actual_home,
         market=None, half=1.0, label=""):
    at = team_tc(away_players, half)
    ht = team_tc(home_players, half)
    tc_combined = round(at["tc_pts"] + ht["tc_pts"], 2)
    tc_line_val = tc_line(tc_combined)
    actual_total = int(actual_away or 0) + int(actual_home or 0)
    edge = round(tc_line_val - (float(market) if market else tc_line_val), 2)
    signal = "OVER" if edge > 3 else "UNDER" if edge < -3 else "PASS"
    result = "OVER" if actual_total > tc_line_val else "UNDER" if actual_total < tc_line_val else "PUSH"
    hit = signal != "PASS" and result == signal
    return {
        "label": label,
        "tc_combined": tc_combined,
        "tc_line": tc_line_val,
        "market": market,
        "edge": edge,
        "signal": signal,
        "actual_away": actual_away,
        "actual_home": actual_home,
        "actual_total": actual_total,
        "result": result,
        "hit": "✅" if hit else "❌",
        "diff": round(actual_total - tc_combined, 2),
        "halftime": half < 1.0,
    }

# ─────────────────────────────────────────────────────────────────────
# WNBA BACKTEST CASES
# ─────────────────────────────────────────────────────────────────────

# CASE 1: CON @ SEA — Halftime (May 23, 2026)
# Source: CON_SEA_401856929_halftime_boxscore.md
# Result: CON 28 — SEA 37 | Market total: 159.5
# TC applied at ×0.5 (halftime)
con_players = [
    {"name":"Aaliyah Edwards","pos":"F","pts":4,"reb":5,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Diamond Miller","pos":"F","pts":7,"reb":3,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Kennedy Burke","pos":"G","pts":7,"reb":3,"ast":0,"tpm":1,"status":"ACTIVE"},
    {"name":"Charlisse Leger-Walker","pos":"G","pts":0,"reb":1,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Gianna Kneepkens","pos":"G","pts":4,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Aneesah Morrow","pos":"F","pts":0,"reb":5,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Raegan Beers","pos":"F","pts":2,"reb":1,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Nell Angloma","pos":"F","pts":2,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Hailey Van Lith","pos":"G","pts":2,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Saniya Rivers","pos":"G","pts":0,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Ashlon Jackson","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Brittney Griner","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Olivia Nelson-Ododa","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]
sea_players = [
    {"name":"Jordan Horston","pos":"F","pts":6,"reb":2,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Stefanie Dolson","pos":"C","pts":0,"reb":1,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Natisha Hiedeman","pos":"G","pts":2,"reb":1,"ast":3,"tpm":0,"status":"ACTIVE"},
    {"name":"Flau'jae Johnson","pos":"G","pts":5,"reb":3,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Jade Melbourne","pos":"G","pts":4,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Joyner Holmes","pos":"F","pts":2,"reb":3,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Mackenzie Holmes","pos":"F","pts":2,"reb":5,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Taylor Thierry","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Lexie Brown","pos":"G","pts":0,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Zia Cooke","pos":"G","pts":16,"reb":3,"ast":0,"tpm":2,"status":"ACTIVE"},
    {"name":"Katie Lou Samuelson","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Ezi Magbegor","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Dominique Malonga","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Awa Fam","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]

# CASE 2: MIN @ CHI — Final (May 23, 2026)
# Source: MIN_CHI_WNBA_Final_Boxscore_20260523.md
# Result: MIN 85 — CHI 75 | Market total: 163.5
min_players = [
    {"name":"Kayla McBride","pos":"G","pts":13,"reb":6,"ast":4,"tpm":2,"status":"ACTIVE"},
    {"name":"Natasha Howard","pos":"F","pts":26,"reb":14,"ast":5,"tpm":0,"status":"ACTIVE"},
    {"name":"Aliyah Boston","pos":"C","pts":15,"reb":7,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Jacy Sheldon","pos":"G","pts":5,"reb":1,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Napheesa Collier","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Anastasiia Olairi Kosu","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Courtney Vandersloot","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]
chi_players = [
    {"name":"Skylar Diggins","pos":"G","pts":16,"reb":3,"ast":7,"tpm":1,"status":"ACTIVE"},
    {"name":"Rickea Jackson","pos":"F","pts":13,"reb":3,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Gabriela Jaquez","pos":"G","pts":10,"reb":4,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Kamilla Cardoso","pos":"C","pts":11,"reb":5,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Azura Stevens","pos":"F","pts":8,"reb":3,"ast":0,"tpm":0,"status":"ACTIVE"},
]

# CASE 3: NY @ CLE — NBA Halftime (May 24, 2026)
# Source: NBA_NY_CLE_halftime_20260524_013017.csv
# Result: NY 50 — CLE 44 (halftime) | Market total: 218.5
ny_players = [
    {"name":"OG Anunoby","pos":"F","pts":13,"reb":3,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Karl-Anthony Towns","pos":"F","pts":11,"reb":4,"ast":3,"tpm":1,"status":"ACTIVE"},
    {"name":"Josh Hart","pos":"G","pts":9,"reb":3,"ast":3,"tpm":1,"status":"ACTIVE"},
    {"name":"Mikal Bridges","pos":"G","pts":10,"reb":3,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Jalen Brunson","pos":"G","pts":9,"reb":2,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Mitchell Robinson","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Jordan Clarkson","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Landry Shamet","pos":"G","pts":3,"reb":1,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Jose Alvarado","pos":"G","pts":2,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Miles McBride","pos":"G","pts":3,"reb":0,"ast":0,"tpm":1,"status":"ACTIVE"},
]
cle_players = [
    {"name":"Dean Wade","pos":"F","pts":0,"reb":0,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Jarrett Allen","pos":"C","pts":12,"reb":4,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Evan Mobley","pos":"F","pts":7,"reb":3,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"James Harden","pos":"G","pts":14,"reb":4,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Donovan Mitchell","pos":"G","pts":12,"reb":0,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Dennis Schroder","pos":"G","pts":3,"reb":0,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Max Strus","pos":"G","pts":3,"reb":3,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Sam Merrill","pos":"G","pts":0,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Jaylon Tyson","pos":"G","pts":3,"reb":3,"ast":1,"tpm":0,"status":"ACTIVE"},
]

# CASE 4: SA @ OKC — NBA Halftime (May 24, 2026)
# From live_sports_scrape halftime files — Spurs up big
# TC Combined was 96.5 extrapolated to ~193 (market 218.5 → UNDER signal)
# With actual halftime score SA 58 @ OKC 54
sa_players_halftime = [
    {"name":"Victor Wembanyama","pos":"F","pts":18,"reb":6,"ast":2,"tpm":2,"status":"ACTIVE"},
    {"name":"De'Aaron Fox","pos":"G","pts":14,"reb":2,"ast":4,"tpm":0,"status":"ACTIVE"},
    {"name":"Stephon Castle","pos":"G","pts":8,"reb":2,"ast":3,"tpm":0,"status":"ACTIVE"},
    {"name":"Harrison Barnes","pos":"F","pts":6,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Devin Vassell","pos":"G","pts":5,"reb":1,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Keldon Johnson","pos":"F","pts":4,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Mason Plumlee","pos":"C","pts":3,"reb":4,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Julian Champagnie","pos":"F","pts":0,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
]
okc_players_halftime = [
    {"name":"Shai Gilgeous-Alexander","pos":"G","pts":16,"reb":3,"ast":4,"tpm":0,"status":"ACTIVE"},
    {"name":"Jalen Williams","pos":"G","pts":12,"reb":2,"ast":3,"tpm":0,"status":"ACTIVE"},
    {"name":"Chet Holmgren","pos":"C","pts":8,"reb":5,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Isaiah Hartenstein","pos":"C","pts":6,"reb":4,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Luguentz Dort","pos":"G","pts":5,"reb":2,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Alex Caruso","pos":"G","pts":4,"reb":1,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Cason Wallace","pos":"G","pts":3,"reb":1,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Aaron Wiggins","pos":"G","pts":0,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
]

# ─────────────────────────────────────────────────────────────────────
# RUN BACKTEST
# ─────────────────────────────────────────────────────────────────────
games = [
    grade(con_players, sea_players, 28, 37, market=159.5, half=0.5,
          label="WNBA: CON@SEA Halftime — May 23, 2026"),
    grade(min_players, chi_players, 85, 75, market=163.5, half=1.0,
          label="WNBA: MIN@CHI Final — May 23, 2026"),
    grade(ny_players, cle_players, 50, 44, market=218.5, half=0.5,
          label="NBA: NY@CLE Halftime — May 24, 2026"),
    grade(sa_players_halftime, okc_players_halftime, 58, 54, market=218.5, half=0.5,
          label="NBA: SA@OKC Halftime — May 24, 2026"),
]

print("=" * 70)
print(f"  NBA/WNBA TC BACKTEST REPORT")
print(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  TC Formula: stat × [0.85|0.80|0.75|0.70] × status_fact | Line = TC×0.88")
print(f"  Halftime scale: TC_combined × 0.5")
print("=" * 70)

for g in games:
    period = "HALFTIME" if g["halftime"] else "FINAL"
    print(f"\n{'─'*65}")
    print(f"  📊 {g['label']}")
    print(f"  Period: {period}")
    print(f"  Actual Score: {g['actual_away']} — {g['actual_home']} | Total={g['actual_total']}")
    print(f"  Market Total: {g['market']} | TC Combined: {g['tc_combined']} | TC Line: {g['tc_line']}")
    print(f"  Edge: {g['edge']:+.2f} | Signal: {g['signal']}")
    print(f"  Result: {g['result']} | {g['hit']} | Diff: {g['diff']:+.2f}")

hits = sum(1 for g in games if g["hit"] == "✅")
print(f"\n{'='*70}")
print(f"  SUMMARY: {hits}/{len(games)} games hit — {round(hits/len(games)*100,1)}% hit rate")
print(f"  Pass signals: {sum(1 for g in games if g['signal']=='PASS')}/{len(games)}")
print(f"  Halftime games: {sum(1 for g in games if g['halftime'])}")
print(f"  Full games: {sum(1 for g in games if not g['halftime'])}")
print("=" * 70)

# Per-stat breakdown for final box score games
print("\n  DETAIL: Player Prop TC vs Actual (Full Games)")
print(f"  {'Player':<22} {'Stat':<5} {'TC':>6} {'Target':>7} {'Actual':>7} {'Result':<6}")
print(f"  {'─'*60}")
full_games = [g for g in games if not g["halftime"]]
for g in full_games:
    print(f"\n  {g['label']}")
    # Prop picks from active players
    all_players = (con_players if "CON@SEA" in g["label"] else
                   min_players if "MIN@CHI" in g["label"] else [])
    for p in all_players:
        if status_factor(p.get("status","ACTIVE")) == 0: continue
        for stat, key in [("PTS","pts"),("REB","reb"),("AST","ast"),("3PM","tpm")]:
            tc_p = tc_val(key, p.get(key,0), p.get("status","ACTIVE"))
            line_p = tc_line(tc_p)
            actual_raw = p.get(key,0)
            actual_val = actual_raw  # already actual in backtest
            res = "✅" if (actual_val > line_p and tc_p > line_p) or (actual_val < line_p and tc_p < line_p) else "❌"
            print(f"    {p['name']:<20} {stat:<5} {tc_p:>6.1f} {line_p:>7} {actual_val:>7.1f} {res}")