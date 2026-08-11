# TC Sports Betting Pipeline — Definitive System Integration v1.0

**Date**: 2026-08-11  
**Status**: LIVE — 3,151 picks generated for 8/11

---

## Architecture

```
daily_picks.py (entry point)
├── MLB: statsapi → tc_math.py → projections → picks
├── WNBA: nba_api (WNBA LeagueID=10) + ESPN → projections → picks
├── grading: sports_grading_engine.py + grade_wnba_sportypy.py
├── regrade: src/regrade_all_outstanding.py --date YYYY-MM-DD --force
├── DB: data/picks.db (SQLite, UNIQUE index on date+league+player+stat+matchup+direction+source)
└── dashboard: streamlit (localhost:8510) + zo.space + tc-api
```

## Schema (picks table)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| date | TEXT | Game date |
| league | TEXT | MLB / WNBA / NBA / NFL |
| player | TEXT | Player full name |
| team | TEXT | Team abbreviation |
| stat | TEXT | PTS / REB / AST / HR / K / etc. |
| tc_projection | REAL | TC model projection |
| market_line | REAL | Market line (odds-derived) |
| edge | REAL | tc_projection - market_line |
| abs_edge | REAL | ABS(edge) capped at 10.0 |
| direction | TEXT | OVER / UNDER |
| matchup | TEXT | team_at_team |
| hit | INTEGER | 1=hit, 0=miss, NULL=pending |
| actual | REAL | Actual stat from boxscore |
| p_hit | REAL | Projected hit probability |
| tier | TEXT | RED/YELLOW/GREEN |
| source | TEXT | SELF_EDGE |

## Key Functions

### add_combo_stats(boxscore)
```python
def add_combo_stats(boxscore):
    """Add PA, PR, PRA to each player's stats."""
    for player, stats in boxscore.items():
        pts = stats.get('PTS', 0) or 0
        reb = stats.get('REB', 0) or 0
        ast = stats.get('AST', 0) or 0
        stats['PA'] = pts + ast
        stats['PR'] = pts + reb
        stats['PRA'] = pts + reb + ast
    return boxscore
```

### fetch_mlb_boxscore(game_id)
```python
def fetch_mlb_boxscore(game_id):
    """Fetch MLB boxscore and merge batting + pitching stats."""
    import statsapi
    data = statsapi.boxscore_data(game_id)
    players = {}
    for player_id, info in data.get('players', {}).items():
        name = info.get('fullName', '')
        batting = info.get('stats', {}).get('batting', {})
        pitching = info.get('stats', {}).get('pitching', {})
        combined = {**pitching, **batting}
        players[name] = combined
    return players
```

## WNBA Grading Pipeline
1. ESPN summary API → game IDs + boxscore data
2. nba_api (WNBA LeagueID=10) → player stats
3. `add_combo_stats()` → PA/PR/PRA
4. Fuzzy name matching against picks
5. Hit/miss determination: OVER hit when actual >= line+0.5
6. DB write: UPDATE picks SET actual=..., hit=...

## MLB Grading Pipeline
1. `statsapi.boxscore_data(game_id)` → players dict
2. Batting + pitching merge (batting overrides pitching on conflicts)
3. Name matching against picks
4. Hit/miss: OVER hit when actual > line
5. DB write

## Regrade
```bash
# Single date:
python3 src/regrade_all_outstanding.py --sport MLB --date 2026-08-10 --force
python3 src/regrade_all_outstanding.py --sport WNBA --date 2026-08-10 --force

# Full integration:
python3 src/final_integration.py --date 2026-08-10 --force
```

## Performance Targets
- Combined hit rate: ≥55.0%
- 8/10 actual: MLB 56.3% (758/1347) | WNBA 67.6% (100/148) | Combined 57.4%

## File Map
| File | Purpose |
|------|---------|
| `Projects/daily_picks.py` | Pipeline entry point |
| `Projects/sports_grading_engine.py` | MLB/NFL grading engine |
| `Projects/grade_wnba_sportypy.py` | WNBA grading via ESPN |
| `Projects/src/regrade_all_outstanding.py` | Batch regrade |
| `Projects/src/final_integration.py` | Full integration script |
| `Projects/data/picks.db` | SQLite picks database |
| `Projects/tc_dashboard.py` | Streamlit dashboard (port 8510) |
| `SYSTEM_INTEGRATION.md` | This document |
