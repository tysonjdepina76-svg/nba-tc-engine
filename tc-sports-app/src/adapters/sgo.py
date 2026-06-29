# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.

"""SGO (SportsGameOdds) adapter — DK player props + lines.

Pattern mirrors ESPN adapter: fetch + parse, NO math.
Returns parsed event rows with DK bookmaker odds.

SGO V2 API (correct endpoint + params from existing /Projects/build_pregame_combos.py):
  GET https://api.sportsgameodds.com/v2/events
      ?leagueID={league}  # required, lowercase ("wnba", "nba", etc.)
      &oddsAvailable=true  # filters to events with active lines
      &limit=100           # default is 10 — MUST set

  Headers:
      x-api-key: <SPORTSGAMEODDS_API_KEY>

Response shape (per event):
  data: [
    {
      "id": ...,
      "teams": {"home": {...}, "away": {...}},
      "odds": {
        "points-<PLAYER_ID>-game-ou-over": {
          "byBookmaker": {
            "draftkings": {"available": true, "overUnder": 24.5, "odds": -110}
          }
        },
        "rebounds-<PLAYER_ID>-game-ou-over": {...},
        ...
        "points-all-game-ou-over": <game total>,
        "points-home-game-ml-home": <home ML>,
      }
    }
  ]
"""

import json
import os
import re
import socket
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode

from src.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from src.auto_retry import retry_with_backoff

socket.setdefaulttimeout(8)

WORKSPACE = Path("/home/workspace")
SECRETS_FILE = Path("/root/.zo/secrets.env")

SGO_BASE = "https://api.sportsgameodds.com/v2/events"
SGO_API_KEY_ENV = "SPORTSGAMEODDS_API_KEY"

DEFAULT_LIMIT = 100

# map sport → leagueID (lowercase, per SGO convention)
SPORT_TO_LEAGUE = {
    "NFL": "nfl",
    "NBA": "nba",
    "WNBA": "wnba",
    "MLB": "mlb",
    "SOCCER": "fifa_world_cup",
}

# stat name ↔ SGO stat key (as it appears in odds keys after "points-<PID>-game-ou-over")
STAT_ALIASES = {
    "PTS": "points",
    "REB": "rebounds",
    "AST": "assists",
    "3PM": "threes",
    "STL": "steals",
    "BLK": "blocks",
}
STAT_KEY_TO_ALIAS = {v: k for k, v in STAT_ALIASES.items()}


def _load_api_key() -> Optional[str]:
    k = os.environ.get(SGO_API_KEY_ENV)
    if k:
        return k
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith(SGO_API_KEY_ENV + "="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def _fetch(url: str, headers: dict, timeout: int = 10) -> dict:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}


class SGOAdapter:
    """SportsGameOdds data adapter — DK lines via /v2/events."""

    _breakers = CircuitBreakerRegistry()

    def __init__(self, sport: str, league: Optional[str] = None):
        sport = sport.upper()
        if sport not in SPORT_TO_LEAGUE:
            raise ValueError(f"Unsupported sport: {sport}. Supported: {list(SPORT_TO_LEAGUE)}")
        self.sport = sport
        self.league = league or SPORT_TO_LEAGUE[sport]
        self.api_key = _load_api_key()
        if not self.api_key:
            raise RuntimeError(f"Missing {SGO_API_KEY_ENV} in env or secrets file")
        self._breaker = self._breakers.get(
            f"sgo_{sport}", failure_threshold=3, recovery_timeout_sec=60
        )

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key, "Accept": "application/json"}

    def fetch_events(self, odds_only: bool = True) -> List[dict]:
        """Fetch events (raw). Pass odds_only=False to see closed/inactive markets."""
        params = {
            "leagueID": self.league,
            "limit": str(DEFAULT_LIMIT),
        }
        if odds_only:
            params["oddsAvailable"] = "true"
        url = f"{SGO_BASE}?{urlencode(params)}"
        try:
            data = self._breaker.call(retry_with_backoff, _fetch, url, self._headers(), 10)
        except CircuitOpenError as e:
            print(f"[SGO] blocked: {e}")
            return []
        except Exception as e:
            print(f"[SGO] failed: {e}")
            return []
        if data.get("_error"):
            return []
        return data.get("data", [])

    def fetch_dk_lines(self) -> Dict[str, Dict]:
        """Return DK player-prop lines for every active event, indexed as:

            {
              "<event_id>": {
                "game_total": float | None,
                "players": {
                  "<player_id>": {
                    "PTS":  {"line": 24.5, "over_odds": -110},
                    "REB":  {"line": 9.5,  "over_odds": -110},
                    ...
                  }
                }
              }
            }

        Player IDs follow SGO convention (NAME_1_<LEAGUE>).
        """
        out: Dict[str, Dict] = {}
        for event in self.fetch_events(odds_only=True):
            eid = event.get("id") or event.get("eventID")
            if not eid:
                continue
            entry = {"game_total": None, "players": {}}
            odds = event.get("odds", {}) or {}
            for key, val in odds.items():
                dk = (val.get("byBookmaker") or {}).get("draftkings") or {}
                if not dk.get("available"):
                    continue
                # game total
                if key == "points-all-game-ou-over":
                    ou = dk.get("overUnder")
                    if ou is not None:
                        try: entry["game_total"] = float(ou)
                        except (TypeError, ValueError): pass
                    continue
                # player prop: <stat>-<playerID>-game-ou-over
                m = re.match(r"^(points|rebounds|assists|threes|steals|blocks)-([A-Z0-9_]+)-game-ou-over$", key)
                if m:
                    stat_key, pid = m.group(1), m.group(2)
                    alias = STAT_KEY_TO_ALIAS.get(stat_key)
                    if not alias:
                        continue
                    ou = dk.get("overUnder")
                    if ou is None:
                        continue
                    try: line = float(ou)
                    except (TypeError, ValueError): continue
                    entry["players"].setdefault(pid, {})[alias] = {
                        "line": line,
                        "over_odds": dk.get("odds"),
                    }
            out[eid] = entry
        return out

    def fetch_player_props(self, stat_key: Optional[str] = None) -> List[dict]:
        """Flat list of (player_id, name, team, stat, line, odds).

        player name → ID resolver: extracts name from Player ID pattern
        NAME_1_NBA by uppercasing first segment and inserting spaces.
        """
        flat: List[dict] = []
        for eid, entry in self.fetch_dk_lines().items():
            for pid, props in entry["players"].items():
                for stat, info in props.items():
                    if stat_key and stat.upper() != stat_key.upper():
                        continue
                    flat.append({
                        "event_id": eid,
                        "player_id": pid,
                        "player": pid.split("_")[0].replace("_", " ").title(),
                        "stat": stat,
                        "line": info["line"],
                        "over_odds": info.get("over_odds"),
                        "source": "SGO",
                        "sport": self.sport,
                    })
        return flat


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="WNBA")
    args = ap.parse_args()
    a = SGOAdapter(sport=args.sport)
    lines = a.fetch_dk_lines()
    print(f"SGO {args.sport}: {len(lines)} events")
    for eid, entry in list(lines.items())[:2]:
        print(f"  event {eid}: {len(entry['players'])} players, total={entry['game_total']}")
        sample_pid = next(iter(entry["players"]), None)
        if sample_pid:
            print(f"    sample {sample_pid}: {entry['players'][sample_pid]}")
