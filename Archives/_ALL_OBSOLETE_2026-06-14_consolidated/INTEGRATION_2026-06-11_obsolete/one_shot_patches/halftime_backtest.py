#!/usr/bin/env python3
"""Halftime backtest: pull real DK combo lines at halftime, project the 2nd-half stats from 1H rates, grade. Run for NBA + WNBA last 5 days."""

import json, csv, sys, re, requests
from pathlib import Path
from collections import defaultdict
from datetime import datetime
sys.path.insert(0, "/home/workspace/Projects")
from tc_math import project_pra, project_pr, project_pa, ceiling_recommend

REPORTS = Path("/home/workspace/Reports")
HALFTIME_DIR = Path("/home/workspace/Daily_Log/halftime")
FINAL_DIR = Path("/home/workspace/Daily_Log/final")
LEAGUE_ESPN = {"WNBA": "basketball/wnba", "NBA": "basketball/nba"}
ODDS_SPORT = {"WNBA": "basketball_wnba", "NBA": "basketball_nba"}
SECRET_PATH = Path("/root/.zo/secrets.env")
def load_key(name):
    for line in SECRET_PATH.read_text().splitlines():
        m = re.match(r"^\s*" + re.escape(name) + r"\s*=\s*[\"']?([^\"'\s#]+)", line)
        if m: return m.group(1)
    return ""
ODDS_KEY = load_key("ODDS_API_KEY")

ODDS_TO_ESPN = {
    "Atlanta Dream": "ATL", "Chicago Sky": "CHI", "Connecticut Sun": "CON",
    "Dallas Wings": "DAL", "Indiana Fever": "IND", "Las Vegas Aces": "LV",
    "Los Angeles Sparks": "LA", "Minnesota Lynx": "MIN", "New York Liberty": "NY",
    "Phoenix Mercury": "PHX", "Seattle Storm": "SEA", "Washington Mystics": "WSH",
    "Golden State Valkyries": "GS", "Toronto Tempo": "TOR", "Portland Fire": "POR",
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SA",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

def find_espn_abbrev(odds_away, odds_home):
    a = ODDS_TO_ESPN.get(odds_away, odds_away)
    h = ODDS_TO_ESPN.get(odds_home, odds_home)
    return a, h

def fetch_odds_api_event(sport, event_id, halftime_iso):
    r = requests.get(
        "https://api.the-odds-api.com/v4/historical/sports/" + ODDS_SPORT[sport] + "/events/" + event_id + "/odds",
        params={"apiKey": ODDS_KEY, "regions": "us", "markets": "player_points_rebounds_assists,player_points_rebounds,player_points_assists", "oddsFormat": "american", "date": halftime_iso, "bookmakers": "draftkings"},
        timeout=20,
    )
    if r.status_code != 200: return {}
    return r.json().get("data", {})

def extract_combo_lines(odds_data):
    out = []
    for bk in odds_data.get("bookmakers", []):
        if bk.get("key") != "draftkings": continue
        for m in bk.get("markets", []):
            ctype = {"player_points_rebounds_assists": "PRA", "player_points_rebounds": "PR", "player_points_assists": "PA"}.get(m["key"])
            if not ctype: continue
            for o in m.get("outcomes", []):
                if "point" in o and o.get("name") in ("Over", "Under"):
                    out.append((o.get("description", "?"), ctype, float(o["point"]), o["name"], o.get("price")))
    return out

def main():
    rows = []
    halftime_files = sorted(HALFTIME_DIR.glob("*.json"))
    for hf in halftime_files:
        ht = json.loads(hf.read_text())
        sport = ht.get("sport") or "WNBA"
        if sport not in LEAGUE_ESPN: continue
        eid = ht.get("event_id")
        players_1h = ht.get("players", {})
        if not players_1h: continue
        # find matching final
        final = next((f for f in FINAL_DIR.glob(f"*{eid}*.json") if "halftime" not in f.name), None)
        if not final: continue
        final_data = json.loads(final.read_text())
        players_full = final_data.get("players", {})
        # halftime timestamp: 1.5 hours after game start
        game_date = hf.stem.split("_")[-1]
        halftime_iso = game_date[:4] + "-" + game_date[4:6] + "-" + game_date[6:8] + "T03:00:00Z"
        odds = fetch_odds_api_event(sport, eid, halftime_iso)
        combos = extract_combo_lines(odds)
        if not combos: continue
        for player, ctype, line, side, price in combos:
            p1 = players_1h.get(player.lower())
            pf = players_full.get(player.lower())
            if not p1 or not pf: continue
            # 2H stats: full - 1H
            pts_2h = pf.get("points", 0) - p1.get("points", 0)
            reb_2h = pf.get("rebounds", 0) - p1.get("rebounds", 0)
            ast_2h = pf.get("assists", 0) - p1.get("assists", 0)
            full_combo = {"PRA": pf.get("points",0)+pf.get("rebounds",0)+pf.get("assists",0), "PR": pf.get("points",0)+pf.get("rebounds",0), "PA": pf.get("points",0)+pf.get("assists",0)}[ctype]
            one_h_combo = {"PRA": p1.get("points",0)+p1.get("rebounds",0)+p1.get("assists",0), "PR": p1.get("points",0)+p1.get("rebounds",0), "PA": p1.get("points",0)+p1.get("assists",0)}[ctype]
            # TC projection = 2H projection = full - 1H
            if ctype == "PRA":
                tc_proj_full = project_pra(pf.get("points",0), pf.get("rebounds",0), pf.get("assists",0), "ACTIVE", sport)
                tc_proj_2h = tc_proj_full - one_h_combo
            elif ctype == "PR":
                tc_proj_full = project_pr(pf.get("points",0), pf.get("rebounds",0), "ACTIVE", sport)
                tc_proj_2h = tc_proj_full - one_h_combo
            else:
                tc_proj_full = project_pa(pf.get("points",0), pf.get("assists",0), "ACTIVE", sport)
                tc_proj_2h = tc_proj_full - one_h_combo
            # actual 2H outcome
            actual_2h = {"PRA": pts_2h+reb_2h+ast_2h, "PR": pts_2h+reb_2h, "PA": pts_2h+ast_2h}[ctype]
            hit_2h = (actual_2h > line) if side == "Over" else (actual_2h < line)
            # pre-game line using full projection
            full_pick = "Over" if tc_proj_full > line else "Under"
            full_correct = (full_pick == side and (full_combo > line if side == "Over" else full_combo < line))
            rows.append({
                "sport": sport, "event_id": eid, "player": player, "combo_type": ctype,
                "dk_line": line, "side": side, "price": price,
                "1h_pts": p1.get("points",0), "1h_reb": p1.get("rebounds",0), "1h_ast": p1.get("assists",0),
                "full_pts": pf.get("points",0), "full_reb": pf.get("rebounds",0), "full_ast": pf.get("assists",0),
                "2h_pts": pts_2h, "2h_reb": reb_2h, "2h_ast": ast_2h,
                "full_combo": full_combo, "2h_combo": actual_2h,
                "tc_proj_full": round(tc_proj_full, 2), "tc_proj_2h": round(tc_proj_2h, 2),
                "actual_2h_beat_line": hit_2h, "pre_game_pick_correct": full_correct,
            })
    if not rows:
        print("no rows — no Odds API combo lines found at halftime timestamp")
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_out = REPORTS / ("halftime_backtest_" + stamp + ".csv")
    with open(csv_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", csv_out, "rows:", len(rows))
    # summary
    h2_hr = round(100 * sum(1 for r in rows if r["actual_2h_beat_line"] == "True") / len(rows), 1)
    full_hr = round(100 * sum(1 for r in rows if r["pre_game_pick_correct"] == "True") / len(rows), 1)
    print("if you HAD bet at halftime using real DK lines: 2H actual beat line:", h2_hr + "%")
    print("if you bet pre-game using TC projection: full actual beat line:", full_hr + "%")
    # By sport
    by_sport = defaultdict(list)
    for r in rows: by_sport[r["sport"]].append(r)
    for sp, rs in by_sport.items():
        h2 = round(100 * sum(1 for r in rs if r["actual_2h_beat_line"] == "True") / len(rs), 1)
        fl = round(100 * sum(1 for r in rs if r["pre_game_pick_correct"] == "True") / len(rs), 1)
        print(" ", sp, "legs:", len(rs), "2H HR:", h2, "%  pre-game HR:", fl, "%")
    # By combo type
    by_ct = defaultdict(list)
    for r in rows: by_ct[r["combo_type"]].append(r)
    for ct, rs in by_ct.items():
        h2 = round(100 * sum(1 for r in rs if r["actual_2h_beat_line"] == "True") / len(rs), 1)
        fl = round(100 * sum(1 for r in rs if r["pre_game_pick_correct"] == "True") / len(rs), 1)
        print(" ", ct, "legs:", len(rs), "2H HR:", h2, "%  pre-game HR:", fl, "%")
    # 2H avg
    avg_2h_combo = sum(r["2h_combo"] for r in rows) / len(rows)
    avg_1h_combo = sum(r["1h_pts"]+r["1h_reb"]+r["1h_ast"] for r in rows) / len(rows)
    print(f"avg 1H total points+reb+ast per leg: {round(avg_1h_combo, 2)}")
    print(f"avg 2H total points+reb+ast per leg: {round(avg_2h_combo, 2)}")
    print(f"1H share of full game: {round(100*avg_1h_combo/(avg_1h_combo+avg_2h_combo), 1)}%")

if __name__ == "__main__":
    main()