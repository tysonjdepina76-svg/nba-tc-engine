# SPORTS TC — PIPELINE WORKFLOW

## Overview
The Sports TC pipeline provides a complete workflow for generating Triple Conservative projections for NBA and WNBA games.

## Pipeline Steps

### 1. SELECT SPORT
```
NBA  → 30 teams (all major US franchises)
WNBA → 13 teams (all major US franchises)
```

### 2. SELECT GAME
```
Format: AWAY @ HOME
Example: NYK @ PHI
```

### 3. LIVE SCRAPE
The system scrapes ESPN for:
- Today's games list
- Injury reports (ACTIVE / Q / OUT)
- Starting lineups (best 5 active players)
- Game odds and lines

### 4. TC CALCULATIONS
```
TC = stat × 0.85
Q  = stat × 0.55
OUT = 0

Outputs per player:
- TC_PTS — projected points
- TC_REB — projected rebounds
- TC_AST — projected assists
- TC_3PM — projected 3-point shots made
```

### 5. OUTPUT
The system prints:
1. **Injury Report** — full roster status
2. **Starting Lineup** — best 5 active players
3. **TC Projections** — all players (PTS/REB/AST/3PM)
4. **Team Totals** — combined TC
5. **ATS Picks** — spread picks
6. **Parlay Legs** — NO O/U, prop bets only

### 6. ARCHIVE
All outputs are timestamped and saved to:
- `sports_tc/archive/` — text files
- `sports_tc/data/backtest_log.csv` — CSV log

## Commands

### Interactive Dashboard
```bash
python /home/workspace/sports_tc/sports_tc.py --dashboard
```

### Single Game
```bash
python /home/workspace/sports_tc/sports_tc.py --sport NBA --game "NYK @ PHI"
python /home/workspace/sports_tc/sports_tc.py --sport WNBA --game "MIN @ DAL"
```

### List Teams
```bash
python /home/workspace/sports_tc/sports_tc.py --sport NBA --list
python /home/workspace/sports_tc/sports_tc.py --sport WNBA --list
```

### Backtest
```bash
python /home/workspace/sports_tc/sports_tc.py --sport NBA --backtest
python /home/workspace/sports_tc/sports_tc.py --sport WNBA --backtest
```

## API Key
- Store in: `~/.zo/secrets.env`
- Variable: `ODDS_API_KEY`
- Used for: live odds fetching (optional)

## Dashboard Features
1. Sport selector (NBA / WNBA)
2. Game selector (list or manual)
3. Live injury report
4. Starting lineup (injury-adjusted)
5. Full roster TC projections (PTS/REB/AST/3PM)
6. ATS picks
7. Parlay legs (no O/U)
8. Archive option