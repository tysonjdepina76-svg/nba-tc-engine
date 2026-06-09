---
name: sportsgameodds
description: >-
  Connects to SportsGameOdds (SGO) API to fetch live NBA/WNBA game lines,
  spreads, totals, and player props from DraftKings and other books.
  Primary paid feed for the TC pipeline (cheaper + more data than The Odds API).
  Activate when the user wants live odds, SGO data, or DK scraping.
compatibility: Created for Zo Computer
metadata:
  author: true.zo.computer
---

# SportsGameOdds (SGO)

## Status
✅ **Connected** — key `SPORTSGAMEODDS_API_KEY` loaded from `/root/.zo/secrets.env`
⚠️ **WNBA unavailable** at current subscription tier — NBA works, WNBA shows "leagueID unavailable"
✅ **NBA**: fully functional with SGO v2 API

## Usage
- Events list: `GET /v2/events?leagueID=NBA`
- Player props (per-event): parsed from `oddID` format `{stat}-{PLAYER}-{league}-game-ou-over`
- DK odds extracted via `byBookmaker.draftkings.overUnder`

## Pipeline integration
- `/api/tc` calls this as Tier 1 (PRIMARY paid feed)
- `parseSGOPlayerProps()` extracts DK player prop lines from oddID patterns

## Key files
- `/api/tc` — route handler with SGO parser built-in
