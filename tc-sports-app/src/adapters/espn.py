# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.
"""ESPN adapter — fetches + parses data only. NO math.

Wraps ESPN Core API and Site API calls with:
• circuit_breaker (3 fails → stops hitting the API)
• auto_retry (exponential backoff)
• thread-pool fan-out for athlete stats (proven in old wnba_tc_engine)

Returns domain entities (Player, Game). The engine never sees raw JSON.
"""

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from src.auto_retry import retry_with_backoff
from src.domain.entities import Player, Game
from src.domain.sport_config import SPORT_CONFIG


WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
SECRETS_FILE = Path("/root/.zo/secrets.env")

# ESPN Core API base (no auth, reliable per old wnba engine)
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"
# ESPN Site API base (slower, intermittent)
ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"

# Sport slug mapping for ESPN URLs
SPORT_SLUGS = {
    "WNBA": "basketball/leagues/wnba",
    "NBA":  "basketball/leagues/nba",
    "NFL":  "football/leagues/nfl",
    "MLB":  "baseball/leagues/mlb",
    "SOCCER": "soccer/leagues/uefa.champions",  # overridden per league
}


def load_secrets() -> None:
    """Load ESPN/api keys from secrets file (no-op if ESPN is public)."""
    if not SECRETS_FILE.exists():
        return
    for line in SECRETS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))

def _fetch(url: str, timeout: int = 10) -> dict:
    """Raw fetch. Wrapped by breaker+retry at the call site."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}


class ESPNAdapter:
    """ESPN data adapter. One instance per sport."""

    # Module-level breaker registry, one breaker per endpoint category
    _breakers = CircuitBreakerRegistry()

    def __init__(self, sport: str, season: int = 2026):
        load_secrets()
        sport = sport.upper()
        if sport not in SPORT_SLUGS:
            raise ValueError(f"Unsupported sport: {sport}")
        self.sport = sport
        self.season = season
        self.slug = SPORT_SLUGS[sport]
        self.config = SPORT_CONFIG[sport]
        # Per-endpoint breakers (separate budgets for slate vs stats)
        self._slate_breaker = self._breakers.get(f"espn_{sport}_slate", failure_threshold=3, recovery_timeout_sec=60)
        self._stats_breaker = self._breakers.get(f"espn_{sport}_stats", failure_threshold=5, recovery_timeout_sec=30)

    # ─────────────────────────────────────────────────────────────────
    # Slate (today's games)
    # ─────────────────────────────────────────────────────────────────
    def fetch_today_slate(self) -> List[Game]:
        """Fetch today's games via Site API. Returns List[Game]."""
        try:
            data = self._slate_breaker.call(
                retry_with_backoff,
                _fetch,
                f"{ESPN_SITE}/{self.slug}/scoreboard",
                8,
            )
        except CircuitOpenError as e:
            print(f"[ESPN:{self.sport}] slate fetch blocked: {e}")
            return []
        except Exception as e:
            print(f"[ESPN:{self.sport}] slate fetch failed: {e}")
            return []

        if data.get("_error"):
            return []

        games: List[Game] = []
        for ev in data.get("events", []):
            comp = (ev.get("competitions", []) or [{}])[0]
            teams = comp.get("competitors", [])
            a = next((t for t in teams if t.get("homeAway") == "away"), {})
            h = next((t for t in teams if t.get("homeAway") == "home"), {})
            a_abbr = (a.get("team") or {}).get("abbreviation", "")
            h_abbr = (h.get("team") or {}).get("abbreviation", "")
            status_obj = ev.get("status") or {}
            games.append(Game(
                sport=self.sport,
                away=a_abbr,
                home=h_abbr,
                event_id=str(ev.get("id", "")),
                status=(status_obj.get("type") or {}).get("description", ""),
                completed=(status_obj.get("type") or {}).get("completed", False),
                game_time=ev.get("date", ""),
            ))
        return games

    # ─────────────────────────────────────────────────────────────────
    # Season stats (for projections)
    # ─────────────────────────────────────────────────────────────────
    def fetch_season_stats(self, limit: int = 150) -> Dict[str, Player]:
        """Fetch season averages for top players. Returns {player_name_lower: Player}.

        Pattern lifted from old wnba_tc_engine.fetch_all_season_stats:
        1. Leaders endpoint → collect unique athlete IDs
        2. Parallel fetch per-athlete stats + name
        3. Stitch into Player objects
        """
        try:
            leaders_data = self._stats_breaker.call(
                retry_with_backoff,
                _fetch,
                (f"{ESPN_CORE}/{self.slug}/seasons/{self.season}/types/2/"
                 f"leaders?limit={limit}"),
                12,
            )
        except CircuitOpenError as e:
            print(f"[ESPN:{self.sport}] leaders blocked: {e}")
            return {}
        except Exception as e:
            print(f"[ESPN:{self.sport}] leaders failed: {e}")
            return {}

        if leaders_data.get("_error"):
            return {}

        # Phase 1: collect unique athlete refs + team ids
        athlete_refs: Dict[int, tuple] = {}
        team_id_map = self.config.get("team_ids", {})
        team_id_to_abbr = {v: k for k, v in team_id_map.items()}

        for cat in leaders_data.get("categories", []):
            for leader in cat.get("leaders", []):
                ath_ref = leader.get("athlete", {}).get("$ref", "")
                athlete_id = int(ath_ref.split("/")[-1].split("?")[0]) if ath_ref else None
                if not athlete_id:
                    continue
                team_ref = leader.get("team", {}).get("$ref", "")
                team_id = int(team_ref.split("/")[-1].split("?")[0]) if team_ref else None
                team_abbr = team_id_to_abbr.get(team_id, "")
                if athlete_id not in athlete_refs:
                    athlete_refs[athlete_id] = (ath_ref, team_abbr, leader)

        # Phase 2: parallel fetch per-athlete stats + name
        result: Dict[str, Player] = {}
        lock = threading.Lock()

        def fetch_one(athlete_id: int, ref: str, team_abbr: str, leader_obj: dict) -> Optional[Player]:
            try:
                stats = self._stats_breaker.call(
                    retry_with_backoff,
                    _fetch,
                    (f"{ESPN_CORE}/{self.slug}/seasons/{self.season}/types/2/"
                     f"athletes/{athlete_id}/statistics/0?lang=en&region=us"),
                    4,
                )
            except (CircuitOpenError, Exception):
                return None
            if stats.get("_error"):
                return None

            ath = self._stats_breaker.call(retry_with_backoff, _fetch, ref, 4) if ref else {}
            if ath.get("_error"):
                ath = {}
            name = ath.get("displayName", ath.get("fullName", f"id_{athlete_id}"))

            # Extract stat averages
            stat_avgs: Dict[str, float] = {}
            for sc in (stats.get("splits") or {}).get("categories", []):
                for s in sc.get("stats", []):
                    sname = s.get("name", "")
                    sval = s.get("value", 0)
                    if isinstance(sval, (int, float)) and sval > 0 and sname:
                        stat_avgs[sname] = float(sval)

            player = Player(
                name=name,
                team=team_abbr,
                sport=self.sport,
                role=PlayerRole.BENCH,  # starters detected downstream
                status=PlayerStatus.ACTIVE,
                pos=ath.get("position", {}).get("abbreviation", "") if isinstance(ath.get("position"), dict) else "",
                min=self.config.get("default_minutes", 25.0),
                season_stats=stat_avgs,
            )
            with lock:
                result[name.lower()] = player
            return player

        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [
                ex.submit(fetch_one, aid, ref, tabbr, leader)
                for aid, (ref, tabbr, leader) in athlete_refs.items()
            ]
            for f in as_completed(futures):
                pass  # results mutated into `result` dict

        return result

    # ─────────────────────────────────────────────────────────────────
    # Filter by team (for a matchup)
    # ─────────────────────────────────────────────────────────────────
    def players_for_matchup(
        self, all_players: Dict[str, Player], home: str, away: str
    ) -> tuple:
        """Return (home_players, away_players) from full roster."""
        home = home.upper()
        away = away.upper()
        home_roster = [p for p in all_players.values() if p.team == home]
        away_roster = [p for p in all_players.values() if p.team == away]
        return home_roster, away_roster
