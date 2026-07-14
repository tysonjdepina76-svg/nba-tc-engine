# ==================== nfl_combos.py ====================
class NFLComboGenerator:
    """NFL-specific combo generation with TC logic"""
    
    def __init__(self, tc_model):
        self.tc_model = tc_model
        self.team_stats = {}
        self.player_stats = {}
        
    def generate_nfl_combos(self, game_data: dict) -> list:
        """Generate NFL-specific combos"""
        combos = []
        qb_combos = self._generate_qb_combos(game_data)
        combos.extend(qb_combos)
        drive_combos = self._generate_drive_combos(game_data)
        combos.extend(drive_combos)
        turnover_combos = self._generate_turnover_combos(game_data)
        combos.extend(turnover_combos)
        td_combos = self._generate_td_combos(game_data)
        combos.extend(td_combos)
        return combos
    
    def _generate_qb_combos(self, game_data: dict) -> list:
        combos = []
        for qb in game_data.get('qbs', []):
            if qb.get('passing_yards_line', 250) > 250:
                combos.append({
                    'type': 'QB Performance Combo',
                    'player': qb['name'],
                    'legs': [
                        f"{qb['name']} Over {qb.get('passing_yards_line', 250)} Yards",
                        f"{qb['name']} Over {qb.get('td_line', 1.5)} TDs"
                    ],
                    'correlation': 0.55,
                    'tc_score': self._calculate_qb_tc_score(qb, game_data)
                })
            for wr in game_data.get('receivers', []):
                if wr.get('team') == qb.get('team'):
                    combos.append({
                        'type': 'QB-WR Stack',
                        'qb': qb['name'],
                        'wr': wr['name'],
                        'legs': [
                            f"{qb['name']} Over {qb.get('passing_yards_line', 250)} Yards",
                            f"{wr['name']} Over {wr.get('receiving_yards_line', 75)} Yards"
                        ],
                        'correlation': 0.72,
                        'tc_score': self._calculate_stack_score(qb, wr, game_data)
                    })
        return combos
    
    def _generate_drive_combos(self, game_data: dict) -> list:
        combos = []
        teams = game_data.get('teams', [])
        for team in teams:
            drive_score = team.get('drive_score', 2.0)
            total_drives = team.get('total_drives', 12)
            if drive_score > 2.5 and total_drives > 10:
                combos.append({
                    'type': 'Drive Efficiency Combo',
                    'team': team['name'],
                    'legs': [
                        f"{team['name']} Over {team.get('total_score_line', 24)} Points",
                        f"{team['name']} Over {team.get('first_half_line', 13)} First Half Points"
                    ],
                    'correlation': 0.8,
                    'tc_score': self._calculate_drive_tc_score(team, game_data)
                })
        return combos
    
    def _generate_turnover_combos(self, game_data: dict) -> list:
        combos = []
        teams = game_data.get('teams', [])
        for team in teams:
            turnovers_forced = team.get('turnovers_forced', 1.5)
            turnover_line = team.get('turnover_line', 1.5)
            if turnovers_forced > turnover_line:
                combos.append({
                    'type': 'Turnover Combo',
                    'team': team['name'],
                    'legs': [
                        f"{team['name']} Over {turnover_line} Turnovers Forced",
                        f"{team['name']} ML"
                    ],
                    'correlation': 0.58,
                    'tc_score': self._calculate_turnover_tc_score(team, game_data)
                })
        return combos
    
    def _generate_td_combos(self, game_data: dict) -> list:
        combos = []
        for player in game_data.get('players', []):
            if player.get('td_probability', 0) > 0.4:
                combos.append({
                    'type': 'TD + ML Combo',
                    'player': player['name'],
                    'team': player['team'],
                    'legs': [
                        f"{player['name']} Anytime TD",
                        f"{player['team']} ML"
                    ],
                    'correlation': 0.62,
                    'tc_score': player.get('td_probability', 0) * 1.5
                })
        return combos
    
    def _calculate_qb_tc_score(self, qb: dict, game_data: dict) -> float:
        ol_continuity = game_data.get('ol_continuity', 0.5)
        wr_synergy = qb.get('wr_synergy', 0.5)
        home_factor = 1.0 if qb.get('home', False) else 0.95
        return (ol_continuity + wr_synergy) / 2 * home_factor
    
    def _calculate_stack_score(self, qb: dict, wr: dict, game_data: dict) -> float:
        qb_score = self._calculate_qb_tc_score(qb, game_data)
        wr_score = wr.get('target_share', 0.25) * 2
        connection_rating = wr.get('connection_rating', 0.5)
        return (qb_score + wr_score + connection_rating) / 3
    
    def _calculate_drive_tc_score(self, team: dict, game_data: dict) -> float:
        ol_continuity = game_data.get('ol_continuity', 0.5)
        run_block_cohesion = game_data.get('run_block_cohesion', 0.5)
        return (ol_continuity + run_block_cohesion) / 2
    
    def _calculate_turnover_tc_score(self, team: dict, game_data: dict) -> float:
        defensive_communication = game_data.get('defensive_communication', 0.5)
        turnover_rate = team.get('turnover_rate', 0.5)
        return (defensive_communication + turnover_rate) / 2
