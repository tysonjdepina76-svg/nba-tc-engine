"""Sport registry with stat schemas.

Single source of truth for all sport configs:
- name + display_name
- data source (TC_ENGINE / BOOK_LINES / STATIC / COMING_SOON)
- fetcher: player projections
- line_fetcher: game lines (ML/spread/total)
- schema: stat_labels, formatting, color, default_sort

Lives in sources/ so daily_picks.py, dashboard, and zo.space can all import the
canonical config.
"""
from enum import Enum
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass


class DataSource(Enum):
    TC_ENGINE = "tc_engine"
    BOOK_LINES = "book_lines"
    STATIC = "static"
    COMING_SOON = "coming_soon"


@dataclass
class SportConfig:
    name: str
    source: DataSource
    module: Optional[str] = None
    fn: Optional[str] = None
    fetcher: Optional[Callable] = None
    line_fetcher: Optional[Callable] = None
    enabled: bool = True
    error_msg: Optional[str] = None
    display_name: str = ""
    schema: Optional[Dict[str, Any]] = None


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
        # Lazy imports to avoid circular deps
        from sources.mlb_book_fetcher import fetch_mlb_book_lines
        from sources.wnba_lines_fetcher import fetch_wnba_lines
        from sources.line_fetcher import fetch_lines
        from sources.soccer_lines_fetcher import fetch_soccer_lines

        # ---- MLB ----
        self._registry['mlb'] = SportConfig(
            name='mlb',
            display_name='MLB Baseball',
            source=DataSource.BOOK_LINES,
            module=None,
            fetcher=fetch_mlb_book_lines,
            line_fetcher=lambda: fetch_lines('mlb'),
            enabled=True,
            schema={
                'stat_labels': ['AVG', 'HR', 'RBI', 'R', 'SB', 'OPS', 'ERA', 'WHIP', 'SO'],
                'stat_type': 'per_game',
                'default_sort': 'AVG',
                'color': '#003278',
                'category': 'baseball',
                'formatting': {
                    'AVG': '%.3f',
                    'ERA': '%.2f',
                    'WHIP': '%.2f',
                    'OPS': '%.3f',
                    'HR': '%d',
                    'RBI': '%d',
                    'R': '%d',
                    'SB': '%d',
                    'SO': '%d',
                },
            },
        )

        # ---- WNBA ----
        self._registry['wnba'] = SportConfig(
            name='wnba',
            display_name='WNBA Basketball',
            source=DataSource.TC_ENGINE,
            module='wnba_tc_engine',
            fetcher=None,
            line_fetcher=lambda: fetch_lines('wnba'),
            enabled=True,
            schema={
                'stat_labels': ['PTS', 'REB', 'AST', 'FG%', '3PM', 'STL', 'BLK'],
                'stat_type': 'per_game',
                'default_sort': 'PTS',
                'color': '#FFC72C',
                'category': 'basketball',
                'formatting': {
                    'PTS': '%.1f', 'REB': '%.1f', 'AST': '%.1f',
                    'FG%': '%.1f%%', '3PM': '%.1f', 'STL': '%.1f', 'BLK': '%.1f',
                },
            },
        )

        # ---- World Cup / Soccer ----
        wc_config = SportConfig(
            name='wc',
            display_name='World Cup Soccer',
            source=DataSource.BOOK_LINES,
            module='soccer_tc_engine',
            fn='project_matchup',
            fetcher=fetch_soccer_lines,
            line_fetcher=lambda: fetch_lines('wc'),
            enabled=True,
            schema={
                'stat_labels': ['Goals', 'Assists', 'Shots', 'Shots on Target',
                                'Pass%', 'Tackles', 'Fouls', 'Corners'],
                'stat_type': 'per_match',
                'default_sort': 'Goals',
                'color': '#1A1A2E',
                'category': 'soccer',
                'formatting': {
                    'Goals': '%d', 'Assists': '%d',
                    'Shots': '%.1f', 'Shots on Target': '%.1f',
                    'Pass%': '%.1f%%', 'Tackles': '%.1f',
                    'Fouls': '%.1f', 'Corners': '%.1f',
                },
            },
        )
        self._registry['wc'] = wc_config
        # alias
        self._registry['soccer'] = wc_config

        # ---- Off-season ----
        for k, label, color, stats in [
            ('nba', 'NBA Basketball', '#1D428A',
             ['PTS', 'REB', 'AST', 'FG%', '3PM', 'STL', 'BLK']),
            ('nfl', 'NFL Football', '#013369',
             ['PASS YDS', 'RUSH YDS', 'REC YDS', 'TD', 'INT', 'SACKS']),
            ('nhl', 'NHL Hockey', '#D05A34',
             ['Goals', 'Assists', 'Points', 'SOG', 'PIM']),
        ]:
            self._registry[k] = SportConfig(
                name=k, display_name=label,
                source=DataSource.COMING_SOON,
                enabled=False,
                error_msg=f"{label} off-season — purged 6/27",
                schema={
                    'stat_labels': stats,
                    'stat_type': 'per_game',
                    'default_sort': stats[0],
                    'color': color,
                },
            )

    def get(self, sport: str) -> SportConfig:
        sl = sport.lower()
        if sl in self._registry:
            return self._registry[sl]
        # alias: 'soccer' -> 'wc'
        if sl == 'soccer':
            return self._registry['wc']
        if sl == 'world cup':
            return self._registry['wc']
        return SportConfig(
            name=sport, display_name=sport.upper(),
            source=DataSource.STATIC,
            enabled=False,
            error_msg=f"Unknown sport: {sport}",
        )

    def get_schema(self, sport: str) -> Dict:
        return self.get(sport).schema or {}

    def list_enabled(self) -> Dict[str, SportConfig]:
        return {k: v for k, v in self._registry.items() if v.enabled}

    def list_sports(self) -> List[SportConfig]:
        return list(self._registry.values())


REGISTRY = SportsRegistry()
