"""
SPORT-SPECIFIC INTELLIGENCE LOGIC
WNBA | NBA | NFL | MLB | NHL | CBB | SOCCER
"""

from typing import Dict, List


class SportIntelligence:
    """Sport-specific intelligence for all sports"""

    def __init__(self):
        self.sport_configs = self._init_sport_configs()
        self.agent_weights = self._init_agent_weights()

    def _init_sport_configs(self) -> Dict:
        return {
            'WNBA': {
                'name': 'WNBA', 'emoji': '🏀',
                'conferences': ['Eastern', 'Western'], 'teams': 15,
                'game_days': ['Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'OT'],
                'stats': ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'FG%', '3P%', 'FT%'],
                'key_features': ['rebounding', 'assists', 'star_impact', 'minutes_consistency'],
                'agent_weights': {
                    'true_rebounding': 0.16, 'true_assists': 0.15, 'true_combos': 0.14,
                    'injury_impact': 0.12, 'defensive_impact': 0.11,
                    'minutes_consistency': 0.10, 'h2h_matchup': 0.08,
                    'scheme_continuity': 0.06, 'chemistry': 0.05, 'momentum': 0.03
                }
            },
            'NBA': {
                'name': 'NBA', 'emoji': '🏀',
                'conferences': ['Eastern', 'Western'], 'teams': 30,
                'game_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'OT'],
                'stats': ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'FG%', '3P%', 'FT%'],
                'key_features': ['pace', 'efg_pct', 'defensive_rating', 'star_impact'],
                'agent_weights': {
                    'statistical': 0.18, 'pace': 0.15, 'defensive': 0.14,
                    'star_impact': 0.12, 'injury': 0.10, 'home_court': 0.08,
                    'matchup': 0.07, 'rest': 0.06, 'momentum': 0.05,
                    'chemistry': 0.04, 'public': 0.01
                }
            },
            'NFL': {
                'name': 'NFL', 'emoji': '🏈',
                'conferences': ['AFC', 'NFC'], 'teams': 32,
                'game_days': ['Thu', 'Sun', 'Mon'],
                'periods': ['Q1', 'Q2', 'Q3', 'Q4', 'OT'],
                'stats': ['Pass Yds', 'Rush Yds', 'Rec Yds', 'TD', 'INT', 'Sacks'],
                'key_features': ['turnovers', 'yards_per_play', 'third_down', 'qb_rating'],
                'agent_weights': {
                    'sharp_money': 0.16, 'statistical': 0.15, 'turnovers': 0.14,
                    'defensive': 0.12, 'injury': 0.10, 'home_court': 0.08,
                    'weather': 0.07, 'matchup': 0.06, 'momentum': 0.05,
                    'public': 0.04, 'chemistry': 0.03
                }
            },
            'MLB': {
                'name': 'MLB', 'emoji': '⚾',
                'conferences': ['American', 'National'], 'teams': 30,
                'game_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'periods': ['Top 1', 'Bot 1', 'Top 2', 'Bot 2'],
                'stats': ['H', 'R', 'RBI', 'HR', 'SB', 'ERA', 'WHIP', 'K'],
                'key_features': ['pitching', 'bullpen', 'hitting', 'defense'],
                'agent_weights': {
                    'pitching': 0.20, 'bullpen': 0.15, 'hitting': 0.14,
                    'defense': 0.12, 'injury': 0.10, 'home_court': 0.08,
                    'matchup': 0.07, 'weather': 0.06, 'momentum': 0.05, 'public': 0.03
                }
            },
            'NHL': {
                'name': 'NHL', 'emoji': '🏒',
                'conferences': ['Eastern', 'Western'], 'teams': 32,
                'game_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'periods': ['P1', 'P2', 'P3', 'OT', 'SO'],
                'stats': ['G', 'A', 'PTS', 'SOG', 'SV', 'GAA', 'SV%'],
                'key_features': ['goal_diff', 'power_play', 'penalty_kill', 'save_pct'],
                'agent_weights': {
                    'goal_diff': 0.18, 'power_play': 0.16, 'penalty_kill': 0.14,
                    'goalie': 0.12, 'injury': 0.10, 'home_court': 0.08,
                    'matchup': 0.07, 'momentum': 0.06, 'public': 0.05, 'chemistry': 0.04
                }
            },
            'SOCCER': {
                'name': 'SOCCER', 'emoji': '⚽',
                'conferences': ['Premier League', 'La Liga', 'Serie A', 'Bundesliga'],
                'teams': 20,
                'game_days': ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                'periods': ['H1', 'H2', 'ET', 'PK'],
                'stats': ['G', 'A', 'SOG', 'PASS', 'TACK', 'CLR', 'SAV'],
                'key_features': ['xg', 'possession', 'shots_on_target', 'defensive'],
                'agent_weights': {
                    'xg': 0.18, 'possession': 0.16, 'shots_on_target': 0.14,
                    'defensive': 0.12, 'injury': 0.10, 'home_court': 0.08,
                    'matchup': 0.07, 'momentum': 0.06, 'public': 0.05, 'chemistry': 0.04
                }
            }
        }

    def _init_agent_weights(self) -> Dict:
        return self.sport_configs['NBA']['agent_weights']

    def get_sport_config(self, sport: str) -> Dict:
        return self.sport_configs.get(sport, {})

    def get_agent_weights(self, sport: str) -> Dict:
        config = self.get_sport_config(sport)
        return config.get('agent_weights', self.agent_weights)

    def get_key_features(self, sport: str) -> List:
        config = self.get_sport_config(sport)
        return config.get('key_features', [])

    def get_sport_signal_logic(self, sport: str) -> Dict:
        sport_configs = {
            'WNBA': {
                'primary_color': '#FF1493',
                'signal_thresholds': {
                    'high_edge': 0.12, 'medium_edge': 0.06,
                    'high_confidence': 0.72, 'medium_confidence': 0.58,
                    'high_win_prob': 0.62, 'medium_win_prob': 0.48
                },
                'key_metrics': ['rebounding', 'assists', 'star_impact', 'minutes']
            },
            'NBA': {
                'primary_color': '#FF6B00',
                'signal_thresholds': {
                    'high_edge': 0.10, 'medium_edge': 0.05,
                    'high_confidence': 0.70, 'medium_confidence': 0.55,
                    'high_win_prob': 0.60, 'medium_win_prob': 0.45
                },
                'key_metrics': ['pace', 'efg_pct', 'defensive_rating']
            },
            'NFL': {
                'primary_color': '#004C97',
                'signal_thresholds': {
                    'high_edge': 0.10, 'medium_edge': 0.05,
                    'high_confidence': 0.70, 'medium_confidence': 0.55,
                    'high_win_prob': 0.60, 'medium_win_prob': 0.45
                },
                'key_metrics': ['turnovers', 'yards_per_play', 'qb_rating']
            },
            'MLB': {
                'primary_color': '#003B6F',
                'signal_thresholds': {
                    'high_edge': 0.12, 'medium_edge': 0.06,
                    'high_confidence': 0.68, 'medium_confidence': 0.54,
                    'high_win_prob': 0.58, 'medium_win_prob': 0.44
                },
                'key_metrics': ['pitching', 'bullpen', 'hitting']
            },
            'NHL': {
                'primary_color': '#002F6C',
                'signal_thresholds': {
                    'high_edge': 0.10, 'medium_edge': 0.05,
                    'high_confidence': 0.70, 'medium_confidence': 0.55,
                    'high_win_prob': 0.60, 'medium_win_prob': 0.45
                },
                'key_metrics': ['goal_diff', 'power_play', 'save_pct']
            },
            'SOCCER': {
                'primary_color': '#00AA44',
                'signal_thresholds': {
                    'high_edge': 0.12, 'medium_edge': 0.06,
                    'high_confidence': 0.68, 'medium_confidence': 0.54,
                    'high_win_prob': 0.58, 'medium_win_prob': 0.44
                },
                'key_metrics': ['xg', 'possession', 'shots_on_target']
            }
        }
        return sport_configs.get(sport, sport_configs['NBA'])

    def calculate_signal_strength(self, edge: float, confidence: float, win_prob: float) -> Dict:
        if edge >= 0.10:
            edge_strength, edge_color = 'high', '#00FF88'
        elif edge >= 0.05:
            edge_strength, edge_color = 'medium', '#FFAA00'
        else:
            edge_strength, edge_color = 'low', '#FF4444'

        if confidence >= 0.70:
            conf_strength, conf_color = 'high', '#00FF88'
        elif confidence >= 0.55:
            conf_strength, conf_color = 'medium', '#FFAA00'
        else:
            conf_strength, conf_color = 'low', '#FF4444'

        if win_prob >= 0.60:
            prob_strength, prob_color = 'high', '#00FF88'
        elif win_prob >= 0.45:
            prob_strength, prob_color = 'medium', '#FFAA00'
        else:
            prob_strength, prob_color = 'low', '#FF4444'

        strengths = [edge_strength, conf_strength, prob_strength]
        if all(s == 'high' for s in strengths):
            overall, overall_color = 'high', '#00FF88'
        elif any(s == 'low' for s in strengths):
            overall, overall_color = 'low', '#FF4444'
        else:
            overall, overall_color = 'medium', '#FFAA00'

        return {
            'overall': overall, 'overall_color': overall_color,
            'edge': {'strength': edge_strength, 'color': edge_color},
            'confidence': {'strength': conf_strength, 'color': conf_color},
            'win_prob': {'strength': prob_strength, 'color': prob_color}
        }
