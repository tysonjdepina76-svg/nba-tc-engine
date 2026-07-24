TC SPORTS PICKS REPORT — 2026-07-22
=====================================

PIPELINE STATUS: HEALTHY
Total: 1,210 picks (270 MLB + 940 WNBA) — WC: no matches

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MLB — 270 picks across 5 games
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Matchups: ARI@STL, KC@DET, MIN@CLE, SD@ATL, TB@TOR
Direction: 270 OVER / 0 UNDER
Signal: 100% SELF_EDGE (no real market lines available)

TOP MLB EDGES:
  Shohei Ohtani (LAD) — KC@DET
    TB | proj=1.96 line=0.0 edge=1.96 | OVER
  Yordan Alvarez (HOU) — MIN@CLE
    TB | proj=1.94 line=0.0 edge=1.94 | OVER
  Aaron Judge (NYY) — TB@TOR
    TB | proj=1.94 line=0.0 edge=1.94 | OVER
  Ronald Acuna (ATL) — ARI@STL
    TB | proj=1.92 line=0.0 edge=1.92 | OVER
  Aaron Judge (NYY) — MIN@CLE
    TB | proj=1.92 line=0.0 edge=1.92 | OVER
  Juan Soto (NYM) — KC@DET
    TB | proj=1.88 line=0.0 edge=1.88 | OVER
  Shohei Ohtani (LAD) — ARI@STL
    TB | proj=1.87 line=0.0 edge=1.87 | OVER
  Vladimir Guerrero (TOR) — KC@DET
    TB | proj=1.87 line=0.0 edge=1.87 | OVER
  Bryce Harper (PHI) — SD@ATL
    TB | proj=1.85 line=0.0 edge=1.85 | OVER
  Corey Seager (TEX) — SD@ATL
    TB | proj=1.79 line=0.0 edge=1.79 | OVER

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WNBA — 940 picks across 5 games  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Matchups: CHI_at_NY, CON_at_IND, LV_at_WSH, MIN_at_SEA, PHX_at_LA
Direction: 940 OVER / 0 UNDER
Signal: 100% SELF_EDGE (no real market lines available)

TOP WNBA EDGES:
  Azura Stevens (CHI) — CHI_at_NY
    PTS | proj=8.0 line=7.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    3PM | proj=0.0 line=-0.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    REB | proj=6.0 line=5.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    AST | proj=3.0 line=2.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    TO | proj=2.0 line=1.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    STL | proj=2.0 line=1.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    BLK | proj=2.0 line=1.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    OREB | proj=0.0 line=-0.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    DREB | proj=6.0 line=5.5 edge=0.5 | OVER
  Azura Stevens (CHI) — CHI_at_NY
    PF | proj=4.0 line=3.5 edge=0.5 | OVER

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA SOURCES & INTEGRITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MLB: ESPN boxscore → TC projections (5 games, 30 players)
WNBA: ESPN boxscore → TC projections (5 games, 94 players)
WC: No World Cup matches today
SerpAPI: Quota maxed (540/253 daily) — all picks SELF_EDGE
Odds API: Business tier quota maxed
Free APIs (statsapi/pybaseball/nba_api): Wired, enriching

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES APPLIED TODAY (7/22)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. WNBA projection extraction fixed — correct team mapping via ESPN boxscore
2. Team lookup: Brittney Griner → ATL, Natasha Cloud → CHI, Dana Evans → LV
3. Aaliyah Edwards team verified → WSH (correct)
4. Combined WNBA file skip — eliminates duplicate entries
5. backfill_projections.py date hardcode removed — auto-uses today
6. gen_wnba_today.py combined file now includes per-player matchup data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAVEATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ All picks are SELF_EDGE — TC projections only, no real sportsbook lines
⚠ No market context available until SerpAPI quota resets (~8/1)
⚠ DAL@POR WNBA game had no players yet (not started at projection time)

Report generated: 2026-07-23 00:43:24 ET
Picks files: data/picks/mlb_2026-07-22.csv, data/picks/wnba_2026-07-22.csv
Dashboard: https://true.zo.space/nba-tc
