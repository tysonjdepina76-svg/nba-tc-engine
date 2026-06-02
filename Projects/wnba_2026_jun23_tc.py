"""
WNBA TC Engine for Jun 2 & Jun 3, 2026.
Reads ESPN slates (saved), pulls rosters + 2026 season stats, applies 22-min starter
override, projects totals/sides/player props, writes CSV + JSON to Daily_Log.
"""
import csv, json, os, re, sys, time
import requests
from pathlib import Path
from datetime import datetime

ESPN_SCHED = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_ROSTER = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{tid}/roster"
ESPN_STATS  = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/wnba/athletes/{aid}/stats"
ESPN_TEAM_STATS = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/seasons/2026/teams/{tid}/statistics"

WORKSPACE = Path("/home/workspace")
LOG_DIR   = WORKSPACE / "Daily_Log"
SLATE_DIR = WORKSPACE / "data" / "wnba_slates"

UA = {"User-Agent": "Mozilla/5.0 (Zo TC Engine)"}

def http(url, retries=3, sleep=0.3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            if r.ok: return r
        except Exception as e:
            if i == retries-1: raise
        time.sleep(sleep)
    return r

def get_roster(tid):
    """Flat list of player dicts from ESPN roster endpoint."""
    r = http(ESPN_ROSTER.format(tid=tid))
    d = r.json()
    return d.get("athletes", []) or []

def get_season_stats(aid):
    """Return dict of 2026 averages, or None if not available."""
    r = http(ESPN_STATS.format(aid=aid))
    d = r.json()
    # ESPN 2026 labels: GP, GS, MIN, PTS, OR, DR, REB, AST, STL, BLK, TO, FG, FG%, 3PT, 3P%, FT, FT%, PF
    LBL = ["GP","GS","MIN","PTS","OR","DR","REB","AST","STL","BLK","TO","FG","FG%","3PT","3P%","FT","FT%","PF"]
    for cat in d.get("categories", []):
        if cat.get("name") != "averages": continue
        for row in cat.get("statistics", []):
            season = row.get("season", {})
            if season.get("year") != 2026: continue
            stats = row.get("stats", [])
            if len(stats) < len(LBL): continue
            def f(idx, default=0.0):
                v = stats[idx]
                if v in (None, "", "0.0-"): return default
                if isinstance(v, str) and "-" in v and v.replace("-","").replace(".","").isdigit():
                    return float(v.split("-")[0])
                try: return float(v)
                except: return default
            return {
                "gp": int(f(LBL.index("GP"), 0)),
                "gs": int(f(LBL.index("GS"), 0)),
                "min": f(LBL.index("MIN"), 0),
                "pts": f(LBL.index("PTS"), 0),
                "reb": f(LBL.index("REB"), 0),
                "ast": f(LBL.index("AST"), 0),
                "stl": f(LBL.index("STL"), 0),
                "blk": f(LBL.index("BLK"), 0),
                "3pm": f(LBL.index("3PT"), 0),
                "pf": f(LBL.index("PF"), 0),
            }
    return None

def tc_project(avg, role, starter_min=22, bench_min=14):
    """TC projection: scale season avg to target minutes.
    Use linear scale * role-efficiency factor (starters more efficient per min)."""
    if not avg: return None
    mins = starter_min if role == "START" else bench_min
    season_min = avg["min"] or 1.0
    scale = mins / season_min
    return {k: round(avg[k] * scale, 2) for k in ("pts","reb","ast","stl","blk","3pm")} | {
        "mins": mins, "scale": round(scale, 3)
    }

def role_of(avg):
    """Use GS to determine starter/bench (GS > 0 = START)."""
    return "START" if (avg and avg.get("gs", 0) > 0) else "BENCH"

def _ml_int(v):
    """ESPN ML comes as {'close':{'odds':'-1350'},'open':{'odds':'-1200'}} — return int."""
    if v is None: return None
    if isinstance(v, (int, float)): return int(v)
    if isinstance(v, dict):
        return _ml_int(v.get("close", {}).get("odds", None))
    return None

def parse_slate(filepath):
    """Parse a saved ESPN slate into a clean game dict."""
    with open(filepath) as f: data = json.load(f)
    games = []
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        away = comp["competitors"][0]["team"]
        home = comp["competitors"][1]["team"]
        # Odds (DraftKings)
        ml_home = ml_away = None
        spread_home = None
        ou_total = None
        for odd in comp.get("odds", []):
            if odd.get("provider", {}).get("id") != "100": continue  # DraftKings
            ou_total = odd.get("overUnder")
            sp = odd.get("spread")
            if sp is not None:
                # ESPN uses negative for home favorite, positive for home underdog
                # DK style: spread_home = -sp (if -14.5 means home favored by 14.5)
                spread_home = -float(sp)
            # Moneyline: ESPN structure for DK
            #   odd['awayTeamOdds']['moneyLine'] = {'close':{'odds':'+800'}, 'open':...}
            #   odd['homeTeamOdds']['moneyLine'] = {'close':{'odds':'-1350'}, 'open':...}
            ml_away = _ml_int(odd.get("awayTeamOdds", {}).get("moneyLine"))
            ml_home = _ml_int(odd.get("homeTeamOdds", {}).get("moneyLine"))
            if ml_away is None or ml_home is None:
                # Try flat shape
                ml_odds = odd.get("moneyline", {}) or {}
                if isinstance(ml_odds, dict):
                    ml_away = ml_away or _ml_int(ml_odds.get("away"))
                    ml_home = ml_home or _ml_int(ml_odds.get("home"))
            break
        games.append({
            "date": ev["date"],
            "name": ev["name"],
            "shortName": ev["shortName"],
            "away": {"id": away["id"], "abbr": away["abbreviation"], "name": away.get("displayName","")},
            "home": {"id": home["id"], "abbr": home["abbreviation"], "name": home.get("displayName","")},
            "ml_away": ml_away, "ml_home": ml_home,
            "spread_home": spread_home, "ou_total": ou_total,
        })
    return games

def main():
    all_props = []
    all_summaries = []
    for date in ["20260602", "20260603"]:
        slate_file = SLATE_DIR / f"espn_wnba_{date}.json"
        if not slate_file.exists():
            print(f"[{date}] slate not found, fetching live...")
            data = http(ESPN_SCHED, retries=2).json()
            slate_file.parent.mkdir(parents=True, exist_ok=True)
            slate_file.write_text(json.dumps(data, indent=2))
        games = parse_slate(slate_file)
        print(f"\n=== {date} | {len(games)} games ===")
        for g in games:
            print(f"\n  {g['shortName']}  ML H={g['ml_home']} A={g['ml_away']}  SpreadH={g['spread_home']}  O/U={g['ou_total']}")
            team_pts = {}
            team_roster_size = {}
            for side in ("away","home"):
                ros = get_roster(g[side]["id"])
                # Filter to rotation: players with GP>0 in 2026
                ros_avgs = []
                for p in ros:
                    name = p.get("fullName") or p.get("displayName") or "?"
                    aid = p.get("id")
                    avgs = get_season_stats(aid) if aid else None
                    if avgs and avgs["gp"] > 0:
                        ros_avgs.append((p, avgs))
                # Keep top 12 by minutes (real WNBA rotation per team)
                ros_avgs.sort(key=lambda x: x[1]["min"], reverse=True)
                ros_avgs = ros_avgs[:12]
                team_roster_size[side] = len(ros_avgs)
                side_pts = 0.0
                for p, avgs in ros_avgs:
                    name = p.get("fullName") or p.get("displayName") or "?"
                    role = role_of(avgs)
                    proj = tc_project(avgs, role)
                    if not proj: continue
                    side_pts += proj["pts"]
                    for stat_key, stat_name in [("pts","PTS"),("reb","REB"),("ast","AST"),("3pm","3PM"),("stl","STL"),("blk","BLK")]:
                        season_v = avgs[stat_key]
                        tc_v = proj[stat_key]
                        if season_v <= 0 or tc_v <= 0:
                            continue
                        line = round(season_v * 0.95, 1)
                        edge = round(tc_v - line, 2)
                        if abs(edge) < 0.5:
                            continue
                        all_props.append({
                            "date": f"2026-{date[4:6]}-{date[6:8]}",
                            "league": "WNBA",
                            "matchup": g["shortName"],
                            "team": g[side]["abbr"],
                            "player": name,
                            "role": role,
                            "stat": stat_name,
                            "season_avg": season_v,
                            "minutes_proj": proj["mins"],
                            "tc_projection": tc_v,
                            "market_line": line,
                            "edge": edge,
                            "side": "OVER" if edge > 0 else "UNDER",
                        })
                team_pts[side] = round(side_pts, 1)
            proj_total = round(team_pts["home"] + team_pts["away"], 1)
            ou = g["ou_total"] or 0
            ou_edge = round(proj_total - ou, 1)
            ou_pick = "OVER" if ou_edge >= 3.0 else "UNDER" if ou_edge <= -3.0 else "PASS"
            # Side pick via moneyline (TC's preferred side = the one with positive edge on ML)
            # Without a real ML projection, use spread direction as tiebreaker
            side_pick = "HOME" if (g["ml_home"] or 0) < (g["ml_away"] or 0) else "AWAY"
            summary = {
                "date": f"2026-{date[4:6]}-{date[6:8]}",
                "matchup": g["shortName"],
                "ml_home": g["ml_home"], "ml_away": g["ml_away"],
                "spread_home": g["spread_home"], "ou_total": ou,
                "proj_home": team_pts["home"], "proj_away": team_pts["away"],
                "proj_total": proj_total, "ou_edge": ou_edge, "ou_pick": ou_pick,
                "side_pick_ml": side_pick,
                "roster_away": team_roster_size["away"],
                "roster_home": team_roster_size["home"],
            }
            all_summaries.append(summary)
            print(f"  Proj HOME={team_pts['home']:.1f} + AWAY={team_pts['away']:.1f} = {proj_total:.1f}  vs O/U {ou}  edge {ou_edge:+.1f} → {ou_pick}")
    # Save
    out_dir = LOG_DIR / "2026-06-02"  # snapshot dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "wnba_jun23_slate.json").write_text(json.dumps({
        "summaries": all_summaries, "props_count": len(all_props),
        "timestamp": datetime.now().isoformat(),
    }, indent=2))
    if all_props:
        fields = list(all_props[0].keys())
        with open(out_dir / "wnba_jun23_player_props.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(all_props)
        (out_dir / "wnba_jun23_player_props.json").write_text(json.dumps(all_props, indent=2))
    # Print top plays
    print("\n" + "="*70)
    print("FINAL TOTALS PICKS (O/U edge >= 3.0)")
    print("="*70)
    for s in all_summaries:
        if s["ou_pick"] != "PASS":
            print(f"  {s['matchup']:<12}  Proj {s['proj_total']:5.1f}  vs O/U {s['ou_total']}  edge {s['ou_edge']:+.1f}  → {s['ou_pick']}")
    print("\nTOP 25 PROPS (by |edge|):")
    sorted_props = sorted(all_props, key=lambda p: abs(p["edge"]), reverse=True)[:25]
    for p in sorted_props:
        print(f"  {p['matchup']:<12} {p['player']:<22} {p['team']} {p['role'][:5]:<5} {p['stat']:<3} line={p['market_line']:>4} tc={p['tc_projection']:>4} edge={p['edge']:+.2f} → {p['side']}")
    print(f"\nSaved to: {out_dir}/wnba_jun23_player_props.csv ({len(all_props)} props)")
    print(f"          {out_dir}/wnba_jun23_slate.json")

if __name__ == "__main__":
    main()
