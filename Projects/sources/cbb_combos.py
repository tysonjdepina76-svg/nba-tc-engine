# ==================== cbb_combos.py ====================
class CBBComboGenerator:
    """College Basketball combo generation with TC logic"""
    
    def __init__(self, tc_model):
        self.tc_model = tc_model
        self.team_stats = {}
        self.player_stats = {}
        
    def generate_cbb_combos(self, game_data: dict) -> list:
        combos = []
        combos.extend(self._generate_player_combos(game_data))
        combos.extend(self._generate_team_combos_cbb(game_data))
        combos.extend(self._generate_neutral_site_combos(game_data))
        return combos
    
    def _generate_player_combos(self, game_data: dict) -> list:
        combos = []
        for player in game_data.get('players', []):
            if player.get('points_projection', 10) > 10:
                combos.append({
                    'type': 'PRA Combo',
                    'player': player['name'],
                    'legs': [
                        f"{player['name']} Over {player.get('points_line', 10)} Points",
                        f"{player['name']} Over {player.get('rebounds_line', 4)} Rebounds",
                        f"{player['name']} Over {player.get('assists_line', 2)} Assists"
                    ],
                    'correlation': 0.4,
                    'tc_score': self._calculate_cbb_player_score(player, game_data)
                })
        return combos
    
    def _generate_team_combos_cbb(self, game_data: dict) -> list:
        combos = []
        teams = game_data.get('teams', [])
        for team in teams:
            star_player = team.get('star_player', None)
            if star_player:
                combos.append({
                    'type': 'Team + Star Combo',
                    'team': team['name'],
                    'player': star_player['name'],
                    'legs': [
                        f"{team['name']} Over {team.get('team_total_line', 70)} Points",
                        f"{star_player['name']} Over {star_player.get('points_line', 15)} Points"
                    ],
                    'correlation': 0.55,
                    'tc_score': self._calculate_cbb_team_score(team, game_data)
                })
        return combos
    
    def _generate_neutral_site_combos(self, game_data: dict) -> list:
        if game_data.get('neutral_site', False):
            return [{
                'type': 'Neutral Site Combo',
                'legs': [
                    f"Under {game_data.get('total_line', 140)}",
                    f"{game_data.get('home_team')} ML"
                ],
                'correlation': 0.3,
                'tc_score': 0.7,
                'neutral_advantage': 0.1
            }]
        return []
    
    def _calculate_cbb_player_score(self, player: dict, game_data: dict) -> float:
        usage_rate = player.get('usage_rate', 0.2)
        experience = min(1.0, player.get('years_experience', 1) / 4)
        matchup_score = player.get('matchup_score', 0.5)
        return (usage_rate * 0.5 + experience * 0.3 + matchup_score * 0.2)
    
    def _calculate_cbb_team_score(self, team: dict, game_data: dict) -> float:
        continuity = team.get('continuity', 0.5)
        conference_factor = 1.0 if team.get('conference_game', False) else 0.95
        home_factor = 1.0 if team.get('home', False) else 0.90
        return (continuity * 0.5 + conference_factor * 0.3 + home_factor * 0.2)
