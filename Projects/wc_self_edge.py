#!/usr/bin/env python3
import json, csv, os, math, requests
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone

WORKSPACE = Path("/home/workspace")
BTEST_CSV = WORKSPACE / "Daily_Log" / "wc_player_stats_backtest.csv"
CACHE_DIR = WORKSPACE / "Daily_Log" / "cache" / "odds"
LOG_DIR = WORKSPACE / "Daily_Log" / "worldcup" / datetime.now(timezone.utc).strftime("%Y%m%d")
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

LINE_FACTOR = 0.88
EDGE_THRESH = 0.3
Q_FACTOR = 0.55

WC_WEIGHTS = {"goals": 0.85, "assists": 0.85, "shots": 0.80, "shots_on_target": 0.80,
              "tackles": 0.80, "fouls": 0.80, "cards": 0.75}
WC_GAPS = {"goals": 0.0, "assists": 0.1, "shots": 0.5, "shots_on_target": 0.2,
           "tackles": 0.5, "fouls": 0.5, "cards": 0.0}

def load_backtest_avgs():
    avgs = defaultdict(lambda: defaultdict(list))
    if not BTEST_CSV.exists():
        print(f"  No backtest CSV at {BTEST_CSV}")
        return {}
    with open(BTEST_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = (r.get("player_name","") or "").strip()
            team = (r.get("team_abbr","") or "").strip()
            if not name or not team:
                continue
            key = f"{name}|{team}"
            for stat in ["goals", "assists", "shots", "shots_on_target",
                         "fouls_committed", "yellow_cards", "red_cards"]:
                try:
                    v = float(r.get("total_goals" if stat=="goals" else
                                   "goal_assists" if stat=="assists" else
                                   "total_shots" if stat=="shots" else
                                   "shots_on_target" if stat=="shots_on_target" else
                                   "fouls_committed" if stat=="fouls_committed" else
                                   "yellow_cards" if stat=="yellow_cards" else
                                   "red_cards", "0") or "0")
                except (ValueError, TypeError):
                    v = 0.0
                avgs[key][stat].append(v)
    result = {}
    for key, stats in avgs.items():
        name, team = key.split("|", 1)
        avg_dict = {}
        for s, vals in stats.items():
            if vals:
                avg_dict[s] = round(sum(vals) / len(vals), 2)
        if avg_dict:
            result[(name.lower(), team)] = avg_dict
    print(f"  Backtest avgs: {len(result)} players")
    return result

def scrub_name(n):
    return " ".join(n.replace("\u00e9","e").replace("\u00e1","a")
                    .replace("\u00e3","a").replace("\u00ed","i")
                    .replace("\u00f3","o").replace("\u00fa","u")
                    .replace("\u00e7","c").replace("\u00f1","n").split()).lower().strip()

def get_wc_rosters():
    rosters = {}
    try:
        r = requests.get(ESPN_URL, timeout=15, params={"dates": datetime.now(timezone.utc).strftime("%Y%m%d")})
        r.raise_for_status()
        data = r.json()
        for e in data.get("events", []):
            comps = e.get("competitions", [])
            for c in comps:
                for co in c.get("competitors", []):
                    team = co.get("team", {})
                    tname = team.get("displayName", "")
                    tabbr = team.get("abbreviation", "")
                    homeaway = co.get("homeAway", "away")
                    tid = team.get("id", "")
                    players = []
                    for rgroup in co.get("roster", {}).get("entries", []):
                        pid = rgroup.get("playerId", "")
                        pname = rgroup.get("athlete", {}).get("displayName", "")
                        pos = rgroup.get("position", "").get("abbreviation", "")
                        if pname:
                            players.append({"name": pname, "id": pid, "pos": pos or "F"})
                    rosters[(tabbr, homeaway)] = {"name": tname, "players": players}
        print(f"  Rosters: {len(rosters)} teams")
    except Exception as exc:
        print(f"  ESPN roster error: {exc}")
    return rosters

def load_wc_cache_props():
    props = {}
    for fn in CACHE_DIR.glob("wc_*.json"):
        if fn.name == "wc_all.json":
            continue
        try:
            data = json.loads(fn.read_text())
            name = fn.stem.replace("wc_", "").replace("_"," @ ")
            bks = data.get("bookmakers", [])
            player_props = {}
            for bk in bks:
                for m in bk.get("markets", []):
                    mk = m.get("key", "")
                    stat = mk.replace("player_", "")
                    for o in m.get("outcomes", []):
                        pdesc = o.get("description", o.get("name", ""))
                        if o.get("name") == "Over" and o.get("point") is not None:
                            player_props.setdefault(pdesc, {})[stat] = o.get("point")
            if player_props:
                props[name] = player_props
        except Exception:
            pass
    print(f"  Cache props: {len(props)} games")
    return props

def project_wc(rosters, avgs, cache_props):
    all_props = []
    team_groups = defaultdict(list)
    for (tabbr, ha), tdata in rosters.items():
        team_groups.setdefault(tabbr, []).extend(tdata["players"])

    for (tabbr, _), tdata in rosters.items():
        for p in tdata["players"]:
            pname = p["name"]
            sk = scrub_name(pname)
            found_key = None
            for (bk, bt) in avgs:
                if scrub_name(bk) == sk:
                    found_key = (bk, bt)
                    break
            if not found_key:
                continue
            pdata = avgs[found_key]
            for stat_src, tc_stat in [("goals","goals"),("shots","shots"),
                                      ("shots_on_target","shots_on_target"),
                                      ("assists","assists")]:
                raw_avg = pdata.get(stat_src, 0)
                if raw_avg <= 0:
                    continue
                w = WC_WEIGHTS.get(tc_stat, 0.85)
                gap = WC_GAPS.get(tc_stat, 0)
                tc_val = round(raw_avg * w + gap, 2)
                if tc_val <= 0:
                    continue
                self_line = max(0, math.floor(tc_val * LINE_FACTOR))
                edge = round(tc_val - self_line, 2)
                direction = "OVER" if edge > 0 else "UNDER"
                signal = "PASS"
                if abs(edge) >= EDGE_THRESH:
                    signal = direction
                all_props.append({
                    "player": pname, "team": tabbr, "pos": p.get("pos","F"),
                    "stat": tc_stat, "market_line": float(self_line),
                    "tc_projection": tc_val, "edge": edge,
                    "direction": direction, "signal": signal,
                    "status": "ACTIVE", "source": "wc-self-edge",
                })

    for matchup, pprops in cache_props.items():
        for pname, stats in pprops.items():
            sp = scrub_name(pname)
            team_found = ""
            for (tabbr, _), tdata in rosters.items():
                for rp in tdata["players"]:
                    if scrub_name(rp["name"]) == sp:
                        team_found = tabbr
                        break
                if team_found:
                    break
            for stat, line_val in stats.items():
                stat_map = {"goals":"goals","assists":"assists","shots":"shots",
                           "shots_on_target":"shots_on_target"}
                tc_s = stat_map.get(stat, stat)
                tc_val = 0.0
                sn = scrub_name(pname)
                for (bk, bt), pd in avgs.items():
                    if scrub_name(bk) == sn:
                        raw_src = stat if stat in pd else None
                        if raw_src is None:
                            continue
                        raw_avg = pd.get(raw_src, 0)
                        if raw_avg > 0:
                            w = WC_WEIGHTS.get(tc_s, 0.85)
                            tc_val = round(raw_avg * w + WC_GAPS.get(tc_s, 0), 2)
                        break
                if tc_val <= 0:
                    tc_val = line_val * 0.9 if line_val else 0
                edge = round(tc_val - line_val, 2) if line_val else 0
                direction = "OVER" if edge > 0 else "UNDER"
                signal = "PASS"
                if abs(edge) >= 0.25:
                    signal = direction
                all_props.append({
                    "player": pname, "team": team_found, "pos": "F",
                    "stat": tc_s, "market_line": line_val,
                    "tc_projection": tc_val, "edge": edge,
                    "direction": direction, "signal": signal,
                    "status": "ACTIVE", "source": "wc-cache-props",
                })

    return sorted(all_props, key=lambda x: abs(x["edge"]), reverse=True)

def run():
    print("=== World Cup Self-Edge ===")
    avgs = load_backtest_avgs()
    rosters = get_wc_rosters()
    cache_props = load_wc_cache_props()
    props = project_wc(rosters, avgs, cache_props)
    print(f"Total props: {len(props)}")
    srcs = Counter(p["source"] for p in props)
    print(f"Sources: {dict(srcs)}")
    signals = Counter(p["signal"] for p in props)
    print(f"Signals: {dict(signals)}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "props.json", "w") as f:
        json.dump(props, f, indent=2, default=str)
    with open(LOG_DIR / "picks.csv", "w", newline="") as f:
        if props:
            w = csv.DictWriter(f, fieldnames=props[0].keys())
            w.writeheader()
            w.writerows(props)
    with open(WORKSPACE / "Daily_Log" / "worldcup" / "last_run.json", "w") as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(),
                   "total_props": len(props), "sources": dict(srcs),
                   "signals": dict(signals)}, f, indent=2)
    return props

if __name__ == "__main__":
    run()
