#!/usr/bin/env python3
"""
Live TC Pipeline — NBA + WNBA Conference Finals
==============================================
Full roster projections for all players.
TC applies ONLY to player props (PTS×0.85, REB×0.80, AST×0.75, TPM×0.70).
Team/game totals are RAW projections only.

Run:
  python3 live_tc_pipeline.py --sport NBA --game "SAS @ OKC"
  python3 live_tc_pipeline.py --sport NBA --injury-report
  python3 live_tc_pipeline.py --sport NBA --all-games
  python3 live_tc_pipeline.py --sport NBA --full-roster "SAS"
"""

import json, os, argparse
from datetime import datetime

# ─── Paths ───────────────────────────────────────────────────────────────────
NBA_LIVE_DIR   = "/home/workspace/sports-tc/live_nba"
MONITOR_DIR    = "/home/workspace/sports-tc/monitor"
REPORTS_DIR    = "/home/workspace/sports-tc/reports"
NBA_BACKTEST  = "/home/workspace/wnba_rosters/NBA_BACKTEST_ROSTERS.json"
WNBA_BACKTEST = "/home/workspace/wnba_rosters/WNBA_BACKTEST_ROSTERS.json"

os.makedirs(REPORTS_DIR, exist_ok=True)

# ─── TC Constants (corrected) ─────────────────────────────────────────────────
TC_FACTORS  = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
Q_FACTOR    = 0.55   # Questionable: TC × 0.55
OUT_FACTOR = 0.0    # OUT: 0 contribution
LINE_FACTOR = 0.88  # TC_line = TC_pts × 0.88

# ─── Roster Loader ────────────────────────────────────────────────────────────
def load_live_roster(team_code, sport="NBA"):
    """Load roster from live scrape JSON (prioritized) or backtest JSON."""
    live_file = f"{NBA_LIVE_DIR}/conference_finals_live.json"
    if os.path.exists(live_file):
        with open(live_file) as f:
            data = json.load(f)
        teams_data = data.get("teams", {})
        if team_code in teams_data:
            raw = teams_data[team_code]
            if isinstance(raw, list):
                starters = [p for p in raw if p.get("role") == "STARTER"]
                bench = [p for p in raw if p.get("role") == "BENCH"]
                return {"starters": starters, "bench": bench}
            if isinstance(raw, dict):
                return raw

    bt_file = NBA_BACKTEST if sport == "NBA" else WNBA_BACKTEST
    if os.path.exists(bt_file):
        with open(bt_file) as f:
            bt = json.load(f)
        teams = bt.get("teams", {})
        if team_code in teams:
            t = teams[team_code]
            if isinstance(t, dict):
                return {"starters": t.get("starters", []), "bench": t.get("bench", [])}
            if isinstance(t, list):
                return {
                    "starters": [p for p in t if p.get("role") == "STARTER"],
                    "bench": [p for p in t if p.get("role") == "BENCH"]
                }
    return None


def load_injury_report():
    inj_file = f"{NBA_LIVE_DIR}/injury_report.json"
    if os.path.exists(inj_file):
        with open(inj_file) as f:
            return json.load(f)
    return {}


# ─── TC Calculator ─────────────────────────────────────────────────────────────
def calc_tc(player):
    s = player.get("status", "ACTIVE")
    if s == "OUT":
        mp = mr = ma = mt = OUT_FACTOR
    elif s == "Q":
        mp = mr = ma = mt = Q_FACTOR
    else:
        mp = mr = ma = mt = 1.0

    tc_pts = round(player.get("ppg", 0) * TC_FACTORS["pts"] * mp, 1)
    tc_reb = round(player.get("rpg", 0) * TC_FACTORS["reb"] * mr, 1)
    tc_ast = round(player.get("apg", 0) * TC_FACTORS["ast"] * ma, 1)
    tc_tpm = round(player.get("tpm", 0) * TC_FACTORS["tpm"] * mt, 1)
    tc_line = round(tc_pts * LINE_FACTOR)
    edge = round(player.get("ppg", 0) - tc_line, 1)
    return {
        "tc_pts": tc_pts, "tc_reb": tc_reb, "tc_ast": tc_ast, "tc_tpm": tc_tpm,
        "tc_line": tc_line, "edge": edge
    }


def status_icon(s):
    return {"ACTIVE": "✅", "Q": "⚠️", "OUT": "❌"}.get(s, "?")


# ─── Report: Full Roster Projections ─────────────────────────────────────────
def generate_full_roster_report(team_code, sport="NBA"):
    """Print ALL players (starters + bench) with full TC projections."""
    roster = load_live_roster(team_code, sport)
    if not roster:
        print(f"[!] No roster found for {team_code}")
        return

    all_players = roster.get("starters", []) + roster.get("bench", [])
    tc_map = {p["name"]: calc_tc(p) for p in all_players}

    print(f"\n{'='*92}")
    print(f"  👥 FULL ROSTER PROJECTIONS — {team_code}")
    print(f"  TC = stat×0.85 | Q=×0.55 | OUT=0 | Line = TC_pts×0.88")
    print(f"{'='*92}")
    print(f"\n  {team_code} — STARTING LINEUP (5 players)")
    print(f"  {'Player':<22} {'POS':<5} {'TC PTS':>7} {'TC REB':>7} {'TC AST':>7} {'TC 3PM':>7} {'TC LINE':>8} {'EDGE':>6} Status")
    print(f"  {'-'*90}")

    for i, p in enumerate(roster.get("starters", []), 1):
        tc = tc_map[p["name"]]
        icon = status_icon(p.get("status", "ACTIVE"))
        edge_sign = "+" if tc["edge"] >= 0 else ""
        print(f"  {i}. {p['name']:<20} {p.get('position','?'):<5} "
              f"{tc['tc_pts']:>7.1f} {tc['tc_reb']:>7.1f} {tc['tc_ast']:>7.1f} {tc['tc_tpm']:>7.1f} "
              f"{tc['tc_line']:>8d} {edge_sign}{tc['edge']:>5.1f} {icon} {p.get('status','ACTIVE')}")

    bench_players = roster.get("bench", [])
    print(f"\n  {team_code} — BENCH ({len(bench_players)} players)")
    print(f"  {'Player':<22} {'POS':<5} {'TC PTS':>7} {'TC REB':>7} {'TC AST':>7} {'TC 3PM':>7} {'TC LINE':>8} {'EDGE':>6} Status")
    print(f"  {'-'*90}")

    for p in bench_players:
        tc = tc_map[p["name"]]
        icon = status_icon(p.get("status", "ACTIVE"))
        edge_sign = "+" if tc["edge"] >= 0 else ""
        bench_marker = "B " if p.get("role") == "BENCH" else "  "
        print(f"  {bench_marker}{p['name']:<20} {p.get('position','?'):<5} "
              f"{tc['tc_pts']:>7.1f} {tc['tc_reb']:>7.1f} {tc['tc_ast']:>7.1f} {tc['tc_tpm']:>7.1f} "
              f"{tc['tc_line']:>8d} {edge_sign}{tc['edge']:>5.1f} {icon} {p.get('status','ACTIVE')}")

    # Team totals
    team_tc_pts = sum(tc_map[p["name"]]["tc_pts"] for p in all_players)
    team_tc_reb = sum(tc_map[p["name"]]["tc_reb"] for p in all_players)
    team_tc_ast = sum(tc_map[p["name"]]["tc_ast"] for p in all_players)
    team_tc_tpm = sum(tc_map[p["name"]]["tc_tpm"] for p in all_players)
    active_count = len([p for p in all_players if p.get("status") != "OUT"])

    print(f"\n  {'─'*90}")
    print(f"  TEAM TOTAL ({active_count} active) | TC PTS: {team_tc_pts:.1f} | TC REB: {team_tc_reb:.1f} | TC AST: {team_tc_ast:.1f} | TC 3PM: {team_tc_tpm:.1f}")

    # Raw totals (non-TC)
    raw_pts = sum(p.get("ppg", 0) for p in all_players if p.get("status") != "OUT")
    raw_reb = sum(p.get("rpg", 0) for p in all_players if p.get("status") != "OUT")
    raw_ast = sum(p.get("apg", 0) for p in all_players if p.get("status") != "OUT")
    raw_tpm = sum(p.get("tpm", 0) for p in all_players if p.get("status") != "OUT")
    print(f"  RAW TOTAL (no TC applied)     | PTS: {raw_pts:.1f} | REB: {raw_reb:.1f} | AST: {raw_ast:.1f} | TPM: {raw_tpm:.1f}")


# ─── Report: Injury Report ────────────────────────────────────────────────────
def generate_injury_report(sport="NBA"):
    teams = {"NBA": ["OKC", "SAS", "CLE", "NYK"], "WNBA": []}
    if sport == "WNBA":
        import json as _j
        with open(WNBA_BACKTEST) as f:
            wnba = _j.load(f)
        teams["WNBA"] = list(wnba.get("teams", {}).keys())

    print(f"\n{'='*70}")
    print(f"  ⚕  INJURY REPORT — {sport}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    for team in teams[sport]:
        roster = load_live_roster(team, sport)
        if not roster:
            continue
        all_players = roster.get("starters", []) + roster.get("bench", [])
        injuries = [p for p in all_players if p.get("status") != "ACTIVE"]
        active = [p for p in all_players if p.get("status") == "ACTIVE"]
        q_players = [p for p in all_players if p.get("status") == "Q"]
        out_players = [p for p in all_players if p.get("status") == "OUT"]

        print(f"\n  {team}  ({len(active)} ✅ | {len(q_players)} ⚠️ | {len(out_players)} ❌)")
        print(f"  {'─'*65}")
        for p in out_players:
            detail = p.get("injury_detail", "")
            print(f"  ❌ {p['name']:<22} {p.get('position','?'):<5} {detail}")
        for p in q_players:
            detail = p.get("injury_detail", "")
            print(f"  ⚠️  {p['name']:<22} {p.get('position','?'):<5} {detail}")
        if not injuries:
            print(f"  📋 No injuries reported — all players ACTIVE")


# ─── Report: Game TC Projections ──────────────────────────────────────────────
def generate_game_report(away_code, home_code, sport="NBA"):
    away_roster = load_live_roster(away_code, sport)
    home_roster = load_live_roster(home_code, sport)

    if not away_roster or not home_roster:
        print(f"[!] Missing roster for {away_code} or {home_code}")
        return

    away_players = away_roster.get("starters", []) + away_roster.get("bench", [])
    home_players = home_roster.get("starters", []) + home_roster.get("bench", [])

    # Raw game totals (no TC)
    away_raw = {
        "pts": sum(p.get("ppg", 0) for p in away_players),
        "reb": sum(p.get("rpg", 0) for p in away_players),
        "ast": sum(p.get("apg", 0) for p in away_players),
        "tpm": sum(p.get("tpm", 0) for p in away_players),
    }
    home_raw = {
        "pts": sum(p.get("ppg", 0) for p in home_players),
        "reb": sum(p.get("rpg", 0) for p in home_players),
        "ast": sum(p.get("apg", 0) for p in home_players),
        "tpm": sum(p.get("tpm", 0) for p in home_players),
    }

    # TC game totals (for player props only — not game total O/U)
    away_tc = {k: sum(calc_tc(p)[f"tc_{k}"] for p in away_players) for k in ["pts","reb","ast","tpm"]}
    home_tc = {k: sum(calc_tc(p)[f"tc_{k}"] for p in home_players) for k in ["pts","reb","ast","tpm"]}
    away_tc_pts = sum(calc_tc(p)["tc_pts"] for p in away_players)
    home_tc_pts = sum(calc_tc(p)["tc_pts"] for p in home_players)
    combined_tc = away_tc_pts + home_tc_pts

    # Est game total from raw (playoff adj × 1.18)
    est_game_total = round((away_raw["pts"] + home_raw["pts"]) * 1.18)

    print(f"\n{'='*92}")
    print(f"  🏀 TC GAME REPORT — {away_code} @ {home_code}")
    print(f"  TC Formula: TC PTS = pts×0.85 | Q=×0.55 | OUT=0 | Line=PTS×0.88")
    print(f"{'='*92}")

    print(f"\n  RAW GAME TOTALS (no TC applied to game total)")
    print(f"  {away_code} RAW: {away_raw['pts']:.1f} pts | {away_raw['reb']:.1f} reb | {away_raw['ast']:.1f} ast | {away_raw['tpm']:.1f} 3pm")
    print(f"  {home_code} RAW: {home_raw['pts']:.1f} pts | {home_raw['reb']:.1f} reb | {home_raw['ast']:.1f} ast | {home_raw['tpm']:.1f} 3pm")
    print(f"  Combined RAW PTS: {away_raw['pts'] + home_raw['pts']:.1f} | Est Game Total: ~{est_game_total} (×1.18 playoff adj)")

    print(f"\n  TC PLAYER PROPS ONLY (not game total)")
    print(f"  {away_code} TC: {away_tc_pts:.1f} pts | {away_tc['reb']:.1f} reb | {away_tc['ast']:.1f} ast | {away_tc['tpm']:.1f} 3pm")
    print(f"  {home_code} TC: {home_tc_pts:.1f} pts | {home_tc['reb']:.1f} reb | {home_tc['ast']:.1f} ast | {home_tc['tpm']:.1f} 3pm")

    # Full roster for each team
    for label, players in [(f"{away_code} (Away)", away_players), (f"{home_code} (Home)", home_players)]:
        print(f"\n  {'─'*92}")
        print(f"  👥 FULL ROSTER — {label}")
        print(f"  {'Player':<22} {'POS':<5} {'TC PTS':>7} {'TC REB':>7} {'TC AST':>7} {'TC 3PM':>7} {'TC LINE':>8} {'EDGE':>6} Status")
        print(f"  {'─'*92}")

        tc_map = {p["name"]: calc_tc(p) for p in players}
        sorted_players = sorted(players, key=lambda p: tc_map[p["name"]]["tc_pts"], reverse=True)

        for p in sorted_players:
            tc = tc_map[p["name"]]
            icon = status_icon(p.get("status", "ACTIVE"))
            edge_sign = "+" if tc["edge"] >= 0 else ""
            role_marker = "S" if p.get("role") == "STARTER" else "B"
            print(f"  [{role_marker}] {p['name']:<20} {p.get('position','?'):<5} "
                  f"{tc['tc_pts']:>7.1f} {tc['tc_reb']:>7.1f} {tc['tc_ast']:>7.1f} {tc['tc_tpm']:>7.1f} "
                  f"{tc['tc_line']:>8d} {edge_sign}{tc['edge']:>5.1f} {icon} {p.get('status','ACTIVE')}")

        team_tc = sum(tc_map[p["name"]]["tc_pts"] for p in players)
        team_raw = sum(p.get("ppg", 0) for p in players)
        print(f"  {'─'*92}")
        print(f"  TEAM TOTAL: TC={team_tc:.1f} pts | RAW={team_raw:.1f} pts")


# ─── Report: All Conference Finals Games ─────────────────────────────────────
def generate_all_games(sport="NBA"):
    games = [("SAS", "OKC"), ("CLE", "NYK")]
    for away, home in games:
        generate_game_report(away, home, sport)
        print("\n")


# ─── Save backtest seed ───────────────────────────────────────────────────────
def save_backtest_seed(away_code, home_code, actual_total, sport="NBA"):
    import csv
    seed_file = f"{MONITOR_DIR}/backtest_master.csv"
    file_exists = os.path.exists(seed_file)

    with open(seed_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "phase", "game", "away", "home", "actual_total",
                             "tc_line", "market_total", "pick", "signal", "result", "notes"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d"), "CONF FINALS",
            f"{away_code} @ {home_code}", away_code, home_code,
            actual_total, "", "", "", "", ""
        ])
    print(f"[✓] Backtest seed saved to {seed_file}")


# ─── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live TC Pipeline — Full Roster TC Projections")
    parser.add_argument("--sport", default="NBA", choices=["NBA", "WNBA"])
    parser.add_argument("--game", help="Game in format 'AWAY @ HOME'")
    parser.add_argument("--injury-report", action="store_true")
    parser.add_argument("--all-games", action="store_true")
    parser.add_argument("--full-roster", help="Single team full roster projection")
    parser.add_argument("--save-seed", help="Save backtest seed: AWAY HOME ACTUAL_TOTAL")
    args = parser.parse_args()

    if args.injury_report:
        generate_injury_report(args.sport)
    elif args.full_roster:
        generate_full_roster_report(args.full_roster.upper(), args.sport)
    elif args.all_games:
        generate_all_games(args.sport)
    elif args.game:
        parts = args.game.split(" @ ")
        if len(parts) == 2:
            generate_game_report(parts[0].strip(), parts[1].strip(), args.sport)
        else:
            print("[!] Use format: 'AWAY @ HOME'")
    elif args.save_seed:
        parts = args.save_seed.split()
        if len(parts) >= 3:
            save_backtest_seed(parts[0], parts[1], parts[2], args.sport)
        else:
            print("[!] Use: --save-seed 'AWAY HOME ACTUAL_TOTAL'")
    else:
        print("""
Live TC Pipeline — Conference Finals Edition
============================================
Usage:
  --injury-report            Print full injury report
  --all-games                Print all CF game reports
  --game 'SAS @ OKC'         Print specific game report
  --full-roster 'OKC'        Full roster projection for one team
  --save-seed 'SAS OKC 241'  Save backtest seed

TC Rules:
  TC applies ONLY to player prop categories (PTS, REB, AST, 3PM).
  Team/game totals are RAW projections only — no TC line, no TC edge.
""")