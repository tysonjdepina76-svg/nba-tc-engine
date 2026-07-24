#!/usr/bin/env python3
"""
Roster Loader — Loads player rosters from data/rosters/ JSON files.
Provides lookup-by-name, team resolution, position enrichment for all 4 sports.
Uses punctuation-normalized fuzzy matching for names with apostrophes/accents.
"""
import json
import os
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

ROSTER_DIR = Path("/home/workspace/data/rosters")


class Roster:
    """Single-sport roster container with fast lookup."""

    def __init__(self, sport: str, raw: dict):
        self.sport = sport

        if sport == "mlb":
            self.teams = raw.get("rosters", {})
            self.total = raw.get("total_players", 0)
        else:
            self.teams = raw
            self.total = sum(len(t.get("players", [])) for t in raw.values())

        self._name_index = {}
        self._id_index = {}
        self._team_index = {}

        for abbr, team_data in self.teams.items():
            team_name = team_data.get("team", abbr) if isinstance(team_data, dict) else abbr
            players = team_data.get("players", []) if isinstance(team_data, dict) else []
            self._team_index[abbr.upper()] = team_name
            for p in players:
                name_key = p["name"].lower().strip()
                norm_key = self._normalize(name_key)
                self._name_index[norm_key] = {
                    "name": p["name"],
                    "position": p.get("position") or p.get("pos", ""),
                    "team_abbr": abbr,
                    "team_name": team_name,
                    "jersey": str(p.get("jersey", "")),
                    "id": str(p.get("id", "")) if p.get("id") else "",
                }
                pid = str(p.get("id", ""))
                if pid:
                    self._id_index[pid] = self._name_index[norm_key]

    @staticmethod
    def _normalize(s: str) -> str:
        """Strip punctuation for fuzzy matching ('A'ja' -> 'aja', 'O'Neal' -> 'oneal')."""
        return re.sub(r"[^a-z]", "", s.lower().strip())

    def lookup(self, name: str) -> Optional[dict]:
        """Normalized lookup: strips punctuation, then exact match, then partial."""
        n = self._normalize(name)
        if n in self._name_index:
            return self._name_index[n]
        for key, val in self._name_index.items():
            if n in key or key in n:
                return val
        return None

    def get_team_name(self, abbr: str) -> str:
        return self._team_index.get(abbr.upper(), abbr)

    def __repr__(self):
        return f"Roster({self.sport}, {len(self.teams)} teams, {len(self._name_index)} players)"


class RosterLoader:
    """Loads all 4 sports rosters and provides unified lookup."""

    def __init__(self):
        self.rosters: Dict[str, Roster] = {}
        self._loaded = False

    def load(self):
        if self._loaded:
            return

        sport_files = {
            "mlb": "mlb_rosters.json",
            "wnba": "wnba_rosters.json",
            "nba": "nba_rosters.json",
            "nfl": "nfl_rosters.json",
        }

        for sport, filename in sport_files.items():
            fpath = ROSTER_DIR / filename
            if not fpath.exists():
                print(f"⚠️ Roster file missing: {fpath}")
                continue
            try:
                with open(fpath) as f:
                    self.rosters[sport] = Roster(sport, json.load(f))
                print(f"✅ Loaded {self.rosters[sport]}")
            except Exception as e:
                print(f"❌ Failed to load {sport}: {e}")

        self._loaded = True

    def enrich_player(self, name: str, sport: str, team_hint: str = "") -> dict:
        """Enrich a player entry with roster data: position, full team name, jersey, id."""
        sport_l = sport.lower()
        if sport_l not in self.rosters:
            return {}

        roster = self.rosters[sport_l]
        info = roster.lookup(name)
        if not info:
            return {}

        result = {
            "roster_position": info["position"],
            "roster_team_full": info["team_name"],
            "roster_team_abbr": info["team_abbr"],
            "roster_jersey": info["jersey"],
            "roster_id": info["id"],
        }

        # If team_hint matches, confirm it
        if team_hint and info["team_abbr"].upper() == team_hint.upper().strip():
            result["roster_team_confirmed"] = True

        return result

    def enrich_pick(self, pick: dict) -> dict:
        """Enrich a pick dict in-place with roster data."""
        sport = pick.get("sport", pick.get("league", ""))
        name = pick.get("name", pick.get("player", ""))
        team = pick.get("team", "")
        if not sport or not name:
            return pick

        enrichment = self.enrich_player(name, sport, team)
        pick.update(enrichment)
        return pick

    def resolve_team_name(self, abbr: str, sport: str) -> str:
        sport_l = sport.lower()
        if sport_l in self.rosters:
            return self.rosters[sport_l].get_team_name(abbr)
        return abbr


_loader = None


def get_loader() -> RosterLoader:
    global _loader
    if _loader is None:
        _loader = RosterLoader()
        _loader.load()
    return _loader


if __name__ == "__main__":
    loader = get_loader()
    for s, r in loader.rosters.items():
        print(r)
    # Test lookup
    print("\n--- Lookup tests ---")
    wnba = loader.enrich_player("Aja Wilson", "wnba")
    print(f"Aja Wilson: {wnba}")
    mlb = loader.enrich_player("Aaron Judge", "mlb")
    print(f"Aaron Judge: {mlb}")
