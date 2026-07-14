#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
Soccer Combo Engine — World Cup / Soccer Parlay Builder
========================================================

Separate engine, separate port (8516), separate data path from dk_combos_engine.

Inputs:
  - /home/workspace/Daily_Log/worldcup/YYYY-MM-DD/picks.csv  (FanDuel player props)
  - /home/workspace/Daily_Log/soccer/YYYY-MM-DD/lines.json   (game lines, 49 books)

Outputs (JSON):
  {
    "sport": "soccer",     # not "WORLD CUP" — clean normalization
    "leagues": [...],
    "matches": [{home, away, commence, event_id, combo_legs, best_mls_spread, best_total}],
    "combos": [{legs: [...], books: [...], total_odds: int, sportsbook_count: int}],
    "count": int,
    "source": "worldcup_picks" | "soccer_live_pull" | "merged"
  }

Usage:
  python3 soccer_combo_engine.py --serve
  python3 soccer_combo_engine.py --league "FIFA World Cup" --max-legs 4

Independent from dk_combos_engine.py — never touches NBA/WNBA data.
"""

import json
import os
import re
import sys
import argparse
import http.server
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SECRETS_FILE = "/root/.zo/secrets.env"

def load_secret(name: str) -> str:
    try:
        txt = Path(SECRETS_FILE).read_text()
        for line in txt.split("\n"):
            m = re.match(rf"^\s*{name}\s*=\s*[\"']?([^\"'\s#]+)", line)
            if m:
                return m.group(1)
    except Exception:
        import logging as _log
        _log.getLogger(__name__).debug("exception", exc_info=True)
    return os.environ.get(name, "")

# === Data sources ===
WORLDCUP_DIR = Path("/home/workspace/Daily_Log/worldcup")
SOCCER_DIR = Path("/home/workspace/Daily_Log/soccer")
LIVE_PROPS_DIR = Path("/home/workspace/Daily_Log/live_props")

SUPPORTED_SOCCER_LEAGUES = {
    "soccer_fifa_world_cup": "FIFA World Cup",
    "soccer_conmebol_copa_libertadores": "Copa Libertadores",
    "soccer_conmebol_copa_sudamericana": "Copa Sudamericana",
    "soccer_brazil_serie_b": "Brazil Serie B",
    "soccer_china_superleague": "China Super League",
    "soccer_germany_dfb_pokal": "Germany DFB-Pokal",
    "soccer_league_of_ireland": "League of Ireland",
    "soccer_norway_eliteserien": "Norway Eliteserien",
    "soccer_spain_segunda_division": "Spain Segunda",
    "soccer_sweden_allsvenskan": "Sweden Allsvenskan",
    "soccer_sweden_superettan": "Sweden Superettan",
}

@dataclass
class SoccerComboLeg:
    player: str
    team: str
    stat: str              # "goals" | "assists" | "shots" | "shots_on_target" | "corners" | "tackles" | "fouls" | "cards" | "passes" | "points" (rare)
    direction: str         # "Over" | "Under"
    line: float
    odds: int              # American
    book: str              # "fanduel" | "draftkings" | "betmgm" | ...
    match: str             # "Cape Verde @ Spain"
    commence: str          # ISO

@dataclass
class SoccerCombo:
    match: str
    legs: List[SoccerComboLeg] = field(default_factory=list)
    books: List[str] = field(default_factory=list)
    total_odds: int = 0    # American
    sportsbook_count: int = 0

    def to_dict(self):
        return {
            "match": self.match,
            "legs": [asdict(l) for l in self.legs],
            "books": self.books,
            "total_odds": self.total_odds,
            "sportsbook_count": self.sportsbook_count,
        }

def _latest_dir(parent: Path) -> Optional[Path]:
    """Return most recent date subdir of `parent`, or None."""
    if not parent.exists():
        return None
    candidates = [d for d in parent.iterdir() if d.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda d: d.name, reverse=True)[0]

def _read_worldcup_picks() -> Tuple[List[dict], Optional[str]]:
    """Read WC player-prop picks CSV. Prefers today's Daily_Log first.

    Returns (rows, date_str). Skips header if present.
    """
    from datetime import datetime as _dt
    today = _dt.now().strftime("%Y-%m-%d")
    # Prefer today's per-player WC picks from main log dir
    today_path = Path(f"/home/workspace/Daily_Log/{today}/soccer_player_picks.csv")
    if today_path.exists():
        import csv
        rows = []
        with today_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows, today
    d = _latest_dir(WORLDCUP_DIR)
    if not d:
        return [], None
    csv_path = d / "picks.csv"
    if not csv_path.exists():
        return [], d.name
    import csv
    rows = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows, d.name

def _read_soccer_lines() -> Tuple[dict, Optional[str]]:
    """Read the most recent soccer game-lines JSON (49 books)."""
    d = _latest_dir(SOCCER_DIR)
    if not d:
        return {}, None
    p = d / "lines.json"
    if not p.exists():
        return {}, d.name
    try:
        return json.loads(p.read_text()), d.name
    except Exception:
        return {}, d.name

def _american_to_decimal(odds: int) -> float:
    if odds is None:
        return 1.0
    if odds >= 100:
        return 1.0 + odds / 100.0
    if odds <= -100:
        return 1.0 + 100.0 / abs(odds)
    return 1.0

def _decimal_to_american(dec: float) -> int:
    if dec <= 1.0:
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))

def build_combo_legs_from_worldcup(picks_rows: List[dict]) -> List[SoccerComboLeg]:
    """Convert WC picks.csv rows into typed SoccerComboLegs."""
    out = []
    for r in picks_rows:
        try:
            player = (r.get("player") or r.get("Player") or "").strip()
            if not player:
                continue
            team = (r.get("team") or r.get("Team") or "").strip()
            stat = (r.get("stat") or r.get("market") or r.get("Stat") or "").strip().lower()
            direction = (r.get("direction") or r.get("side") or "Over").strip()
            line = float(r.get("line") or r.get("Line") or 0)
            odds_raw = r.get("odds") or r.get("Odds") or "-110"
            odds = int(re.sub(r"[^\-0-9]", "", str(odds_raw)) or "-110")
            book = (r.get("book") or r.get("bookmaker") or "fanduel").strip().lower()
            match = (r.get("match") or r.get("matchup") or r.get("event") or "").strip()
            commence = (r.get("commence") or r.get("commence_time") or r.get("start") or "").strip()
            out.append(SoccerComboLeg(
                player=player, team=team, stat=stat, direction=direction,
                line=line, odds=odds, book=book, match=match, commence=commence,
            ))
        except Exception:
            continue
    return out

def _find_best_game_line(lines_payload: dict, match: str) -> Tuple[Optional[float], Optional[float], int]:
    """Return (best_home_spread, best_total, sportsbook_count) for a match.
    match is a free-text string like 'Cape Verde @ Spain'.
    """
    if not lines_payload:
        return None, None, 0
    best_spread, best_total = None, None
    sb_count = 0
    # Match substring both directions
    mt = match.lower()
    for ev in lines_payload.get("events", []):
        ev_match = f"{ev.get('away_team','')} @ {ev.get('home_team','')}".lower()
        if mt not in ev_match and ev_match not in mt:
            continue
        books = ev.get("books", {})
        sb_count = len(books)
        for book_data in books.values():
            for m in book_data.get("h2h", []):
                pass  # h2h not a spread
            for m in book_data.get("spreads", []):
                if m.get("name") == ev.get("home_team"):
                    p = m.get("point")
                    if p is not None and (best_spread is None or abs(p) < abs(best_spread)):
                        best_spread = p
            for m in book_data.get("totals", []):
                p = m.get("point")
                if p is not None and (best_total is None or p > best_total):
                    best_total = p
    return best_spread, best_total, sb_count

def build_combos(legs: List[SoccerComboLeg], max_legs: int = 4) -> List[SoccerCombo]:
    """Build same-match parlays grouped by match."""
    by_match: Dict[str, List[SoccerComboLeg]] = {}
    for leg in legs:
        by_match.setdefault(leg.match, []).append(leg)

    combos = []
    for match, mlegs in by_match.items():
        if len(mlegs) < 2:
            continue
        # Pick the top max_legs by lowest vig (closest to -110 = balanced)
        mlegs_sorted = sorted(mlegs, key=lambda l: abs(int(l.odds or -110) + 110))
        chosen = mlegs_sorted[:max_legs]
        # Combined odds
        dec = 1.0
        for l in chosen:
            dec *= _american_to_decimal(int(l.odds or -110))
        total_odds = _decimal_to_american(dec)
        books = sorted(set(l.book for l in chosen))
        combos.append(SoccerCombo(
            match=match,
            legs=chosen,
            books=books,
            total_odds=total_odds,
            sportsbook_count=len(books),
        ))
    return combos

def render_summary(combos: List[SoccerCombo], leagues: List[str], source: str, date: str) -> dict:
    return {
        "sport": "soccer",          # clean — not "WORLD CUP"
        "leagues": leagues,
        "date": date,
        "count": len(combos),
        "source": source,
        "combos": [c.to_dict() for c in combos],
    }

# === HTTP server (port 8516 — does NOT collide with 8515 basketball engine) ===

def serve_combos(port: int = 8516):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # quiet

        def do_GET(self):
            if not self.path.startswith("/combos"):
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            qs = self.path.split("?")[-1] if "?" in self.path else ""
            params = dict(p.split("=") for p in qs.split("&") if "=" in p)
            league = params.get("league")
            max_legs = int(params.get("max_legs", 4))

            picks, wc_date = _read_worldcup_picks()
            legs = build_combo_legs_from_worldcup(picks)

            # Optional league filter
            if league:
                legs = [l for l in legs if league.lower() in l.match.lower()]

            combos = build_combos(legs, max_legs=max_legs)

            # Attach game-line context
            lines_payload, _ = _read_soccer_lines()
            for c in combos:
                sp, tot, sb = _find_best_game_line(lines_payload, c.match)
                if sp is not None:
                    c.legs[0].match = f"{c.match} (spread {sp:+.1f})"
                # best_total / sb count not added to leg dataclass — store in combo object
                c.sportsbook_count = sb or c.sportsbook_count

            leagues = sorted(set(SUPPORTED_SOCCER_LEAGUES.get(l, l) for l in []))

            out = render_summary(
                combos=combos,
                leagues=list(SUPPORTED_SOCCER_LEAGUES.values()),
                source="worldcup_picks" if picks else "none",
                date=wc_date or "",
            )
            self.wfile.write(json.dumps(out, indent=2).encode())

    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print(f"Soccer Combos server on http://0.0.0.0:{port}/combos")
    server.serve_forever()

def main():
    p = argparse.ArgumentParser(description="Soccer Combo Lines (World Cup + 10 other leagues)")
    p.add_argument("--league", help="Filter by league name substring")
    p.add_argument("--max-legs", type=int, default=4, help="Max legs per combo (default 4)")
    p.add_argument("--serve", action="store_true", help="Run as HTTP server (port 8516)")
    p.add_argument("--port", type=int, default=8516)
    args = p.parse_args()

    picks, wc_date = _read_worldcup_picks()
    legs = build_combo_legs_from_worldcup(picks)
    if args.league:
        legs = [l for l in legs if args.league.lower() in l.match.lower()]

    combos = build_combos(legs, max_legs=args.max_legs)
    print(json.dumps(render_summary(
        combos=combos,
        leagues=list(SUPPORTED_SOCCER_LEAGUES.values()),
        source="worldcup_picks" if picks else "none",
        date=wc_date or "",
    ), indent=2))

    if args.serve:
        serve_combos(args.port)

if __name__ == "__main__":
    main()
