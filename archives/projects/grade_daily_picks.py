#!/usr/bin/env python3
"""
Grade pending picks by joining against saved boxscores.
- Player props: join on matchup + player + stat
- Game totals: sum team scores in boxscore
"""
import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path

LOG = Path("/home/workspace/Daily_Log")
FINAL = LOG / "final"
MLB_DIR = LOG / "mlb_boxscores"
WC_DIR = LOG / "wc_boxscores"
OUT_DIR = LOG  # write graded_picks.csv into each date folder

STAT_MAP = {
    "PTS": "pts", "REB": "reb", "AST": "ast", "STL": "stl", "BLK": "blk",
    "3PM": "fg3m", "TO": "to", "PF": "pf", "OREB": "oreb", "DREB": "dreb",
    "MIN": "minutes",
    "HITS": "h", "RUNS": "r", "RBI": "rbi", "HR": "hr",
    "EARNED_RUNS": "er", "HITS_ALLOWED": "h", "STRIKEOUTS": "so",
}

# --- Team name normalization (boxscores use full names, picks use abbrevs) ---
TEAM_ABBREV = {
    "WNBA": {
        "Las Vegas Aces": "LV", "Aces": "LV",
        "New York Liberty": "NY", "Liberty": "NY",
        "Minnesota Lynx": "MIN", "Lynx": "MIN",
        "Connecticut Sun": "CON", "Sun": "CON",
        "Seattle Storm": "SEA", "Storm": "SEA",
        "Phoenix Mercury": "PHX", "Mercury": "PHX",
        "Chicago Sky": "CHI", "Sky": "CHI",
        "Atlanta Dream": "ATL", "Dream": "ATL",
        "Indiana Fever": "IND", "Fever": "IND",
        "Washington Mystics": "WSH", "Mystics": "WSH",
        "Dallas Wings": "DAL", "Wings": "DAL",
        "Los Angeles Sparks": "LA", "Sparks": "LA",
        "Golden State Valkyries": "GSV", "Valkyries": "GSV",
        "Toronto Tempo": "TOR", "Tempo": "TOR",
        "Portland Fire": "POR", "Fire": "POR",
    },
    "MLB": {
        "Arizona Diamondbacks": "ARI", "D-backs": "ARI",
        "Atlanta Braves": "ATL", "Braves": "ATL",
        "Baltimore Orioles": "BAL", "Orioles": "BAL",
        "Boston Red Sox": "BOS", "Red Sox": "BOS",
        "Chicago Cubs": "CHC", "Cubs": "CHC",
        "Chicago White Sox": "CHW", "White Sox": "CHW",
        "Cincinnati Reds": "CIN", "Reds": "CIN",
        "Cleveland Guardians": "CLE", "Guardians": "CLE",
        "Colorado Rockies": "COL", "Rockies": "COL",
        "Detroit Tigers": "DET", "Tigers": "DET",
        "Houston Astros": "HOU", "Astros": "HOU",
        "Kansas City Royals": "KC", "Royals": "KC",
        "Los Angeles Angels": "LAA", "Angels": "LAA",
        "Los Angeles Dodgers": "LAD", "Dodgers": "LAD",
        "Miami Marlins": "MIA", "Marlins": "MIA",
        "Milwaukee Brewers": "MIL", "Brewers": "MIL",
        "Minnesota Twins": "MIN", "Twins": "MIN",
        "New York Mets": "NYM", "Mets": "NYM",
        "New York Yankees": "NYY", "Yankees": "NYY",
        "Oakland Athletics": "OAK", "Athletics": "OAK",
        "Philadelphia Phillies": "PHI", "Phillies": "PHI",
        "Pittsburgh Pirates": "PIT", "Pirates": "PIT",
        "San Diego Padres": "SD", "Padres": "SD",
        "San Francisco Giants": "SF", "Giants": "SF",
        "Seattle Mariners": "SEA", "Mariners": "SEA",
        "St. Louis Cardinals": "STL", "Cardinals": "STL",
        "Tampa Bay Rays": "TB", "Rays": "TB",
        "Texas Rangers": "TEX", "Rangers": "TEX",
        "Toronto Blue Jays": "TOR", "Blue Jays": "TOR",
    },
    "WORLD_CUP": {},
}

ABBREV_TO_TEAM = {}
for sport, m in TEAM_ABBREV.items():
    for full, ab in m.items():
        ABBREV_TO_TEAM[(sport, ab)] = full


def load_boxscores():
    """Index all final boxscores by (sport, abbrev_matchup) -> boxscore dict.
    Loads from final/ (WNBA), mlb_boxscores/ (MLB), wc_boxscores/ (World Cup).
    """
    idx = {}
    sources = [
        (FINAL, None, lambda name: name),  # WNBA — sport comes from JSON
        (MLB_DIR, "MLB", None),            # MLB — sport from filename
        (WC_DIR, "WORLD_CUP", None),       # WC — sport from filename
    ]
    for source_dir, force_sport, _ in sources:
        if not source_dir.exists():
            continue
        for f in source_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    bs = json.load(fp)
            except Exception:
                continue
            if force_sport:
                sport = force_sport
            else:
                raw = bs.get("sport", "")
                sport = "WORLD_CUP" if raw == "soccer" else raw
            bs = normalize_boxscore(bs, sport)
            ev = bs.get("event_id", "")
            teams = set()
            for p in bs.get("players", {}).values():
                t = p.get("team", "")
                if t:
                    teams.add(t)
            if len(teams) < 2:
                continue
            ts = sorted(teams)
            abbrevs = []
            for t in ts:
                ab = None
                for full, a in TEAM_ABBREV.get(sport, {}).items():
                    if full == t:
                        ab = a
                        break
                abbrevs.append(ab or t)
            key = (sport, "@".join(abbrevs))
            idx[key] = bs
            idx[(sport, f"{abbrevs[1]}@{abbrevs[0]}")] = bs
            if ev:
                idx[(sport, f"ev:{ev}")] = bs
    return idx


def normalize_boxscore(bs, sport):
    """Convert sport-specific boxscore shapes to the unified {players: {name: {team, stat}}} form.

    MLB boxscores have separate batting/pitching dicts keyed by player name.
    World Cup has scorer/lineup shapes depending on capture path.
    WNBA already uses the players form.
    """
    if sport != "MLB":
        return bs
    if "players" in bs:
        return bs
    players = {}
    for src in (bs.get("batting", {}), bs.get("pitching", {})):
        for name, p in src.items():
            entry = players.setdefault(name, {"name": name, "team": p.get("team", "")})
            entry["team"] = entry.get("team") or p.get("team", "")
            for k, v in p.items():
                if k not in ("name", "team"):
                    entry[k] = v
    bs["players"] = players
    return bs


def grade_match(pick, boxscore):
    """Return actual value or None."""
    stat = pick.get("stat", "").upper()
    player = pick.get("player", "")
    team = pick.get("team", "")

    if stat == "TOTAL" or player == "TOTAL" or player == "GAME":
        # Sum team points for game total
        away = pick["matchup"].split("@")[0]
        home = pick["matchup"].split("@")[1]
        total = 0
        for p in boxscore.get("players", {}).values():
            if p.get("team", "") in (ABBREV_TO_TEAM.get((pick["league"], away), away),
                                      ABBREV_TO_TEAM.get((pick["league"], home), home)):
                total += int(p.get("pts", 0) or 0)
        return total if total > 0 else None

    if not player:
        return None

    # Find player in boxscore
    players = boxscore.get("players", {})
    target = None
    name_l = player.lower().strip()
    for pn, pd in players.items():
        if pn.lower().strip() == name_l:
            target = pd
            break
    if not target:
        # try last name
        last = name_l.split()[-1]
        for pn, pd in players.items():
            if pd.get("name", "").lower().split()[-1] == last and pd.get("team", "") == team:
                # confirm by full name
                pass
            elif pd.get("name", "").lower().split()[-1] == last:
                target = pd
                break
    if not target:
        return None

    # Map stat
    key = STAT_MAP.get(stat)
    if not key and stat != "TOTAL_BASES":
        return None
    # For pitcher stats (EARNED_RUNS, HITS_ALLOWED, STRIKEOUTS), look in pitching
    pitcher_stats = {"EARNED_RUNS", "HITS_ALLOWED", "STRIKEOUTS"}
    if stat in pitcher_stats:
        pitching = boxscore.get("pitching", {})
        for name, p in pitching.items():
            if name.lower() == player.lower() or name.lower().split()[-1] == player.lower().split()[-1]:
                val = p.get(key)
                if val is None: return None
                try: return float(val)
                except: return None
        return None
    val = target.get(key) if key else None
    if stat == "TOTAL_BASES":
        # Boxscore only has h and hr (no 2b/3b). Use h + 2*hr as conservative estimate.
        h = target.get("h") or 0
        hr = target.get("hr") or 0
        try: return float(h) + 2 * float(hr)
        except: return None
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def grade_pick(pick, actual):
    """Return 'H' hit, 'M' miss, or None."""
    if actual is None:
        return None
    direction = pick.get("direction", "").upper()
    line = pick.get("market_line", "")
    if line == "" or line is None:
        return None
    try:
        line = float(line)
    except Exception:
        return None
    if direction == "FLAT":
        return None  # No O/U target — can't grade
    if direction == "OVER":
        return "H" if actual > line else "M"
    if direction == "UNDER":
        return "H" if actual < line else "M"
    return None


def grade_date(date_str, box_idx):
    pdir = LOG / date_str
    pcsv = pdir / "picks.csv"
    if not pcsv.exists():
        return None, 0, 0
    picks = []
    with open(pcsv) as f:
        r = csv.DictReader(f)
        for row in r:
            picks.append(row)
    if not picks:
        return None, 0, 0
    graded = []
    hits = 0
    misses = 0
    pending = 0
    for p in picks:
        if p.get("result") not in (None, "", "PENDING"):
            graded.append(p)
            continue
        league = p.get("league", "")
        matchup = p.get("matchup", "")
        bs = box_idx.get((league, matchup))
        if not bs:
            pending += 1
            graded.append(p)
            continue
        actual = grade_match(p, bs)
        if actual is None:
            pending += 1
            graded.append(p)
            continue
        res = grade_pick(p, actual)
        p["actual"] = str(actual)
        if res is None:
            p["result"] = "PENDING"
            pending += 1
        else:
            p["result"] = res
            if res == "H":
                hits += 1
            else:
                misses += 1
        graded.append(p)
    # Write
    out = pdir / "graded_picks.csv"
    with open(out, "w", newline="") as f:
        if graded:
            w = csv.DictWriter(f, fieldnames=graded[0].keys())
            w.writeheader()
            w.writerows(graded)
    return (hits, misses), len(graded), pending


def main():
    box_idx = load_boxscores()
    print(f"Loaded {len(box_idx)} boxscore keys")
    total_h = total_m = total_graded = total_pending = 0
    for d in sorted(LOG.iterdir()):
        if not d.is_dir() or not re.match(r"\d{4}-\d{2}-\d{2}$", d.name):
            continue
        result, g, p = grade_date(d.name, box_idx)
        if g == 0:
            print(f"{d.name}: no picks")
            continue
        if result is None:
            print(f"{d.name}: {g} picks (already graded)")
            continue
        h, m = result
        total_h += h
        total_m += m
        total_graded += g
        total_pending += p
        acc = (h / (h + m) * 100) if (h + m) > 0 else 0
        print(f"{d.name}: {h}H / {m}M ({acc:.1f}%) | pending={p} | graded={g}")
    tot = total_h + total_m
    acc = (total_h / tot * 100) if tot else 0
    print(f"\nTOTAL: {total_h}H / {total_m}M ({acc:.1f}%) | pending={total_pending} | graded={total_graded}")


if __name__ == "__main__":
    main()
