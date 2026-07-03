"""Single source of truth for all sports data sources + stat schemas.
Matches actual workspace layout — engines live at top of Projects/, not in sources/ subpackage.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
from enum import Enum
import importlib


class DataSource(Enum):
    TC_ENGINE = "tc_engine"
    BOOK_LINES = "book_lines"
    STATIC = "static"
    COMING_SOON = "coming_soon"
    OFF_SEASON = "off_season"


# ============================================================================
# SPORT_SCHEMAS — single source of truth for stat labels, types, colors.
# Frontend fetches this via /api/sports-config and renders sport-correct
# columns. Without this, hardcoded "Points/Rebounds/Assists" labels bled
# into every sport's UI (the original "MLB shows Points" bug).
# ============================================================================
SPORT_SCHEMAS = {
    'nba': {
        'stat_labels': ['PTS', 'REB', 'AST', 'FG%', '3PM', 'STL', 'BLK'],
        'stat_keys':   ['pts',  'reb', 'ast', 'fg',  'tpm', 'stl', 'blk'],
        'stat_type':   'per_game',
        'default_sort':'PTS',
        'color':       '#1D428A',
        'display_name':'NBA',
    },
    'wnba': {
        'stat_labels': ['PTS', 'REB', 'AST', 'FG%', '3PM', 'STL', 'BLK'],
        'stat_keys':   ['pts',  'reb', 'ast', 'fg',  'tpm', 'stl', 'blk'],
        'stat_type':   'per_game',
        'default_sort':'PTS',
        'color':       '#FFC72C',
        'display_name':'WNBA',
    },
    'mlb': {
        'stat_labels': ['AVG', 'HR', 'RBI', 'OPS', 'ERA', 'WHIP', 'SO'],
        'stat_keys':   ['avg', 'hr', 'rbi', 'ops', 'era', 'whip', 'so'],
        'stat_type':   'per_game',
        'default_sort':'AVG',
        'color':       '#003278',
        'display_name':'MLB',
    },
    'soccer': {
        'stat_labels': ['Goals', 'Shots', 'Corners', 'Pass%', 'Tackles', 'Fouls'],
        'stat_keys':   ['goals','shots','corners','pass_pct','tackles','fouls'],
        'stat_type':   'per_match',
        'default_sort':'Goals',
        'color':       '#2E8B57',
        'display_name':'Soccer',
    },
    'wc': {
        'stat_labels': ['Goals', 'Shots', 'Corners', 'Pass%', 'Saves'],
        'stat_keys':   ['goals','shots','corners','pass_pct','saves'],
        'stat_type':   'per_match',
        'default_sort':'Goals',
        'color':       '#1A1A2E',
        'display_name':'World Cup',
    },
    'nfl': {
        'stat_labels': ['PASS YDS', 'RUSH YDS', 'REC YDS', 'TD', 'INT', 'SACKS'],
        'stat_keys':   ['pass_yds','rush_yds','rec_yds','td','int','sacks'],
        'stat_type':   'per_game',
        'default_sort':'PASS YDS',
        'color':       '#013369',
        'display_name':'NFL',
    },
    'nhl': {
        'stat_labels': ['Goals', 'Assists', 'Points', 'Shots', 'Hits', 'PIM'],
        'stat_keys':   ['goals','assists','points','shots','hits','pim'],
        'stat_type':   'per_game',
        'default_sort':'Points',
        'color':       '#000000',
        'display_name':'NHL',
    },
}


def get_schema(sport: str) -> Optional[Dict[str, Any]]:
    """Return sport schema (stat_labels, color, etc) or None if unknown."""
    if not sport:
        return None
    sl = sport.lower()
    if sl in SPORT_SCHEMAS:
        return SPORT_SCHEMAS[sl]
    # Fuzzy match: 'world cup' → 'wc', 'soccer' → 'soccer', 'mlb' → 'mlb'
    aliases = {'world cup': 'wc', 'soccer': 'soccer', 'mlb': 'mlb', 'wnba': 'wnba', 'nba': 'nba', 'nfl': 'nfl', 'nhl': 'nhl'}
    if sl in aliases:
        return SPORT_SCHEMAS[aliases[sl]]
    for k, v in SPORT_SCHEMAS.items():
        if sl in k or k in sl:
            return v
    return None


def stat_format(value, label: str) -> str:
    """Format a stat value according to its label convention.
    - Percentages (AVG, FG%, Pass%): show as 3-decimal or .1%
    - Decimals (ERA, OPS, WHIP): 2 decimals
    - Integers (HR, RBI, SO, TD): round
    - Default: 1 decimal
    """
    if value is None or value == "" or value == "—":
        return "—"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)
    pct_labels = {"AVG", "FG%", "Pass%"}
    decimal_labels = {"ERA", "OPS", "WHIP"}
    if label in pct_labels:
        if label == "AVG":
            return f".{int(v * 1000):03d}" if v < 1 else f"{v:.3f}"
        return f"{v * 100:.1f}%"
    if label in decimal_labels:
        return f"{v:.2f}"
    if abs(v) >= 100 or v == int(v):
        return f"{int(round(v))}"
    return f"{v:.1f}"


@dataclass
class SportConfig:
    key: str
    name: str
    source: DataSource
    module: Optional[str] = None
    fn: Optional[str] = None
    fetcher: Optional[Callable] = None
    enabled: bool = True
    error_msg: Optional[str] = None


class SportsRegistry:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._registry: Dict[str, SportConfig] = {}
        self._register_all()

    def _register_all(self):
        # === ACTIVE SPORTS (wired 2026-07-01) ===
        # MLB = BOOK_LINES — TC engine module=None (page consumes /api/dk-lines directly)
        # WNBA = TC_ENGINE — full player projections
        self._registry['mlb'] = SportConfig(
            key='mlb', name='MLB',
            source=DataSource.BOOK_LINES,
            module=None, fn=None,
        )
        self._registry['wnba'] = SportConfig(
            key='wnba', name='WNBA',
            source=DataSource.TC_ENGINE,
            module='wnba_tc_engine', fn='project_game',
        )
        self._registry['soccer'] = SportConfig(
            key='soccer', name='Soccer / World Cup',
            source=DataSource.BOOK_LINES,
            module='soccer_tc_engine', fn='project_matchup',
        )

        # === OFF-SEASON (engines purged 2026-06-27) ===
        for k, label in [('nba','NBA'), ('nfl','NFL'), ('nhl','NHL')]:
            self._registry[k] = SportConfig(
                key=k, name=label,
                source=DataSource.OFF_SEASON,
                enabled=False,
                error_msg=f"{label} off-season — engine removed 2026-06-27. Re-enable when season opens."
            )

    def get(self, sport: str) -> SportConfig:
        if sport in self._registry:
            return self._registry[sport]
        # Fuzzy match
        sl = sport.lower()
        for k, cfg in self._registry.items():
            if sl in k or k in sl:
                return cfg
        return SportConfig(
            key=sport, name=sport,
            source=DataSource.STATIC,
            error_msg=f"Unknown sport: {sport}",
        )

    def is_available(self, sport: str) -> bool:
        c = self.get(sport)
        return c.enabled and c.source not in (DataSource.OFF_SEASON, DataSource.COMING_SOON)

    def list_sports(self) -> List[SportConfig]:
        return list(self._registry.values())


REGISTRY = SportsRegistry()
