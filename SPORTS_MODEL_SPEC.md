# Sports Projection Engine — Full Algorithm Spec
# Tyson Depina | Zo Computer
# Last updated: 2026-05-31

## Sport-by-Sport Algorithm Reference

---

### 🏀 NBA / WNBA — Player Props (RETAIN TC — our proven engine)

**USE: Triple Conservative (TC) Engine**  
TC is already calibrated for NBA/WNBA player props. Enhance it with the following additions:

#### Core TC Formula (retain)
```
TC_PTS = pts × 0.85 − 3.0
TC Line = floor(TC × 0.88)
Edge = TC − Line
Signal: +4 → OVER | −4 → UNDER | 0 → PASS
Q (questionable) × 0.55 | OUT = 0
```

#### Enhancements to add
```
xMins = a weighted average of last 3, 5, and 10 game minutes
        weighted: 50% last-3, 30% last-5, 20% last-10

Usage Rate Adjustment:
  USG_Adj = (USG% / League Avg USG%) × TC_raw

Pace Adjustment:
  Pace_Factor = Team_Pace / League_Avg_Pace
  TC_Pace_Adj = TC_raw × Pace_Factor

Opponent Defensive Rating Adjustment:
  Opp_DEFFactor = Opp_DEFF / League_Avg_DEFF
  TC_Opponent_Adj = TC_Pace_Adj × (1 − (Opp_DEFFFactor − 1) × 0.15)

Injury GAP Factor (from injury reports):
  If OUT → multiply by 0.0 (remove from projection)
  If Q → multiply by 0.55
  If P (probable) → multiply by 0.85

Final TC = TC_Opponent_Adj × Injury_Factor × xMins_Scale
```

#### Game-Lag Feature Method (from peer-reviewed ML study)
```
For each stat category (PTS, REB, AST, 3PM, STL, BLK):
  L1  = avg(last 1 game)
  L3  = avg(last 3 games)
  L5  = avg(last 5 games)
  L7  = avg(last 7 games)
  L10 = avg(last 10 games)

  Weighted_Lag = 0.35×L3 + 0.25×L5 + 0.20×L7 + 0.12×L10 + 0.08×L1

  Combine Weighted_Lag with TC base → final projection
```

---

### ⚾ MLB — Runs Scored / Pitching

**Algorithm: Poisson Regression with Pythagorean Expectation**

```python
# Batting Runs Expected (BRE)
Team_ABV = Avg_Batting_Value  # from season stats
Park_Factor = adjust for home park (each stadium different)
Opposing_Pitcher_FIP = xFIP of expected starter

Expected_Runs = Team_ABV × Park_Factor × (1 − Opposing_Pitcher_FIP/12) × 1.05

# Poisson Model for runs distribution
from scipy.stats import poisson

lambda_home = (home_ABV × away_Pitching_FIP × park_factor) / 1.03
lambda_away = (away_ABV × home_Pitching_FIP) / 1.03

# P(OVER total) = 1 − P(X ≤ line)
P_over = 1 − poisson.cdf(line, lambda_home + lambda_away)

# Pitching - Quality Start estimator
QS_prob = sigmoid((5.0 − ERA) × 0.8 + (IP/6) × 0.2)
```

**Key inputs:**
- FIP (Fielding Independent Pitching) — better predictor than ERA
- xFIP (expected FIP, normalized to league average HR/FB)
- wRC+ (weighted Runs Created plus)
- Park factors (Coors Field = 1.15, Petco = 0.95, etc.)
- Bullpen strength (late-inning leverage)

**Props to support:** Strikeouts (K), Innings Pitched, Runs Allowed, Win

---

### 🏈 NFL — Game / Player Props (INTEGRATE EXISTING TEMPLATE)

**Algorithm: EPA-Based Model + Situational Regression**

```python
# Win Probability Model
Win_Prob = sigmoid(
    (Home_EPA_per_play × Home_Pace − Away_EPA_per_play × Away_Pace)
    × 0.12 + Home_Field_Advantage
)

# Key EPA inputs (per play, rolling 5-game avg):
# - Pass EPA (CPOE × 0.4 + Pass_Yards × 0.6 − INT × 0.5)
# - Rush EPA (Yards per carry × 1.2 − Fumble_Rate × 0.3)
# - Defensive EPA (Opponent_Yards − Expected_Yards)

# Situational adjustments:
Two_Minute_Drill_Bonus = +0.08 EPA per play
Short_Yardage_Percent = Rush_Success_Rate × 1.15
Red_Zone_Conversion = TD_Rate / Opponent_RZ_Defense_Rate

# Player props:
QB: Expected_Passing_Yards = Adj_Pass_Att × Adj_YPA × (1 + Two_Min_Warning × 0.05)
RB: Expected_Rush_Yards = Rush_Carries × YPC × Short_Yardage_Bonus
WR: Expected_Receptions = Targets × Catch_Rate × Opponent_Pass_Defense_Allow
```

**Props to support:** Passing yards, Rushing yards, Receiving yards, TDs, INTs, Longest

---

### 🏀 NCAAB — Game Outcome Prediction

**Algorithm: Adjusted Efficiency + Temporalized Massey Method + LSTM**

```python
# Pomeroy-style adjusted efficiencies
AdjOE = Points_Scored / Possessions × 100
AdjDE = Points_Allowed / Possessions × 100
Net_Rating = AdjOE − AdjDE

# Massey Rating (solves Mr = p via least squares)
# M = D − A (D = diagonal of games played, A = head-to-head matrix)
# p = cumulative point differential
 Massey_Rating = solve(M + λI)⁻¹ × p

# Temporalized Massey (accounts for when games happened)
r_i(t) = α × r_i(t−1) + β × s_i(t) + γ × avg(opponent_ratings_at_time_of_game)

# Four Factors weights (from March Madness study):
ADJOE_weight = 0.35
ADJDE_weight = 0.30
Power_Rating  = 0.20
Two_Point_Pct_Allowed = 0.15

Game_Probability = sigmoid(
    (ADJOE_home − ADJDE_away) × 0.05 +
    (ADJOE_away − ADJDE_home) × 0.05 +
    Home_Court × 0.03 +
    Experience_Factor × 0.02
)

# LSTM for game prediction (Transformer for ranking, LSTM for calibration):
# Transformer + BCE: AUC 0.8473 — best for team ranking
# LSTM + Brier: Brier 0.1589 — best for calibrated probabilities
```

**Props to support:** Game totals (OVER/UNDER), spread, team totals

---

### 🏈 NCAAF — Game Outcome Prediction

**Algorithm: G-Elo + MOV Adjusted + Net Rating**

```python
# G-Elo (Generalized Elo with Margin of Victory)
Expected_Score = 1 / (1 + 10^((Opponent_Rating − Self_Rating) / 400))
MOV_Multiplier = log(abs(Margin) + 1) / 7  # capped at ~1.5x

New_Rating = Old_Rating + K × MOV_Multiplier × (Actual − Expected)

# K-factor: 20 for FCS, 25 for FBS
# Home field: +3.0 points for FBS, +2.5 for FCS

# NET Rating for NCAAF:
Net_Rating = (Points_For / Games) − (Points_Against / Games)
             + Strength_of_Schedule_Correction

# Power 5 vs Group of 5 adjustment:
P5_Bonus = 7.0  # points
G5_Bonus = 0.0

Game_Line = Favorite_Rating − Underdog_Rating + Home_Field
```

---

### 🏒 NHL — Goals Scored

**Algorithm: Goal Expectancy + Poisson**

```python
# Goal Expectancy Model
Team_GF = Goals_For_per_game (rolling 10-game)
Team_GA = Goals_Against_per_game (rolling 10-game)
Opp_5v5_GA = Opponent_5v5_Goals_Allowed_per_game

# Adjust for goaltending:
Goal_Allow_Rate = Sv_Pct × (1 − League_Avg_Sv_Pct)

Expected_Goals = (Team_GF × Opp_Defense_Weakness × Special_Teams_Factor) / 1.02

Special_Teams_Factor = (PP_Pct / 100) × (PK_Pct / 100) × 1.1 + 0.9

# 5v5 Corsi adjustment:
Corsi_Factor = (Team_Corsi / 50) × 0.15 + 0.85

# Poisson distribution for goals:
from scipy.stats import poisson
lambda_5v5 = (Home_GF_5v5 + Away_GA_5v5) / 2 × Corsi_Factor

P_over_5.5 = 1 − poisson.cdf(5.5, lambda_5v5)

# Skaters props: Goals, Assists, Points, Shots
Skaters_Expected_Points = ice_time_pct × points_per_60 × (1 / opponent_pk_pct)
```

---

## Competitive Feature Matrix

| Feature | PrizePicks | Rithmm | ParlaySavant | Our App |
|---------|-----------|--------|-------------|---------|
| NBA player props | ✅ | ✅ | ✅ | TC Engine ✅ |
| WNBA player props | ✅ | ✅ | ✅ | TC Engine ✅ |
| MLB props | limited | limited | limited | POISSON ✅ |
| NFL props | ✅ | ✅ | ✅ | EPA Template ✅ |
| NCAAF props | ❌ | limited | ❌ | G-Elo ✅ |
| NCAAB props | limited | limited | limited | Massey + LSTM ✅ |
| NHL props | ❌ | ❌ | ❌ | Goal Exp ✅ |
| Injury reports | ❌ | limited | limited | LIVE SCRAPE ✅ |
| xMins projections | limited | limited | limited | LAG FEATURES ✅ |
| Auto 2hr pre-tip | ❌ | ❌ | ❌ | AUTOMATION ✅ |
| Plain-English report | ❌ | ❌ | ❌ | 6TH GRADE ✅ |
| Live odds integration | limited | ✅ | ✅ | MEDIUM ✅ |
| Custom model builder | ❌ | ✅ | ❌ | PLANNED ✅ |
| Multi-sport single app | limited | ✅ | partial | FULL ✅ |
| Exportable picks | ❌ | ✅ | ✅ | MEDIUM ✅ |
| Parlay builder | limited | limited | ✅ | TC + PARLAY ✅ |
| Line shopping | ❌ | ❌ | ✅ | PLANNED ✅ |
| Bankroll tracker | ❌ | ✅ | ✅ | PLANNED ✅ |

---

## Missing Features / Add-ons to Build

### Phase 1 — Now (MVP)
1. **Injury Report Window** — per team, per sport, real-time scrape
2. **Minute Projections (xMins)** — weighted game-lag model
3. **2-Hour Pre-Tip Automation** — scan all sports, generate reports
4. **Plain-English Report Generator** — 6th grade reading level
5. **Multi-Sport Engine** — MLB, NCAAB, NCAAF, NHL algorithms
6. **Player prop cards** — clean output for each player

### Phase 2 — Next Month
7. **Live Odds Integration** — The Odds API (already skill exists)
8. **Line Shopping** — compare DraftKings, FanDuel, BetMGM, Caesars
9. **Bankroll Tracker** — track picks, win rate, ROI
10. **Parlay Builder** — combine TC props with game totals
11. **Export to PDF/DOCX** — formatted picks report
12. **Push notifications** — SMS/email with picks 2hr before tip

### Phase 3 — Market Ready
13. **Custom Model Builder** — user tweaks weights
14. **Model backtesting suite** — validate TC vs market
15. **Public web dashboard** — host at true.zo.space
16. **API for sharp bettors** — /api/picks endpoint
17. **Social share** — copy-paste picks for Twitter/Discord
18. **Multi-book parlay calculator** — cross-book arbitrage
19. **Fade/Follow sharp money** — track line movement
20. **Weather integration** — NCAAF/NFL outdoor games

---

## Report Format — 6th Grader Style

```
🏀 OKC @ SAS — 8PM ET

━━━ INJURY REPORT ━━━━━━━━━━━━━━━━━━━
OKC: SGA (Q - ankle) — might play, limited minutes
     Chet (OUT - hip) — done for series
SAS: Wemby (PROBABLE) — playing tonight
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 WHAT TO EXPECT (Plain English)
Thunder: They'll play fast, score around 105-112
Spurs: They'll try to run, might get 100-108
Total: Experts think around 210-218 points

🎯 BEST BETS (TC says...)
✓ SGA OVER 24.5 points — he's hot lately
✓ JDub OVER 19.5 rebounds+assists
✗ Wemby 3PM — too many contested shots tonight

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report generated: 5:58 PM ET (2hr before tip)
Source: TC Engine + Live Injury Scrape
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```