"""SportsDataIO WNBA Adapter."""

from typing import List, Dict, Optional
from .base import SportsDataIOBase
from src.domain.entities import Player, Game, Projection, Sport


class WNBAAdapter(SportsDataIOBase):
    """WNBA data adapter for SportsDataIO."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("wnba", api_key)

    def get_players(self, team_id: Optional[int] = None) -> List[Player]:
        data = self.fetch_players(team_id)
        players = []
        for p in data:
            players.append(Player(
                name=f"{p.get('FirstName', '')} {p.get('LastName', '')}".strip(),
                team=p.get('Team', ''),
                position=p.get('Position', ''),
                stats={
                    "player_id": p.get('PlayerID'),
                    "status": p.get('Status'),
                    "injury_status": p.get('InjuryStatus'),
                    "injury_body_part": p.get('InjuryBodyPart'),
                }
            ))
        return players

    def get_games(self, date: str) -> List[Game]:
        data = self.fetch_games(date)
        games = []
        for g in data:
            games.append(Game(
                game_id=str(g.get('GameID', '')),
                home_team=g.get('HomeTeam', ''),
                away_team=g.get('AwayTeam', ''),
                sport=Sport.WNBA,
                date=g.get('Day', date),
                home_score=g.get('HomeTeamScore'),
                away_score=g.get('AwayTeamScore'),
                status=g.get('Status'),
            ))
        return games

    def get_boxscore(self, game_id: int) -> Dict:
        return self.fetch_boxscore(game_id)

    def get_betting_lines(self, game_id: int) -> Dict:
        events = self.fetch_betting_events()
        for event in events:
            if event.get('GameID') == game_id:
                return {
                    "ml_home": event.get('HomeTeamMoneyLine'),
                    "ml_away": event.get('AwayTeamMoneyLine'),
                    "spread": event.get('PointSpread'),
                    "total": event.get('OverUnder'),
                }
        return {}

    def get_injuries(self) -> List[Dict]:
        return self.fetch_injuries()


# Shorter alias
WNBAData = WNBAAdapter
