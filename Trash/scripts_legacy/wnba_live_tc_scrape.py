#!/usr/bin/env python3
"""
WNBA + NBA Live TC Projections — May 14, 2026
Uses ESPN live API for real lines + TC math for picks.
"""
import json, re, os
import urllib.request
from datetime import datetime

ODDS_DIR = "/home/workspace/.zo_odds"
os.makedirs(ODDS_DIR, exist_ok=True)

PLAYER_FACTOR = 0.85
LINE_FACTOR   = 0.88
MIN_EDGE      = 2.0

# ── Team TC (based on current rosters) ───────────────────────────────────
# WNBA
TEAMS = {
    "LV":  {"name": "Las Vegas Aces",    "tc": 102.2, "inj": ["Chelsea Gray OUT (Achilles)"]},
    "CON": {"name": "Connecticut Sun",   "tc": 92.4,  "inj": ["Leila Lacan OUT (ankle)"]},
    "MIN": {"name": "Minnesota Lynx",    "tc": 88.2,  "inj": ["Napheesa Collier OUT (ankle)", "Alanna Smith OUT (knee)"]},
    "DAL": {"name": "Dallas Wings",      "tc": 96.5,  "inj": ["Azzi Fudd Q (knee)"]},
    "SEA": {"name": "Seattle Storm",     "tc": 96.8,  "inj": ["Jewell Loyd Q (ankle)"]},
    "WSH": {"name": "Washington Mystics","tc": 88.5,  "inj": []},
    "NY":  {"name": "New York Liberty",  "tc": 108.0, "inj": []},
    "POR": {"name": "Portland Fire",     "tc": 78.5,  "inj": []},
}
# NBA Playoffs
NBA_TEAMS = {
    "CLE": {"name": "Cleveland Cavaliers",  "tc": 112.5, "inj": []},
    "DET": {"name": "Detroit Pistons",      "tc": 105.8, "inj": ["Duncan Robinson Q (back)"]},
    "SA":  {"name": "San Antonio Spurs",    "tc": 98.5,  "inj": ["Chris Paul OUT (finger)", "Devin Vassell OUT (knee)"]},
    "MIN": {"name": "Minnesota Timberwolves","tc": 105.2, "inj": ["Terrence Shannon Jr. Q (hip)"]},
}

def tc_team(tc, market_total, spread, is_home=False):
    """Compute TC edge against market-implied team total."""
    if spread < 0:
        implied = (market_total + spread) / 2
    else:
        implied = (market_total - spread) / 2
    if is_home:
        implied *= 1.02
    edge = tc - implied
    return {"tc": round(tc, 1), "implied": round(implied, 1), "edge": round(edge, 1)}

def build_picks(away_tc, home_tc, away, home, spread, market_total, tc_combined, lean):
    legs = []
    seen = set()
    # Away spread: positive edge = bet AWAY team, negative edge = bet HOME team
    if abs(away_tc["edge"]) >= MIN_EDGE:
        team = away if away_tc["edge"] > 0 else home
        if team not in seen:
            seen.add(team)
            legs.append({"type":"SPREAD","team":team,"edge":round(abs(away_tc["edge"]),1),"odds":-110})
    # Home spread: positive edge = bet HOME team, negative edge = bet AWAY team
    if abs(home_tc["edge"]) >= MIN_EDGE:
        team = home if home_tc["edge"] > 0 else away
        if team not in seen:
            seen.add(team)
            legs.append({"type":"SPREAD","team":team,"edge":round(abs(home_tc["edge"]),1),"odds":-110})
    # Total
    legs.append({"type":"TOTAL","team":"COMBINED","edge":round(abs(tc_combined - market_total),1),
                 "lean":lean,"odds":-110})
    # Kelly sizing — cap at 10% to avoid impossible bets
    for leg in legs:
        prob = 0.52 if leg["type"] == "TOTAL" else 0.53
        odds = leg["odds"]
        if odds > 0:
            kelly = (prob * odds - (1-prob)) / odds
        else:
            kelly = (prob * (100 + abs(odds)) - (1-prob)) / 100
        kelly = min(max(kelly, 0), 0.10)  # cap at 10%
        leg["kelly_pct"] = round(kelly, 4)
        leg["bet_size"]  = round(kelly * 1000, 2)
        leg["confidence"] = "HIGH" if abs(leg["edge"]) >= 4 else "MEDIUM" if abs(leg["edge"]) >= 2 else "LOW"
    return legs

# ── Fetch ESPN Live Data ───────────────────────────────────────────────────
def fetch_espn(sport_path, sport_label):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=10).read())
        games = []
        for e in j.get("events", []):
            comp = e.get("competitions", [{}])[0]
            if not comp.get("competitors"): continue
            competitors = comp["competitors"]
            if len(competitors) < 2: continue
            away_c = competitors[0]
            home_c = competitors[1]
            if home_c.get("homeAway") == "home":
                away_c, home_c = home_c, away_c
            away_t = away_c["team"]
            home_t = home_c["team"]
            odds = comp.get("odds", [{}])
            o = odds[0] if odds else {}
            dt = e.get("date", "N/A")[:16]
            games.append({
                "id": e["id"],
                "sport": sport_label,
                "away_abbr": away_t.get("abbreviation",""),
                "home_abbr": home_t.get("abbreviation",""),
                "away_name": away_t.get("shortDisplayName",""),
                "home_name": home_t.get("shortDisplayName",""),
                "spread": o.get("spread"),
                "total":   o.get("overUnder"),
                "date_utc": dt,
            })
        return games
    except Exception as ex:
        print(f"  ESPN {sport_label} error: {ex}")
        return []

# ── MAIN ───────────────────────────────────────────────────────────────────
print("=" * 80)
print(" LIVE TC PROJECTIONS — May 14, 2026 (Updated via ESPN API)")
print("=" * 80)

espn_wnba = fetch_espn("basketball/wnba", "WNBA")
espn_nba  = fetch_espn("basketball/nba",   "NBA")

print(f"\n📡 ESPN WNBA: {len(espn_wnba)} games")
for g in espn_wnba:
    print(f"   {g['away_abbr']:>3} @ {g['home_abbr']:<3} | spread={g['spread']} | ou={g['total']} | {g['date_utc']}")

print(f"\n📡 ESPN NBA: {len(espn_nba)} games")
for g in espn_nba:
    print(f"   {g['away_abbr']:>3} @ {g['home_abbr']:<3} | spread={g['spread']} | ou={g['total']} | {g['date_utc']}")

all_projs = []
for g in espn_wnba + espn_nba:
    sport_teams = TEAMS if g["sport"] == "WNBA" else NBA_TEAMS
    away_abbr = g["away_abbr"]
    home_abbr = g["home_abbr"]
    spread    = g["spread"] or -3.5
    total     = g["total"] or 175.0

    away_t = sport_teams.get(away_abbr, {"tc": 90.0, "inj": []})
    home_t = sport_teams.get(home_abbr, {"tc": 90.0, "inj": []})

    away_tc = tc_team(away_t["tc"], total, -spread)
    home_tc = tc_team(home_t["tc"], total,  spread, is_home=True)
    tc_combined = round(away_tc["tc"] + home_tc["tc"], 1)
    lean = "UNDER" if tc_combined < total else "OVER"
    legs = build_picks(away_tc, home_tc, away_abbr, home_abbr, spread, total, tc_combined, lean)

    proj = {
        "sport": g["sport"], "game": f"{away_abbr} @ {home_abbr}",
        "away_abbr": away_abbr, "home_abbr": home_abbr,
        "away_name": g["away_name"], "home_name": g["home_name"],
        "away_tc": away_tc, "home_tc": home_tc,
        "tc_combined": tc_combined,
        "market_total": total, "spread": spread,
        "total_lean": lean, "total_edge": round(tc_combined - total, 1),
        "date_utc": g["date_utc"],
        "injuries": away_t.get("inj", []) + home_t.get("inj", []),
        "legs": legs,
    }
    all_projs.append(proj)

# Print report
print("\n" + "=" * 80)
for p in all_projs:
    print(f"\n🏀 [{p['sport']}] {p['game']} | {p['date_utc']}")
    print(f"   {p['away_name']} @ {p['home_name']}")
    print(f"   Line: {p['market_total']} | Spread: {p['spread']:+.1f}")
    print(f"   TC: {p['tc_combined']} | Lean: {p['total_lean']} | Edge: {p['total_edge']:+.1f}")
    print(f"   {p['away_abbr']:>3}: TC={p['away_tc']['tc']} | Implied={p['away_tc']['implied']} | Edge={p['away_tc']['edge']:+.1f}")
    print(f"   {p['home_abbr']:>3}: TC={p['home_tc']['tc']} | Implied={p['home_tc']['implied']} | Edge={p['home_tc']['edge']:+.1f}")
    print(f"   ── Picks ──")
    for leg in p["legs"]:
        pct = leg['kelly_pct']
        size = leg['bet_size']
        conf = leg['confidence']
        lean = leg.get('lean','')
        if leg['type'] == 'TOTAL':
            print(f"   {leg['type']:<7} | {lean:>5} {p['market_total']} | Edge:{leg['edge']:+.1f} | Kelly:{pct:.1%} | ${size:.0f} | {conf}")
        else:
            print(f"   {leg['type']:<7} | {leg['team']:>4} | Edge:{leg['edge']:+.1f} | Kelly:{pct:.1%} | ${size:.0f} | {conf}")

# Save outputs
with open(f"{ODDS_DIR}/TC_Live_2026-05-14.json", "w") as f:
    json.dump(all_projs, f, indent=2)

report_lines = ["# LIVE TC PROJECTIONS — May 14, 2026 (via ESPN API)\n"]
for p in all_projs:
    report_lines.append(f"\n## {p['sport']} | {p['game']} | {p['date_utc']}")
    report_lines.append(f"**{p['away_name']} @ {p['home_name']}**")
    report_lines.append(f"Line: {p['market_total']} | Spread: {p['spread']:+.1f}")
    report_lines.append(f"TC Combined: {p['tc_combined']} | Lean: {p['total_lean']} | Edge: {p['total_edge']:+.1f}")
    report_lines.append(f"| Pick | Team | Edge | Kelly% | Bet$ | Confidence |")
    report_lines.append(f"|---|---|---|---|---|---|")
    for leg in p["legs"]:
        report_lines.append(f"| {leg['type']} | {leg['team']} | {leg['edge']} | {leg['kelly_pct']:.1%} | ${leg['bet_size']:.0f} | {leg['confidence']} |")
    report_lines.append(f"**Injuries:** {', '.join(p['injuries']) or 'None'}")

with open(f"{ODDS_DIR}/TC_Live_2026-05-14.md", "w") as f:
    f.write("\n".join(report_lines))

print(f"\n✅ JSON: {ODDS_DIR}/TC_Live_2026-05-14.json")
print(f"✅ MD:   {ODDS_DIR}/TC_Live_2026-05-14.md")

# Summary table
print("\n" + "=" * 80)
print(" TC SUMMARY TABLE")
print("=" * 80)
print(f" {'Sport':<5} {'Game':<14} {'TC':>6} {'Lean':<6} {'Edge':>5} | Picks")
print("-" * 80)
for p in all_projs:
    legs_str = " | ".join([f"{l['type'][:3]}-{l['team']}({l['edge']:+.0f})" for l in p["legs"]])
    print(f" {p['sport']:<5} {p['game']:<14} {p['tc_combined']:>6.1f} {p['total_lean']:<6} {p['total_edge']:>+5.1f} | {legs_str}")