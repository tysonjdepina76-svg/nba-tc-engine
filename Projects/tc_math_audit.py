import json, csv, sys, re, requests
sys.path.insert(0, "/home/workspace/Projects")
from pathlib import Path
from tc_math import project_pra, project_pr, project_pa, line_from_tc

KEY = ""
for line in Path("/root/.zo/secrets.env").read_text().splitlines():
    m = re.match(r"^\s*ODDS_API_KEY\s*=\s*[\"']?([^\"'\s#]+)", line)
    if m: KEY = m.group(1)

# Load the backtest CSV (real DK lines + actuals)
rows = list(csv.DictReader(open("/home/workspace/Reports/boxscore_combo_backtest_20260610_2255.csv")))

# We need per-player PTS/REB/AST splits, but the backtest CSV only has the combo total.
# So fetch boxscore for each game.
LEAGUE_ESPN = {"NBA": "basketball/nba", "WNBA": "basketball/wnba"}

# Map backtest game labels to ESPN event ids
def get_event_id_for_game(sport, game_label, commence_date):
    # game_label is "AWAY@HOME"; we have to re-find from scoreboard by date
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/" + LEAGUE_ESPN[sport] + "/scoreboard", params={"dates": commence_date}, timeout=15)
    if r.status_code != 200: return None
    away_abbr, home_abbr = game_label.split("@")
    for ev in r.json().get("events", []):
        comp = ev.get("competitions", [{}])[0]
        state = comp.get("status", {}).get("type", {}).get("state", "")
        if state != "post": continue
        home = next((c["team"]["abbreviation"] for c in comp.get("competitors", []) if c.get("homeAway") == "home"), "?")
        away = next((c["team"]["abbreviation"] for c in comp.get("competitors", []) if c.get("homeAway") == "away"), "?")
        if away == away_abbr and home == home_abbr:
            return ev["id"]
    return None

def find_event_id_any_date(sport, abbrs):
    """Look up the ESPN event"""
    pass

def fetch_splits(sport, event_id):
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/" + LEAGUE_ESPN[sport] + "/summary", params={"event": event_id}, timeout=15)
    if r.status_code != 200: return {}
    d = r.json()
    out = {}
    for player_grp in d.get("boxscore", {}).get("players", []):
        for stat_grp in player_grp.get("statistics", []):
            keys = stat_grp.get("keys", [])
            if "points" not in keys: continue
            i_pts = keys.index("points")
            i_reb = keys.index("rebounds") if "rebounds" in keys else -1
            i_ast = keys.index("assists") if "assists" in keys else -1
            for ath in stat_grp.get("athletes", []):
                a = ath.get("athlete", {})
                stats = ath.get("stats", [])
                if len(stats) <= max(i_pts, i_reb, i_ast): continue
                try:
                    pts = int(stats[i_pts]) if i_pts >= 0 else 0
                    reb = int(stats[i_reb]) if i_reb >= 0 and i_reb < len(stats) else 0
                    ast = int(stats[i_ast]) if i_ast >= 0 and i_ast < len(stats) else 0
                except (ValueError, TypeError): continue
                nm = a.get("displayName", "")
                if not nm: continue
                out[nm.lower().strip()] = {"name": nm, "pts": pts, "reb": reb, "ast": ast}
    return out

# Group by game
by_game = {}
for r in rows:
    by_game.setdefault(r["game"], []).append(r)

# Use the first row in each group to get sport+date
audit_rows = []
for game, rs in by_game.items():
    sample = rs[0]
    sport = sample["sport"]
    # The commence date - we know the games are from 2026-06-09, 06-10
    # Use the first row's game label + just scan both dates
    splits = None
    for d in ("20260609", "20260610"):
        eid = get_event_id_for_game(sport, game, d)
        if eid:
            s = fetch_splits(sport, eid)
            if s: splits = s; break
    if not splits:
        print("no splits for", game); continue
    for r in rs:
        p = r["player"].lower().strip()
        s = splits.get(p)
        if not s: continue
        # Build TC projection using current actual as the sample mean (rough proxy for rolling avg)
        raw_pts, raw_reb, raw_ast = s["pts"], s["reb"], s["ast"]
        # Use n_games=1 because we only have 1 game's worth of data
        tc_pra = project_pra(raw_pts, raw_reb, raw_ast, "ACTIVE", sport)
        tc_pr = project_pr(raw_pts, raw_reb, "ACTIVE", sport)
        tc_pa = project_pa(raw_pts, raw_ast, "ACTIVE", sport)
        tc_by_type = {"PRA": tc_pra, "PR": tc_pr, "PA": tc_pa}
        ctype = r["combo_type"]
        dk_line = float(r["line"])
        side = r["side"]
        tc_proj = tc_by_type[ctype]
        # TC recommends betting the side that agrees with our projection vs DK line
        tc_pick = "Over" if tc_proj > dk_line else "Under"
        # Did the TC pick win?
        hit = (tc_pick == side and r["hit"] == "True")
        audit_rows.append({
            "sport": sport, "game": game, "player": r["player"], "combo_type": ctype,
            "dk_line": dk_line, "side": side, "tc_pick": tc_pick,
            "actual": float(r["actual"]), "tc_proj": tc_proj,
            "tc_correct": hit,
        })

# Aggregate
from collections import Counter
total = len(audit_rows)
correct = sum(1 for r in audit_rows if r["tc_correct"])
print("=" * 60)
print("TC MATH AUDIT")
print("=" * 60)
print("Total legs audited:", total)
print("TC pick correct:    ", correct, "(", round(100*correct/total, 1), "%)")
print()
print("By combo type:")
by_type = Counter(r["combo_type"] for r in audit_rows)
for ct, n in sorted(by_type.items()):
    sub = [r for r in audit_rows if r["combo_type"] == ct]
    c = sum(1 for r in sub if r["tc_correct"])
    print("  ", ct, ":", c, "/", n, "=", round(100*c/n, 1), "%")
print()
print("By sport:")
by_sp = Counter(r["sport"] for r in audit_rows)
for sp, n in sorted(by_sp.items()):
    sub = [r for r in audit_rows if r["sport"] == sp]
    c = sum(1 for r in sub if r["tc_correct"])
    print("  ", sp, ":", c, "/", n, "=", round(100*c/n, 1), "%")
print()
print("By TC pick direction:")
by_pick = Counter(r["tc_pick"] for r in audit_rows)
for p, n in sorted(by_pick.items()):
    sub = [r for r in audit_rows if r["tc_pick"] == p]
    c = sum(1 for r in sub if r["tc_correct"])
    print("  TC picked", p, ":", c, "/", n, "=", round(100*c/n, 1), "%")

# Save detailed CSV
import csv as _csv
out_path = "/home/workspace/Reports/tc_math_audit_20260610_2257.csv"
with open(out_path, "w", newline="") as f:
    w = _csv.DictWriter(f, fieldnames=["sport","game","player","combo_type","dk_line","side","tc_pick","actual","tc_proj","tc_correct"])
    w.writeheader()
    for r in audit_rows: w.writerow(r)
print("\nWrote", out_path)
