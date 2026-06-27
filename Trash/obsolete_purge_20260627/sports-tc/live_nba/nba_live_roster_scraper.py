#!/usr/bin/env python3
"""
NBA Live Roster Scraper — Conference Finals Edition
Fetches live ESPN roster + injury data for OKC/SAS/CLE/NYK
Merges with existing backtest rosters for stats
Generates injury-adjusted TC projections

Run: python3 live_nba/nba_live_roster_scraper.py
Output: live_nba/conference_finals_live.json, live_nba/injury_report.json
"""

import json, os, time, urllib.request, re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}

TEAM_IDS = {"OKC": "16", "SAS": "24", "CLE": "5", "NYK": "14"}
BASE_DIR = "/home/workspace/sports-tc/live_nba"
ROSTER_DIR = f"{BASE_DIR}/rosters"
os.makedirs(ROSTER_DIR, exist_ok=True)

BACKTEST_FILE = "/home/workspace/wnba_rosters/NBA_BACKTEST_ROSTERS.json"

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  [!] Fetch failed: {url} → {e}")
        return None

def load_backtest_rosters():
    if os.path.exists(BACKTEST_FILE):
        with open(BACKTEST_FILE) as f:
            return json.load(f)
    return {}

def get_espn_roster(team_code, team_id):
    """Get current roster from ESPN API."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster?enableRosterCapabilities=true"
    data = fetch_json(url)
    if not data or "athletes" not in data:
        return {}
    
    roster = {}
    for a in data.get("athletes", []):
        info = a.get("athlete", {})
        pos = a.get("position", {}).get("abbreviation", "G")
        status = a.get("status", {}).get("type", "active").upper()
        
        name = info.get("fullName", info.get("displayName", ""))
        jersey = info.get("jersey", "?")
        
        # Map ESPN status to TC status
        tc_status = "ACTIVE"
        if status in ["INJURY_RESERVE", "OUT", "SUSPENSION"]:
            tc_status = "OUT"
        elif status in ["QUESTIONABLE", "DOUBTFUL", "DAY_TO_DAY"]:
            tc_status = "Q"
        elif status == "PROBABLE":
            tc_status = "ACTIVE"
        
        # Get injury notes from athlete details if available
        injury_detail = ""
        if a.get("injuryStatus"):
            injury_detail = a.get("injuryStatus", "")
        
        roster[name] = {
            "jersey": jersey,
            "position": pos,
            "tc_status": tc_status,
            "injury_detail": injury_detail,
            "active": status in ["ACTIVE", "PROBABLE"],
        }
    return roster

def get_espn_injuries(team_code, team_id):
    """Get injury report from ESPN."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/injuries"
    data = fetch_json(url)
    injuries = {}
    if data and "injuries" in data:
        for inj in data["injuries"]:
            info = inj.get("athlete", {})
            name = info.get("fullName", info.get("displayName", ""))
            status = inj.get("status", "ACTIVE").upper()
            detail = inj.get("description", "")
            injuries[name] = {"status": status, "detail": detail}
    return injuries

def get_team_stats_from_backtest(team_code):
    """Load team's raw stats from backtest JSON."""
    bt = load_backtest_rosters()
    teams = bt.get("teams", {})
    if team_code in teams:
        return teams[team_code]
    return {}

def merge_roster_with_stats(team_code, team_id):
    """Merge live ESPN roster with backtest stats."""
    espn_roster = get_espn_roster(team_code, team_id)
    espn_injuries = get_espn_injuries(team_code, team_id)
    backtest = get_team_stats_from_backtest(team_code)
    
    if not backtest:
        print(f"  [!] No backtest data for {team_code}")
        return None
    
    players = []
    all_names = set(list(espn_roster.keys()) + [p["name"] for p in (backtest.get("starters", []) + backtest.get("bench", []))])
    
    # Process starters from backtest
    for p in backtest.get("starters", []):
        name = p["name"]
        
        # Override status from live ESPN if available
        tc_status = p.get("status", "ACTIVE")
        injury_detail = ""
        
        if name in espn_injuries:
            inj = espn_injuries[name]
            if inj["status"] == "OUT":
                tc_status = "OUT"
            elif inj["status"] == "QUESTIONABLE":
                tc_status = "Q"
            injury_detail = inj["detail"]
        elif name in espn_roster:
            live = espn_roster[name]
            if live["tc_status"] != "ACTIVE":
                tc_status = live["tc_status"]
            if live["injury_detail"]:
                injury_detail = live["injury_detail"]
        
        players.append({
            "name": name,
            "position": p.get("position", "G"),
            "status": tc_status,
            "ppg": p.get("ppg", 0),
            "rpg": p.get("rpg", 0),
            "apg": p.get("apg", 0),
            "tpm": p.get("tpm", 0),
            "injury_detail": injury_detail,
            "role": "STARTER",
        })
    
    # Process bench
    for p in backtest.get("bench", []):
        name = p["name"]
        
        tc_status = p.get("status", "ACTIVE")
        injury_detail = ""
        
        if name in espn_injuries:
            inj = espn_injuries[name]
            if inj["status"] == "OUT":
                tc_status = "OUT"
            elif inj["status"] == "QUESTIONABLE":
                tc_status = "Q"
            injury_detail = inj["detail"]
        elif name in espn_roster:
            live = espn_roster[name]
            if live["tc_status"] != "ACTIVE":
                tc_status = live["tc_status"]
            if live["injury_detail"]:
                injury_detail = live["injury_detail"]
        
        players.append({
            "name": name,
            "position": p.get("position", "G"),
            "status": tc_status,
            "ppg": p.get("ppg", 0),
            "rpg": p.get("rpg", 0),
            "apg": p.get("apg", 0),
            "tpm": p.get("tpm", 0),
            "injury_detail": injury_detail,
            "role": "BENCH",
        })
    
    return players

def generate_tc(player):
    """Generate TC projections for one player."""
    TC = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
    Q, OUT = 0.55, 0.0
    
    status = player["status"]
    if status == "OUT":
        mult_pts, mult_reb, mult_ast, mult_tpm = OUT, OUT, OUT, OUT
    elif status == "Q":
        mult_pts = mult_reb = mult_ast = mult_tpm = Q
    else:
        mult_pts = mult_reb = mult_ast = mult_tpm = 1.0
    
    tc_pts = round(player["ppg"] * TC["pts"] * mult_pts, 1)
    tc_reb = round(player["rpg"] * TC["reb"] * mult_reb, 1)
    tc_ast = round(player["apg"] * TC["ast"] * mult_ast, 1)
    tc_tpm = round(player["tpm"] * TC["tpm"] * mult_tpm, 1)
    tc_line = round(tc_pts * 0.88)
    edge = round(player["ppg"] - tc_line, 1)
    
    return {
        "tc_pts": tc_pts, "tc_reb": tc_reb, "tc_ast": tc_ast, "tc_tpm": tc_tpm,
        "tc_line_pts": tc_line, "edge_pts": edge,
    }

def status_icon(status):
    return {"ACTIVE": "✅", "Q": "⚠️", "OUT": "❌"}.get(status, "?")

def build_injury_report(all_players):
    report = {}
    for team, players in all_players.items():
        injuries = []
        for p in players:
            if p["status"] != "ACTIVE":
                injuries.append({
                    "player": p["name"],
                    "position": p["position"],
                    "status": p["status"],
                    "detail": p.get("injury_detail", ""),
                })
        report[team] = injuries
    return report

def print_injury_report(report):
    print("\n" + "=" * 70)
    print("  ⚕  INJURY REPORT — CONFERENCE FINALS")
    print("=" * 70)
    for team, injuries in report.items():
        status_counts = {"ACTIVE": 0, "Q": 0, "OUT": 0}
        for p in injuries:
            if p["status"] in status_counts:
                status_counts[p["status"]] += 1
        print(f"\n  {team} ({len(injuries)} injuries)")
        print(f"  Active: {status_counts['ACTIVE']} | Q: {status_counts['Q']} | OUT: {status_counts['OUT']}")
        for inj in injuries:
            icon = status_icon(inj["status"])
            detail = f" — {inj['detail']}" if inj["detail"] else ""
            print(f"  {icon} {inj['player']} ({inj['position']}): {inj['status']}{detail}")

def print_starting_lineup(team, players, tc_map):
    print(f"\n  {team} — Starting Lineup")
    print(f"  {'Player':<22} {'POS':<5} {'TC PTS':>7} {'TC REB':>7} {'TC AST':>7} {'TC 3PM':>7} {'Status':<6}")
    print(f"  {'-'*70}")
    starters = [p for p in players if p["role"] == "STARTER"]
    bench = [p for p in players if p["role"] == "BENCH"]
    for i, p in enumerate(starters, 1):
        tc = tc_map[p["name"]]
        icon = status_icon(p["status"])
        print(f"  {i}. {p['name']:<20} {p['position']:<5} {tc['tc_pts']:>7.1f} {tc['tc_reb']:>7.1f} {tc['tc_ast']:>7.1f} {tc['tc_tpm']:>7.1f} {icon} {p['status']:<6}")
    print(f"  --- BENCH ---")
    for p in bench:
        tc = tc_map[p["name"]]
        icon = status_icon(p["status"])
        if p["status"] != "ACTIVE":
            print(f"  B {p['name']:<20} {p['position']:<5} {tc['tc_pts']:>7.1f} {tc['tc_reb']:>7.1f} {tc['tc_ast']:>7.1f} {tc['tc_tpm']:>7.1f} {icon} {p['status']:<6}")

def print_tc_system_summary(all_players):
    print("\n" + "=" * 70)
    print("  TC SYSTEM SUMMARY — Conference Finals Games")
    print("=" * 70)
    
    games = [("SAS", "OKC"), ("CLE", "NYK")]
    for away, home in games:
        away_players = all_players.get(away, [])
        home_players = all_players.get(home, [])
        
        away_tc = sum(generate_tc(p)["tc_pts"] for p in away_players)
        home_tc = sum(generate_tc(p)["tc_pts"] for p in home_players)
        combined = away_tc + home_tc
        
        away_reb = sum(generate_tc(p)["tc_reb"] for p in away_players)
        home_reb = sum(generate_tc(p)["tc_reb"] for p in home_players)
        away_ast = sum(generate_tc(p)["tc_ast"] for p in away_players)
        home_ast = sum(generate_tc(p)["tc_ast"] for p in home_players)
        away_tpm = sum(generate_tc(p)["tc_tpm"] for p in away_players)
        home_tpm = sum(generate_tc(p)["tc_tpm"] for p in home_players)
        
        print(f"\n  {away} @ {home}")
        print(f"  TC PTS:  {away_tc:>6.1f}  |  {home_tc:>6.1f}  |  Combined: {combined:>6.1f}")
        print(f"  TC REB:  {away_reb:>6.1f}  |  {home_reb:>6.1f}")
        print(f"  TC AST:  {away_ast:>6.1f}  |  {home_ast:>6.1f}")
        print(f"  TC 3PM:  {away_tpm:>6.1f}  |  {home_tpm:>6.1f}")
        
        # Estimate O/U line (TC * 1.18 playoff adjustment)
        est_total = combined * 1.18
        print(f"  Est Game Total: ~{est_total:.0f} (TC × 1.18 playoff adj)")

def print_prop_candidates(players, tc_map):
    """Print players with best TC edge."""
    candidates = []
    for p in players:
        if p["ppg"] < 5:
            continue
        tc = tc_map[p["name"]]
        if tc["edge_pts"] >= 2.0:
            candidates.append((p, tc))
    
    candidates.sort(key=lambda x: x[1]["edge_pts"], reverse=True)
    print(f"  {'Player':<22} {'TC PTS':>7} {'TC Line':>8} {'Edge':>6} {'Valid'}")
    print(f"  {'-'*55}")
    for p, tc in candidates[:8]:
        valid = "✅" if tc["edge_pts"] >= 3.0 else "⚠️"
        print(f"  {p['name']:<22} {tc['tc_pts']:>7.1f} {tc['tc_line_pts']:>8d} {tc['edge_pts']:>+6.1f} {valid}")

if __name__ == "__main__":
    print(f"\n{'='*70}")
    print("  NBA LIVE ROSTER SCRAPER — Conference Finals")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    all_players = {}
    
    for team_code, team_id in TEAM_IDS.items():
        print(f"Fetching {team_code}...")
        players = merge_roster_with_stats(team_code, team_id)
        if players:
            all_players[team_code] = players
            print(f"  {team_code}: {len(players)} players loaded")
    
    # Save master file
    master_file = f"{BASE_DIR}/conference_finals_live.json"
    with open(master_file, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "teams": all_players}, f, indent=2)
    print(f"\nSaved: {master_file}")
    
    # Build injury report
    injury_report = build_injury_report(all_players)
    injury_file = f"{BASE_DIR}/injury_report.json"
    with open(injury_file, "w") as f:
        json.dump(injury_report, f, indent=2)
    print(f"Saved: {injury_file}")
    
    # Generate TC maps for all teams
    all_tc_maps = {}
    for team, players in all_players.items():
        tc_map = {p["name"]: generate_tc(p) for p in players}
        all_tc_maps[team] = tc_map
    
    # Print injury report
    print_injury_report(injury_report)
    
    # Print starting lineups and prop candidates
    for team_code in TEAM_IDS:
        if team_code in all_players:
            print_starting_lineup(team_code, all_players[team_code], all_tc_maps[team_code])
            print(f"\n  Prop Candidates ({team_code}):")
            print_prop_candidates(all_players[team_code], all_tc_maps[team_code])
    
    # Print TC system summary
    print_tc_system_summary(all_players)

