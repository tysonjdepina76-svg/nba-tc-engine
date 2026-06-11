#!/usr/bin/env python3
"""Boxscore combo backtest with REAL historical DK lines from The Odds API."""
import json, re, sys, time
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import requests

WORKSPACE = Path("/home/workspace")
REPORTS = WORKSPACE / "Reports"
REPORTS.mkdir(parents=True, exist_ok=True)
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
OUT_MD = REPORTS / ("boxscore_combo_backtest_" + STAMP + ".md")

ODDS_BASE = "https://api.the-odds-api.com/v4"
LEAGUE_ESPN = {"NBA": "basketball/nba", "WNBA": "basketball/wnba"}
ODDS_SPORT = {"NBA": "basketball_nba", "WNBA": "basketball_wnba"}
MARKET_TO_TYPE = {
    "player_points_rebounds_assists": "PRA",
    "player_points_rebounds": "PR",
    "player_points_assists": "PA",
}


def load_key(name):
    p = Path("/root/.zo/secrets.env")
    if not p.exists():
        return ""
    for line in p.read_text().splitlines():
        m = re.match(r"^\s*" + re.escape(name) + r"\s*=\s*[\"']?([^\"'\s#]+)", line)
        if m:
            return m.group(1)
    return ""


ODDS_KEY = load_key("ODDS_API_KEY")


def get(url, params):
    r = requests.get(url, params=params, timeout=20)
    if r.status_code == 422 and "INVALID_MARKET" in r.text:
        return {"_err": "market_not_supported", "_status": 422}
    if r.status_code != 200:
        return {"_err": "http_" + str(r.status_code), "_body": r.text[:200]}
    return r.json()


def list_completed(sport, days_back=3):
    """Return [(eid, label, commence_iso)] for every final game in last N days."""
    out = []
    today = datetime.utcnow().date()
    for offset in range(days_back):
        date = today - timedelta(days=offset)
        ds = date.strftime("%Y%m%d")
        js = get(
            "https://site.api.espn.com/apis/site/v2/sports/" + LEAGUE_ESPN[sport] + "/scoreboard",
            {"dates": ds},
        )
        if "_err" in js:
            continue
        for ev in js.get("events", []):
            comp = ev.get("competitions", [{}])[0]
            state = comp.get("status", {}).get("type", {}).get("state", "")
            if state != "post":
                continue
            home = next((c["team"]["abbreviation"] for c in comp.get("competitors", []) if c.get("homeAway") == "home"), "?")
            away = next((c["team"]["abbreviation"] for c in comp.get("competitors", []) if c.get("homeAway") == "away"), "?")
            out.append((ev["id"], away + "@" + home, ev.get("date", ""), sport))
    return out


def normalize_name(s):
    """Lowercase, strip suffixes, collapse whitespace for fuzzy player matching."""
    if not s:
        return ""
    s = s.lower().strip()
    # strip common suffixes
    for suf in (" jr.", " jr", " iii", " ii", " iv"):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    return s

# in-memory team name map (Odds API full name -> ESPN abbreviation)
ODDS_TO_ESPN = {
    "Atlanta Dream": "ATL", "Chicago Sky": "CHI", "Connecticut Sun": "CON",
    "Dallas Wings": "DAL", "Indiana Fever": "IND", "Las Vegas Aces": "LV",
    "Los Angeles Sparks": "LA", "Minnesota Lynx": "MIN", "New York Liberty": "NY",
    "Phoenix Mercury": "PHX", "Seattle Storm": "SEA", "Washington Mystics": "WSH",
    "Golden State Valkyries": "GS", "Toronto Tempo": "TOR", "Portland Fire": "POR",
    # NBA
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


def fetch_historical_events(sport, date_str):
    """date_str is YYYY-MM-DD (ET game date). Returns list of (hash, away_abbr, home_abbr) for a given date.
    We query the 6am UTC of that day so we get the pre-tip snapshot for any game that day.
    """
    r = requests.get(
        "https://api.the-odds-api.com/v4/historical/sports/" + ODDS_SPORT[sport] + "/events",
        params={"apiKey": ODDS_KEY, "date": date_str + "T06:00:00Z"},
        timeout=20,
    )
    if r.status_code != 200:
        return []
    d = r.json()
    out = []
    for e in d.get("data", []):
        away = ODDS_TO_ESPN.get(e.get("away_team", ""), "")
        home = ODDS_TO_ESPN.get(e.get("home_team", ""), "")
        if not away or not home:
            continue
        out.append((e["id"], away, home))
    return out


def fetch_historical_event_odds_by_hash(sport, hash_id, snapshot_iso):
    """Fetch historical odds for a hash event id at a given snapshot time."""
    r = requests.get(
        "https://api.the-odds-api.com/v4/historical/sports/" + ODDS_SPORT[sport] + "/events/" + hash_id + "/odds",
        params={
            "apiKey": ODDS_KEY,
            "regions": "us",
            "markets": "player_points_rebounds_assists,player_points_rebounds,player_points_assists",
            "oddsFormat": "american",
            "date": snapshot_iso,
            "bookmakers": "draftkings",
        },
        timeout=20,
    )
    if r.status_code != 200:
        return None
    return r.json().get("data", {})


def fetch_historical_event_odds(sport, eid, commence_iso):
    """Pull the snapshot of DK lines at game-tip time for a completed event."""
    if not commence_iso:
        return None
    commence_iso = commence_iso.replace("Z", "+00:00")
    js = get(
        ODDS_BASE + "/historical/sports/" + ODDS_SPORT[sport] + "/events/" + event_id + "/odds",
        {
            "apiKey": ODDS_KEY,
            "regions": "us",
            "markets": "player_points_rebounds_assists,player_points_rebounds,player_points_assists",
            "oddsFormat": "american",
            "date": commence_iso,
            "bookmakers": "draftkings",
        },
    )
    if "_err" in js:
        return None
    return js.get("data", {})


def extract_combo_lines(odds_data):
    """Yield (player, ctype, line, side, price) for every Over+Under line."""
    if not odds_data:
        return
    for bk in odds_data.get("bookmakers", []):
        if bk.get("key") != "draftkings":
            continue
        for mkt in bk.get("markets", []):
            ctype = MARKET_TO_TYPE.get(mkt["key"])
            if not ctype:
                continue
            by_line = defaultdict(dict)
            for o in mkt.get("outcomes", []):
                pt = o.get("point")
                if pt is None:
                    continue
                by_line[float(pt)][o["name"]] = (o.get("description", "?"), o.get("price"))
            for line, sides in by_line.items():
                over = sides.get("Over")
                under = sides.get("Under")
                if over:
                    yield (over[0], ctype, line, "Over", over[1])
                if under:
                    yield (under[0], ctype, line, "Under", under[1])


def fetch_boxscore(sport, eid):
    """Return dict: normalize_name -> {name, pts, reb, ast, team}."""
    js = get(
        "https://site.api.espn.com/apis/site/v2/sports/" + LEAGUE_ESPN[sport] + "/summary",
        {"event": eid},
    )
    if "_err" in js:
        return {}
    out = {}
    for player_grp in js.get("boxscore", {}).get("players", []):
        team_abbr = player_grp.get("team", {}).get("abbreviation", "?")
        for stat_grp in player_grp.get("statistics", []):
            keys = stat_grp.get("keys", [])
            try:
                i_pts = keys.index("points")
                i_reb = keys.index("rebounds")
                i_ast = keys.index("assists")
            except ValueError:
                continue
            for ath in stat_grp.get("athletes", []):
                a = ath.get("athlete", {}) or {}
                stats = ath.get("stats", []) or []
                if len(stats) <= max(i_pts, i_reb, i_ast):
                    continue

                def to_int(s):
                    try:
                        return int(s)
                    except (ValueError, TypeError):
                        return 0

                pts, reb, ast = to_int(stats[i_pts]), to_int(stats[i_reb]), to_int(stats[i_ast])
                if ath.get("didNotPlay") or ath.get("active") is False:
                    continue
                nm = a.get("displayName", "?")
                out[nm.lower().strip()] = {"name": nm, "pts": pts, "reb": reb, "ast": ast, "team": team_abbr}
    return out


def grade(player_lower, ctype, line, side, actuals_idx):
    a = actuals_idx.get(player_lower)
    if not a:
        return None
    p, r, s = a["pts"], a["reb"], a["ast"]
    actual = (p + r + s) if ctype == "PRA" else ((p + r) if ctype == "PR" else (p + s))
    if side == "Over":
        hit = actual > line
    else:
        hit = actual < line
    return {"actual": actual, "hit": hit, "margin": actual - line, "name": a["name"], "team": a["team"]}


EVENTS_BY_DATE = {}  # cache: (sport, date_str) -> [(hash, away_abbr, home_abbr)]

def get_odds_hash_for_game(sport, date_str, away_abbr, home_abbr):
    """Look up the Odds API hash event id for a given ESPN game."""
    key = (sport, date_str)
    if key not in EVENTS_BY_DATE:
        EVENTS_BY_DATE[key] = fetch_historical_events(sport, date_str)
    for h, a, h_ in EVENTS_BY_DATE[key]:
        if a == away_abbr and h_ == home_abbr:
            return h
    return None


def run():
    rows = []
    games_with_odds = 0
    for sport in ("WNBA", "NBA"):
        events = list_completed(sport, days_back=3)
        print("[" + sport + "] " + str(len(events)) + " completed events")
        for eid, label, commence, sp in events:
            # parse date from commence "2026-06-09T23:00Z" or full iso
            date_str = commence[:10]  # YYYY-MM-DD
            away_abbr = label.split("@")[0]
            home_abbr = label.split("@")[1]
            actuals = fetch_boxscore(sp, eid)
            if not actuals:
                print("  skip " + label + " (no boxscore)")
                continue
            hash_id = get_odds_hash_for_game(sp, date_str, away_abbr, home_abbr)
            if not hash_id:
                print("  skip " + label + " (no hash match)")
                continue
            # snapshot 30 min before commence
            from datetime import datetime, timezone, timedelta
            try:
                c = datetime.fromisoformat(commence.replace("Z", "+00:00"))
            except Exception:
                c = datetime.fromisoformat(commence[:19])
            snap = (c - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            odds_data = fetch_historical_event_odds_by_hash(sp, hash_id, snap)
            if not odds_data or "bookmakers" not in odds_data:
                print("  skip " + label + " (no historical odds at " + snap + ")")
                continue
            games_with_odds += 1
            n_lines = 0
            for player, ctype, line, side, price in extract_combo_lines(odds_data):
                g = grade(normalize_name(player), ctype, line, side, actuals)
                if not g:
                    continue
                n_lines += 1
                rows.append({
                    "sport": sp,
                    "game": label,
                    "player": g["name"],
                    "team": g["team"],
                    "combo_type": ctype,
                    "side": side,
                    "line": line,
                    "price": price,
                    "actual": g["actual"],
                    "hit": g["hit"],
                    "margin": g["margin"],
                })
            print("  " + label + ": " + str(n_lines) + " legs graded")
    print("games with real historical odds:", games_with_odds)
    return rows


def render_md(rows):
    by_sport = defaultdict(list)
    by_type = defaultdict(list)
    by_side = defaultdict(list)
    by_game = defaultdict(list)
    for r in rows:
        by_sport[r["sport"]].append(r)
        by_type[r["combo_type"]].append(r)
        by_side[r["side"]].append(r)
        by_game[r["game"]].append(r)
    total = len(rows)
    hits = sum(1 for r in rows if r["hit"])
    out = []
    out.append("# Boxscore Combo Backtest (REAL Historical DK Lines)")
    out.append("")
    out.append("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ET")
    out.append("")
    out.append("Source: The Odds API **historical** endpoint `/v4/historical/sports/{sport}/events/{eid}/odds?date={commence_time}`")
    out.append("Graded against ESPN final box scores (last 3 days).")
    out.append("")
    out.append("**Methodology**: For every completed NBA/WNBA game, pull the snapshot of")
    out.append("DraftKings combo props (PRA/PR/PA) at game-tip time, then grade each side")
    out.append("(Over + Under) against the player's actual box-score combination. This is")
    out.append("a REAL backtest using actual closing lines (not reconstructed).")
    out.append("")
    out.append("## Overall")
    out.append("")
    out.append("- Games with real closing lines: " + str(len(set(r["game"] for r in rows))))
    out.append("- Total legs graded: " + str(total))
    out.append("- Hits: " + str(hits))
    out.append("- Misses: " + str(total - hits))
    out.append("- Hit rate: " + str(round(100.0 * hits / total, 1) if total else 0) + "%")
    out.append("")
    out.append("## By sport")
    out.append("")
    out.append("| sport | games | legs | hits | HR |")
    out.append("|-------|-------|------|------|----|")
    for sp, rs in sorted(by_sport.items()):
        h = sum(1 for r in rs if r["hit"])
        out.append("| " + sp + " | " + str(len(set(r["game"] for r in rs))) + " | " + str(len(rs)) + " | " + str(h) + " | " + str(round(100.0 * h / len(rs), 1)) + "% |")
    out.append("")
    out.append("## By side")
    out.append("")
    out.append("| side | legs | hits | HR |")
    out.append("|------|------|------|----|")
    for s, rs in sorted(by_side.items()):
        h = sum(1 for r in rs if r["hit"])
        out.append("| " + s + " | " + str(len(rs)) + " | " + str(h) + " | " + str(round(100.0 * h / len(rs), 1)) + "% |")
    out.append("")
    out.append("## By combo type")
    out.append("")
    out.append("| type | legs | hits | HR |")
    out.append("|------|------|------|----|")
    for ct, rs in sorted(by_type.items()):
        h = sum(1 for r in rs if r["hit"])
        out.append("| " + ct + " | " + str(len(rs)) + " | " + str(h) + " | " + str(round(100.0 * h / len(rs), 1)) + "% |")
    out.append("")
    out.append("## By game")
    out.append("")
    for g, rs in sorted(by_game.items()):
        h = sum(1 for r in rs if r["hit"])
        out.append("### " + g + " - " + str(h) + "/" + str(len(rs)) + " (" + str(round(100.0 * h / len(rs), 1)) + "%)")
        out.append("")
        out.append("| player | team | type | side | line | price | actual | result |")
        out.append("|--------|------|------|------|------|-------|--------|--------|")
        for r in sorted(rs, key=lambda x: (x["combo_type"], x["side"], x["player"])):
            mark = "HIT" if r["hit"] else "miss"
            out.append("| " + r["player"] + " | " + r["team"] + " | " + r["combo_type"] + " | " + r["side"] + " | " + str(r["line"]) + " | " + str(r["price"]) + " | " + str(r["actual"]) + " | " + mark + " |")
        out.append("")
    return "\n".join(out)


def main():
    rows = run()
    md = render_md(rows)
    OUT_MD.write_text(md)
    csv = OUT_MD.with_suffix(".csv")
    if rows:
        cols = list(rows[0].keys())
        with csv.open("w") as f:
            f.write(",".join(cols) + "\n")
            for r in rows:
                f.write(",".join(str(r.get(c, "")) for c in cols) + "\n")
    print("wrote", OUT_MD, "rows:", len(rows))


if __name__ == "__main__":
    main()
