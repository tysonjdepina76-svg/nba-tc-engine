"""SportsDataIO MLB Adapter."""

from typing import List, Dict, Optional
from .base import SportsDataIOBase
from src.domain.entities import Player, Game, Projection, Sport


class MLBAdapter(SportsDataIOBase):
    """MLB data adapter for SportsDataIO."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("mlb", api_key)

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
                    "bat_hand": p.get('BatHand'),
                    "throw_hand": p.get('ThrowHand'),
                    "height": p.get('Height'),
                    "weight": p.get('Weight'),
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
                sport=Sport.MLB,
                date=g.get('Day', date),
                home_score=g.get('HomeTeamRuns'),
                away_score=g.get('AwayTeamRuns'),
                status=g.get('Status'),
                stage=self._get_stage(g.get('SeasonType')),
            ))
        return games

    def _get_stage(self, season_type: int) -> str:
        mapping = {
            1: "Regular Season",
            2: "Preseason",
            3: "Postseason",
            4: "Offseason",
            5: "All-Star",
        }
        return mapping.get(season_type, "Regular Season")

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

    def get_starting_lineups(self, game_id: int) -> Dict:
        return self._request(f"/starting_lineups/{game_id}")

    def get_injuries(self) -> List[Dict]:
        return self.fetch_injuries()

    def get_play_by_play(self, game_id: int) -> Dict:
        return self._request(f"/play_by_play/{game_id}")

    def get_innings(self, game_id: int) -> List[Dict]:
        return self._request(f"/innings/{game_id}")


# Shorter alias
MLBData = MLBAdapter
