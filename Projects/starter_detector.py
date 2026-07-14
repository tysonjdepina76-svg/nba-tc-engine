"""
Starter detection for TC pipeline.

Primary: ESPN lineup data (summary endpoint, when roster is present)
Fallback: minutes-based heuristic — avgMinutes > 20 = STARTER

Used by wnba_tc_engine / nba_tc_engine to set player.role before
projections are computed and written to proj_SPORT_MATCHUP.json.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)

# minutes-per-game threshold: anyone above this in season avg = STARTER
STARTER_MPG_THRESHOLD = 20.0
# per-team starter cap (WNBA/NBA = 5; soccer/MLB varies)
DEFAULT_STARTER_CAP = 5


def _try_espn_lineup(event_id: str, sport: str = "basketball/wnba") -> Dict[str, List[str]] | None:
    """
    Hit ESPN summary endpoint for the event and return {team_abbr: [starter_names]}.
    Returns None if endpoint fails or no roster present.
    """
    try:
        import requests
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/summary"
        r = requests.get(url, params={"event": event_id}, timeout=5)
        if not r.ok:
            return None
        d = r.json()
        # ESPN summary carries rosters under different keys depending on game state.
        # 1. explicit "rosters" block (soccer/Mlb lineups)
        explicit = d.get("rosters") or []
        if explicit:
            out: Dict[str, List[str]] = {}
            for grp in explicit:
                team_abbr = (grp.get("team") or {}).get("abbreviation") or ""
                names = [
                    (p.get("athlete") or {}).get("displayName")
                    for p in (grp.get("roster") or [])
                    if p.get("starter") is True
                ]
                if team_abbr:
                    out[team_abbr] = [n for n in names if n]
            if out:
                return out
        # 2. boxscore players with starter flag (basketball when game has lineup data)
        starters_by_team: Dict[str, List[str]] = {}
        for t in (d.get("boxscore") or {}).get("teams", []) or []:
            abbr = (t.get("team") or {}).get("abbreviation") or ""
            # boxscore.player entries may carry position/starter flag
            starters = []
            for stat in t.get("statistics", []) or []:
                for ath in stat.get("athletes", []) or []:
                    if ath.get("starter") is True:
                        nm = (ath.get("athlete") or {}).get("displayName")
                        if nm:
                            starters.append(nm)
            if abbr and starters:
                starters_by_team[abbr] = starters
        return starters_by_team or None
    except Exception as e:
        log.debug(f"ESPN lineup fetch failed for event {event_id}: {e}")
        return None


def detect_starters(
    players: List[Dict[str, Any]],
    team_abbr: str,
    event_id: str | None = None,
    sport: str = "basketball/wnba",
    starter_cap: int = DEFAULT_STARTER_CAP,
) -> List[Dict[str, Any]]:
    """
    Mark players with role='START' (TC engine convention) or 'BENCH'.
    Returns the starter subset.

    Order of attempts:
      1. ESPN lineup data via event_id (if provided and reachable)
      2. Minutes-based fallback: avgMinutes > STARTER_MPG_THRESHOLD, top `starter_cap`
    """
    espn_names: set[str] = set()
    if event_id:
        lineup = _try_espn_lineup(event_id, sport) or {}
        espn_names = set(lineup.get(team_abbr, []) or [])

    # mark ESPN-confirmed starters first
    for p in players:
        name = p.get("player") or p.get("name") or ""
        if espn_names and name in espn_names:
            p["role"] = "START"
        else:
            p["role"] = "BENCH"

    # minutes-based fallback if ESPN gave us nothing useful
    if not espn_names:
        mpp_key_candidates = ["avgMinutes", "minutes_per_game", "MPG", "min_per_game"]
        scored = []
        for p in players:
            sinfo = p.get("season_stats") or {}
            mpg = 0.0
            for k in mpp_key_candidates:
                if k in sinfo and sinfo[k]:
                    try:
                        mpg = float(sinfo[k])
                        break
                    except (TypeError, ValueError):
                        continue
            # also check direct avgMinutes on the player dict
            if not mpg:
                try:
                    mpg = float(p.get("avgMinutes") or 0)
                except (TypeError, ValueError):
                    pass
            scored.append((mpg, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        for mpg, p in scored[:starter_cap]:
            if mpg >= STARTER_MPG_THRESHOLD:
                p["role"] = "START"
            else:
                # below threshold but top of bench — keep BENCH, don't promote
                p["role"] = "BENCH"
        # everyone below cap stays BENCH (already set above)

    starters = [p for p in players if p.get("role") == "START"]
    return starters