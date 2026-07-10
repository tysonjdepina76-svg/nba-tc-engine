# Sport Shows — Stat Menus to Show

Source: text from Tyson, 2026-06-30. Wired into `sport_config.py` same day.

## Universal (every sport)
- PTS (Points)
- REB (Rebounds)
- AST (Assists)
  - _Show's universal trio — these are basketball-style labels carried across all shows; map to sport equivalents where appropriate._

## MLB (`_MLB_STATS` in sport_config.py)
- AVG — Batting Average (0.0–1.0)
- HR — Home Runs
- RBI — RBIs
- SB — Stolen Bases
- OPS — On-Base Plus Slugging (0.0–1.5)
- ERA — Earned Run Average (Pitcher)
- _Kept for pipeline: hits, runs, SO (P)_

## SOCCER (`_SOCCER_STATS`)
- G — Goals
- A — Assists
- SH — Shots
- SOT — Shots on Target
- PASS — Passes
- TKL — Tackles
- Cards — Yellow Cards + Red Cards

## NHL (`_NHL_STATS`)
- G — Goals
- A — Assists
- PTS — Points
- +/- — Plus/Minus
- SH — Shots on Goal
- HIT — Hits
- PIM — Penalty Minutes
- _Kept for pipeline: saves (G)_

## NFL (`_NFL_STATS`)
- PASS YDS — Passing Yards
- RUSH YDS — Rushing Yards
- REC YDS — Receiving Yards
- TD — Passing TDs + Rushing TDs + Receiving TDs
- INT — Interceptions (currently `pass_int`)
- _Other NFL stats kept: receptions, targets, fantasy_pts (PPR)_

## Status
- 2026-06-30: MLB added AVG/OPS/ERA, NHL added +/-/HIT/PIM, SOCCER added yellow/red cards
- NFL: `pass_int` key already present (matches INT from show menu)
- NBA/WNBA PTS/REB/AST already wired (universal trio)
