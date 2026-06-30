"""SGO (SportsGameOdds) adapter — player props."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import urllib.request
import json
from dataclasses import dataclass
from typing import List


@dataclass
class SGOProp:
    player_id: str
    player_name: str
    stat: str
    line: float
    over_odds: int = None
    under_odds: int = None


class SGOClient:
    BASE_URL = "https://api.sportsgameodds.com/v2"

    def __init__(self, api_key=None):
        if not api_key:
            raise ValueError("SGO API key is required")
        self.api_key = api_key

    def _get(self, url):
        req = urllib.request.Request(url, headers={"x-api-key": self.api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def fetch_player_props(self, sport: str) -> List[SGOProp]:
        url = f"{self.BASE_URL}/events?sportID={sport.lower()}&market=player-props"
        try:
            payload = self._get(url)
        except Exception:
            return []
        props = []
        for item in payload.get("data", []):
            try:
                props.append(SGOProp(
                    player_id=str(item.get("playerID", "")),
                    player_name=item.get("playerName", ""),
                    stat=item.get("statID", ""),
                    line=float(item.get("line", 0)),
                    over_odds=item.get("overOdds"),
                    under_odds=item.get("underOdds"),
                ))
            except (ValueError, TypeError):
                continue
        return props
