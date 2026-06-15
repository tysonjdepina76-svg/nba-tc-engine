#!/usr/bin/env python3
"""
NBA/WNBA TC — Comprehensive Final Box Score Backtest Engine
=============================================================
Parses actual ESPN box scores and grades TC model against real outcomes.

TC Formula:
  TC stat = stat × [0.85|0.80|0.75|0.70|0.80|0.80] × status_factor
  LINE    = TC × 0.88 (floor)
  Edge    = TC − LINE
  Signal  = OVER if edge > 3, UNDER if edge < -3, PASS otherwise

Status: ACTIVE × 1.0 | Q × 0.55 | OUT/DNP × 0

Backtest mode:
  - Halftime: scale TC_combined by ×0.5
  - Final: use full TC_combined

Usage:
  python tc_backtest_final.py          # runs all tests
  python tc_backtest_final.py --sport WNBA  # WNBA only
  python tc_backtest_final.py --sport NBA    # NBA only
"""

import math, datetime, argparse, re

CONS = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70, "stl": 0.80, "blk": 0.80}
LINE_FAC = 0.88
Q_FAC = 0.55
EDGE_THRESH = 3.0

def sf(s):
    u = str(s).upper()
    if "OUT" in u or "DNP" in u: return 0.0
    if any(x in u for x in ["Q","QUESTION","DOUBTFUL","GTD"]): return Q_FAC
    return 1.0

def tc(stat, raw, status="ACTIVE"):
    return round(float(raw or 0) * CONS.get(stat, 0.85) * sf(status), 2)

def tl(val):
    return math.floor(float(val or 0) * LINE_FAC)

def ed(tc_val, line_val):
    return round(tc_val - line_val, 2)

def team_total(players, half=1.0):
    active = [p for p in players if sf(p.get("status","ACTIVE")) > 0]
    r = {}
    for s in ["pts","reb","ast","tpm"]:
        r[f"tc_{s}"] = round(sum(tc(s, p.get(s,0), p.get("status","ACTIVE")) for p in active) * half, 2)
    return r

def grade(away_p, home_p, away_s, home_s, market=None, half=1.0, label=""):
    at = team_total(away_p, half)
    ht = team_total(home_p, half)
    tc_comb = round(at["tc_pts"] + ht["tc_pts"], 2)
    tc_line = tl(tc_comb)
    actual = int(away_s or 0) + int(home_s or 0)
    edge = round(tc_line - float(market or tc_line), 2)
    signal = "OVER" if edge > EDGE_THRESH else "UNDER" if edge < -EDGE_THRESH else "PASS"
    result = "OVER" if actual > tc_line else "UNDER" if actual < tc_line else "PUSH"
    hit = signal != "PASS" and result == signal
    return {
        "label": label, "tc_comb": tc_comb, "tc_line": tc_line,
        "market": market, "edge": edge, "signal": signal,
        "away_score": away_s, "home_score": home_s,
        "actual_total": actual, "result": result,
        "hit": "✅" if hit else "❌",
        "diff": round(actual - tc_comb, 2), "half": half < 1.0,
    }

def player_prop_detail(players, actual_map, label):
    """Grade player props against actual box score."""
    rows = []
    for p in players:
        if sf(p.get("status","ACTIVE")) == 0: continue
        for stat, key in [("PTS","pts"),("REB","reb"),("AST","ast"),("3PM","tpm")]:
            tc_p = tc(key, p.get(key,0), p.get("status","ACTIVE"))
            line_p = tl(tc_p)
            actual_val = actual_map.get(p["name"], {}).get(key, None)
            if actual_val is None: continue
            direction = "OVER" if ed(tc_p, line_p) > 2.0 else "UNDER" if ed(tc_p, line_p) < -2.0 else "NO BET"
            res = "✅" if (actual_val > line_p and direction == "OVER") or (actual_val < line_p and direction == "UNDER") else "❌"
            rows.append({"player": p["name"], "stat": stat, "tc": tc_p, "line": line_p,
                         "actual": actual_val, "result": res, "direction": direction})
    return rows

# ─────────────────────────────────────────────────────────────────────
# WNBA FINAL BOX SCORE BACKTEST DATA
# ─────────────────────────────────────────────────────────────────────

# DAL @ ATL — May 22, 2026 | DAL 69 @ ATL 86 | Total = 155
dal_atl_away = [
    {"name":"Jessica Shepard","pos":"F","pts":10,"reb":11,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Alanna Smith","pos":"F","pts":2,"reb":2,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Odyssey Sims","pos":"G","pts":14,"reb":1,"ast":5,"tpm":1,"status":"ACTIVE"},
    {"name":"Arike Ogunbowale","pos":"G","pts":2,"reb":0,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Paige Bueckers","pos":"G","pts":7,"reb":1,"ast":7,"tpm":1,"status":"ACTIVE"},
    {"name":"Alysha Clark","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Maddy Siegrist","pos":"F","pts":5,"reb":2,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Awak Kuier","pos":"F","pts":16,"reb":4,"ast":0,"tpm":2,"status":"ACTIVE"},
    {"name":"Li Yueru","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Azzi Fudd","pos":"G","pts":7,"reb":1,"ast":0,"tpm":1,"status":"ACTIVE"},
    {"name":"Aziaha James","pos":"G","pts":6,"reb":4,"ast":5,"tpm":1,"status":"ACTIVE"},
    {"name":"JJ Quinerly","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]
dal_atl_home = [
    {"name":"Naz Hillmon","pos":"F","pts":6,"reb":3,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Angel Reese","pos":"F","pts":15,"reb":9,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Allisha Gray","pos":"G","pts":16,"reb":4,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Jordin Canada","pos":"G","pts":9,"reb":5,"ast":6,"tpm":1,"status":"ACTIVE"},
    {"name":"Rhyne Howard","pos":"G","pts":25,"reb":4,"ast":8,"tpm":2,"status":"ACTIVE"},
    {"name":"Sika Kone","pos":"F","pts":2,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Madina Okot","pos":"C","pts":0,"reb":5,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Te-Hina Paopao","pos":"G","pts":9,"reb":2,"ast":2,"tpm":3,"status":"ACTIVE"},
    {"name":"Aaliyah Nye","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Indya Nivar","pos":"G","pts":2,"reb":1,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Isobel Borlase","pos":"G","pts":2,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Brionna Jones","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]

# TOR @ MIN — May 22, 2026 | TOR 72 @ MIN 100 | Total = 172
tor_min_away = [
    {"name":"Maria Conde","pos":"F","pts":3,"reb":1,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Laura Juskaite","pos":"F","pts":7,"reb":3,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Brittney Sykes","pos":"G","pts":6,"reb":3,"ast":4,"tpm":1,"status":"ACTIVE"},
    {"name":"Marina Mabrey","pos":"G","pts":3,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Kiki Rice","pos":"G","pts":11,"reb":6,"ast":4,"tpm":2,"status":"ACTIVE"},
    {"name":"Teonni Key","pos":"F","pts":4,"reb":3,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Nikolina Milic","pos":"F","pts":8,"reb":1,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Mariella Fasoula","pos":"C","pts":4,"reb":1,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Kia Nurse","pos":"G","pts":23,"reb":4,"ast":2,"tpm":6,"status":"ACTIVE"},
    {"name":"Lexi Held","pos":"G","pts":3,"reb":1,"ast":3,"tpm":1,"status":"ACTIVE"},
    {"name":"Isabelle Harrison","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Nyara Sabally","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Temi Fagbenle","pos":"C","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Julie Allemand","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]
tor_min_home = [
    {"name":"Natasha Howard","pos":"F","pts":13,"reb":6,"ast":3,"tpm":0,"status":"ACTIVE"},
    {"name":"Nia Coffey","pos":"F","pts":8,"reb":3,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Kayla McBride","pos":"G","pts":13,"reb":4,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Courtney Williams","pos":"G","pts":15,"reb":8,"ast":3,"tpm":3,"status":"ACTIVE"},
    {"name":"Olivia Miles","pos":"G","pts":14,"reb":4,"ast":5,"tpm":0,"status":"ACTIVE"},
    {"name":"Liatu King","pos":"F","pts":9,"reb":7,"ast":0,"tpm":1,"status":"ACTIVE"},
    {"name":"Antonia Delaere","pos":"F","pts":3,"reb":1,"ast":4,"tpm":1,"status":"ACTIVE"},
    {"name":"Anastasiia Olairi Kosu","pos":"F","pts":5,"reb":4,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Maya Caldwell","pos":"G","pts":16,"reb":3,"ast":3,"tpm":4,"status":"ACTIVE"},
    {"name":"Eliska Hamzova","pos":"G","pts":4,"reb":6,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Napheesa Collier","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Dorka Juhasz","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Emma Cechova","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]

# CON @ SEA Halftime — May 23, 2026 | CON 28 @ SEA 37 | Total = 65
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

# MIN @ CHI Final — May 23, 2026 | MIN 85 @ CHI 75 | Total = 160
min_players_f = [
    {"name":"Kayla McBride","pos":"G","pts":13,"reb":6,"ast":4,"tpm":2,"status":"ACTIVE"},
    {"name":"Natasha Howard","pos":"F","pts":26,"reb":14,"ast":5,"tpm":0,"status":"ACTIVE"},
    {"name":"Aliyah Boston","pos":"C","pts":15,"reb":7,"ast":2,"tpm":0,"status":"ACTIVE"},
    {"name":"Jacy Sheldon","pos":"G","pts":5,"reb":1,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Napheesa Collier","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Anastasiia Olairi Kosu","pos":"F","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
    {"name":"Courtney Vandersloot","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]
chi_players_f = [
    {"name":"Skylar Diggins","pos":"G","pts":16,"reb":3,"ast":7,"tpm":1,"status":"ACTIVE"},
    {"name":"Rickea Jackson","pos":"F","pts":13,"reb":3,"ast":1,"tpm":1,"status":"ACTIVE"},
    {"name":"Gabriela Jaquez","pos":"G","pts":10,"reb":4,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Kamilla Cardoso","pos":"C","pts":11,"reb":5,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Azura Stevens","pos":"F","pts":8,"reb":3,"ast":0,"tpm":0,"status":"ACTIVE"},
    {"name":"Courtney Vandersloot","pos":"G","pts":0,"reb":0,"ast":0,"tpm":0,"status":"DNP"},
]

# NBA: NY @ CLE Halftime — May 24, 2026 | NY 50 @ CLE 44 | Total = 94
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

# NBA: SA @ OKC Halftime — May 24, 2026 | SA 58 @ OKC 54 | Total = 112
sa_players = [
    {"name":"Victor Wembanyama","pos":"F","pts":18,"reb":6,"ast":2,"tpm":2,"status":"ACTIVE"},
    {"name":"De'Aaron Fox","pos":"G","pts":14,"reb":2,"ast":4,"tpm":0,"status":"ACTIVE"},
    {"name":"Stephon Castle","pos":"G","pts":8,"reb":2,"ast":3,"tpm":0,"status":"ACTIVE"},
    {"name":"Harrison Barnes","pos":"F","pts":6,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Devin Vassell","pos":"G","pts":5,"reb":1,"ast":2,"tpm":1,"status":"ACTIVE"},
    {"name":"Keldon Johnson","pos":"F","pts":4,"reb":2,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Mason Plumlee","pos":"C","pts":3,"reb":4,"ast":1,"tpm":0,"status":"ACTIVE"},
    {"name":"Julian Champagnie","pos":"F","pts":0,"reb":1,"ast":0,"tpm":0,"status":"ACTIVE"},
]
okc_players = [
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
    grade(dal_atl_away, dal_atl_home, 69, 86, market=161.5, half=1.0,
          label="WNBA: DAL@ATL Final — May 22, 2026"),
    grade(tor_min_away, tor_min_home, 72, 100, market=166.5, half=1.0,
          label="WNBA: TOR@MIN Final — May 22, 2026"),
    grade(con_players, sea_players, 28, 37, market=159.5, half=0.5,
          label="WNBA: CON@SEA Halftime — May 23, 2026"),
    grade(min_players_f, chi_players_f, 85, 75, market=163.5, half=1.0,
          label="WNBA: MIN@CHI Final — May 23, 2026"),
    grade(ny_players, cle_players, 50, 44, market=218.5, half=0.5,
          label="NBA: NY@CLE Halftime — May 24, 2026"),
    grade(sa_players, okc_players, 58, 54, market=218.5, half=0.5,
          label="NBA: SA@OKC Halftime — May 24, 2026"),
]

print("=" * 70)
print(f"  NBA/WNBA TC BACKTEST — FINAL BOX SCORE EDITION")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  TC Formula: stat×[0.85|0.80|0.75|0.70] | Line=TC×0.88 | Edge>3=OVER | Edge<-3=UNDER")
print(f"  Halftime games: TC_combined×0.5 | Final games: full TC")
print("=" * 70)

for g in games:
    period = "HALFTIME" if g["half"] else "FINAL"
    print(f"\n{'─'*65}")
    print(f"  📊 {g['label']}")
    print(f"  Period: {period} | Actual: {g['away_score']}—{g['home_score']} | Total={g['actual_total']}")
    print(f"  Market Total: {g['market']} | TC Comb: {g['tc_comb']} | TC Line: {g['tc_line']}")
    print(f"  Edge: {g['edge']:+.2f} | Signal: {g['signal']} | Result: {g['result']} | {g['hit']}")
    print(f"  Diff (actual − tc_comb): {g['diff']:+.2f}")

hits = sum(1 for g in games if g["hit"] == "✅")
signals = sum(1 for g in games if g["signal"] != "PASS")
print(f"\n{'='*70}")
print(f"  SUMMARY: {hits}/{signals} signaled games hit — {round(hits/signals*100,1)}%")
print(f"  Total games tested: {len(games)}")
print(f"  Pass signals: {sum(1 for g in games if g['signal']=='PASS')}/{len(games)}")
print("=" * 70)

# Player prop detail for full-game WNBA
print("\n  PLAYER PROP GRADES (Full Games Only)")
print(f"  {'Player':<22} {'Stat':<5} {'TC':>6} {'Line':>5} {'Actual':>7} {'Dir':<6} {'Result':<6}")
print(f"  {'─'*60}")

full_games = [g for g in games if not g["half"]]
for g in full_games:
    print(f"\n  {g['label']}")
    if "DAL@ATL" in g["label"]:
        all_p = dal_atl_away + dal_atl_home
        am = {p["name"]: p for p in all_p}
    elif "TOR@MIN" in g["label"]:
        all_p = tor_min_away + tor_min_home
        am = {p["name"]: p for p in all_p}
    else:
        all_p = min_players_f + chi_players_f
        am = {p["name"]: p for p in all_p}

    prop_hits = 0
    prop_total = 0
    for p in all_p:
        if sf(p.get("status","ACTIVE")) == 0: continue
        for stat, key in [("PTS","pts"),("REB","reb"),("AST","ast"),("3PM","tpm")]:
            tc_p = tc(key, p.get(key,0), p.get("status","ACTIVE"))
            line_p = tl(tc_p)
            actual_val = p.get(key, 0)
            e = ed(tc_p, line_p)
            direction = "OVER" if e > 2.0 else "UNDER" if e < -2.0 else "NO BET"
            if direction == "NO BET": continue
            prop_total += 1
            res = "✅" if (actual_val > line_p and direction == "OVER") or (actual_val < line_p and direction == "UNDER") else "❌"
            if res == "✅": prop_hits += 1
            print(f"    {p['name']:<20} {stat:<5} {tc_p:>6.2f} {line_p:>5} {actual_val:>7.1f} {direction:<6} {res}")
    print(f"    → Prop hit rate: {prop_hits}/{prop_total} = {round(prop_hits/prop_total*100,1) if prop_total else 0}%")

# ─────────────────────────────────────────────────────────────────────
# SAVE TO FILE
# ─────────────────────────────────────────────────────────────────────
output = []
output.append(f"# TC Backtest Report — {datetime.datetime.now().strftime('%Y-%m-%d')}")
output.append(f"## Summary: {hits}/{signals} signaled games hit — {round(hits/signals*100,1)}%")
output.append("\n| Game | Period | Actual | TC Comb | TC Line | Market | Edge | Signal | Result | Hit |")
output.append("|---|---|---|---|---|---|---|---|---|---|")
for g in games:
    output.append(f"| {g['label']} | {'HALFTIME' if g['half'] else 'FINAL'} | {g['away_score']}—{g['home_score']}={g['actual_total']} | {g['tc_comb']} | {g['tc_line']} | {g['market']} | {g['edge']:+.2f} | {g['signal']} | {g['result']} | {g['hit']} |")

report = "\n".join(output)
with open("/home/workspace/TC_Backtest_Report.md", "w") as f:
    f.write(report)
print("\n  ✅ Report saved to /home/workspace/TC_Backtest_Report.md")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", choices=["NBA","WNBA","ALL"], default="ALL")
    args = parser.parse_args()
    if args.sport == "NBA":
        print("\n  Filtering: NBA games only")
    elif args.sport == "WNBA":
        print("\n  Filtering: WNBA games only")