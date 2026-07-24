# TC Math Truth Weights
# From tc_math_truth.py - NBA Offensive Criteria
OFFENSIVE_WEIGHTS = {
    "points_scored": 0.25,           # Raw scoring output
    "efg_percentage": 0.20,           # Effective FG% (accounts for 3PT value)
    "pace_rating": 0.15,              # Possessions per game
    "assist_rate": 0.10,              # Ball movement efficiency
    "offensive_rebounding": 0.10,     # Second chance opportunities
    "free_throw_rate": 0.08,          # Getting to the line
    "turnover_rate": -0.07,           # Negative weight (giveaways)
    "three_point_rate": 0.05          # 3PA/FGA ratio
}

# From tc_math_truth.py - NBA Defensive Criteria
DEFENSIVE_WEIGHTS = {
    "opponent_points": 0.25,          # Points allowed
    "opponent_efg": 0.20,             # Opponent FG% effectiveness
    "defensive_rebounding": 0.18,     # Limiting second chances
    "steal_rate": 0.12,               # Creating turnovers
    "block_rate": 0.10,               # Rim protection
    "opponent_ft_rate": 0.08,         # Foul prevention
    "opponent_assist_rate": 0.07      # Disrupting ball movement
}

# From tc_math_truth.py - NFL Offensive Criteria
OFFENSIVE_ELEMENTS = {
    "yards_per_play": 0.20,           # Efficiency metric
    "points_per_drive": 0.18,         # Scoring efficiency
    "passing_yards": 0.12,            # Air attack
    "rushing_yards": 0.10,            # Ground game
    "third_down_conversion": 0.10,    # Drive sustainability
    "red_zone_efficiency": 0.10,      # TD% in scoring range
    "touchdown_rate": 0.08,           # End zone visits
    "time_of_possession": 0.06,       # Clock control
    "explosive_play_rate": 0.04,      # 20+ yard plays
    "sack_rate_allowed": -0.02        # Negative weight
}

# From tc_math_truth.py - NFL Defensive Criteria
DEFENSIVE_ELEMENTS = {
    "yards_allowed_per_play": 0.20,   # Defensive efficiency
    "points_allowed_per_drive": 0.18, # Scoring prevention
    "passing_yards_allowed": 0.12,    # Secondary performance
    "rushing_yards_allowed": 0.10,    # Front 7 performance
    "turnover_rate": 0.15,            # Takeaway ability
    "third_down_stops": 0.10,         # Getting off field
    "red_zone_stops": 0.08,           # Bend don't break
    "sack_rate": 0.07                 # Pass rush impact
}

# Chemistry (TC) elements - same for both sports
CHEMISTRY_ELEMENTS = {
    "continuity": 0.40,               # Lineup/OL continuity
    "on_off_court_rating": 0.30,      # On-court/field impact
    "assist_chain_rate": 0.20,        # Ball movement (NBA) / OL cohesion (NFL)
    "chemistry_trend": 0.10           # Direction of chemistry
}

# Contextual elements
CONTEXTUAL_ELEMENTS = {
    "rest_days": 0.30,                # Days since last game
    "travel_distance": 0.25,          # Miles traveled
    "back_to_back": -0.20,            # Negative: fatigue
    "home_court": 0.15,               # Home advantage
    "weather": 0.10                   # Weather impact (NFL/MLB)
}

# Composite game criteria
def calculate_nba_game_score(team_data):
    return (
        calculate_offensive_score(team_data) * 0.45 +
        calculate_defensive_score(team_data) * 0.35 +
        calculate_chemistry_score(team_data) * 0.10 +
        calculate_contextual_score(team_data) * 0.10
    )

def calculate_nfl_game_score(team_data):
    return (
        calculate_offensive_score(team_data) * 0.40 +
        calculate_defensive_score(team_data) * 0.35 +
        calculate_chemistry_score(team_data) * 0.15 +
        calculate_contextual_score(team_data) * 0.10
    )

def calculate_offensive_score(team_data):
    """Weighted sum using OFFENSIVE_WEIGHTS (NBA) or OFFENSIVE_ELEMENTS (NFL)"""
    score = 0
    for key, weight in OFFENSIVE_WEIGHTS.items():
        if key in team_data:
            score += team_data[key] * weight
    return max(0, min(100, score * 100))  # 0-100 scale

def calculate_defensive_score(team_data):
    """Weighted sum using DEFENSIVE_WEIGHTS (NBA) or DEFENSIVE_ELEMENTS (NFL)"""
    score = 0
    for key, weight in DEFENSIVE_WEIGHTS.items():
        if key in team_data:
            score += team_data[key] * weight
    return max(0, min(100, score * 100))

def calculate_chemistry_score(team_data):
    """TC chemistry component - player continuity, on/off, assist chains"""
    score = 0
    for key, weight in CHEMISTRY_ELEMENTS.items():
        if key in team_data:
            score += team_data[key] * weight
    return max(0, min(100, score * 100))

def calculate_contextual_score(team_data):
    """Fatigue, travel, rest, weather"""
    score = 0
    for key, weight in CONTEXTUAL_ELEMENTS.items():
        if key in team_data:
            score += team_data[key] * weight
    return max(0, min(100, score * 100))

# From tc_math_truth.py - Complete Game Criteria
def calculate_game_criteria(sport: str, team_data: dict) -> dict:
    """
    Calculate all game criteria elements for TC scoring
    Returns dictionary with individual scores and composite
    """
    result = {}
    
    if sport == "NBA":
        off = calculate_offensive_score(team_data)
        deff = calculate_defensive_score(team_data)
        chem = calculate_chemistry_score(team_data)
        ctx = calculate_contextual_score(team_data)
        
        game_score = off * 0.45 + deff * 0.35 + chem * 0.10 + ctx * 0.10
        
        # NBA-specific checks
        if team_data.get("pace", 100) > 105:
            game_score *= 1.05  # Boost for high-pace teams
        
        if team_data.get("back_to_back", False):
            game_score *= 0.95  # Fatigue penalty
        
        result = {
            "offense": off, "defense": deff,
            "chemistry": chem, "context": ctx,
            "composite": game_score
        }
    
    elif sport == "NFL":
        off = calculate_offensive_score(team_data)
        deff = calculate_defensive_score(team_data)
        chem = calculate_chemistry_score(team_data)
        ctx = calculate_contextual_score(team_data)
        
        game_score = off * 0.40 + deff * 0.35 + chem * 0.15 + ctx * 0.10
        
        # NFL-specific checks
        if team_data.get("turnover_differential", 0) > 0:
            game_score *= 1.10  # Turnover advantage
        
        if team_data.get("strength_of_schedule", 0) > 0.5:
            game_score *= 1.05  # Adjust for SOS
        
        result = {
            "offense": off, "defense": deff,
            "chemistry": chem, "context": ctx,
            "composite": game_score
        }
    
    return result
