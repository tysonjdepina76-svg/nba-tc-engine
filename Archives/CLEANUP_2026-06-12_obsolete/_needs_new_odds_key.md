# Pipeline Status — Key Not Found

**Last verified:** 2026-06-08 ~23:58 UTC

## What was tested
- `ODDS_API_KEY=toa_live_t5d8p3n1` (in `/root/.zo/secrets.env`) → 401 INVALID_KEY
- `SPORTS_DATA_IO_KEY=2888700f9bce4c41ad074e26b505f9b3` (just added) → 401/404 across 8 endpoints

**Neither key works against The Odds API or sportsdata.io WNBA data.**

## What the pipeline needs

The new `ODDS_API_KEY` value (e.g., a 32+ char `toa_live_...` or `xxx-xxx-xxx-...` style string).

**Where to add it** (one of these):
1. Reply to the chat with the key in plain text — I'll write it to the file and re-verify
2. Settings → Advanced → Secrets → add `ODDS_API_KEY` with the value
3. Direct terminal:  `echo 'ODDS_API_KEY=<new_key>' >> /root/.zo/secrets.env`

## What works today (without the new key)
- 16 NBA DK player props (SGO + ESPN tier 1+2)
- Game total/ML/spread (ESPN DraftKings embedded)
- 0 WNBA DK lines — same SGO NBA-only limit, no WNBA fallback yet

## What unlocks with a working `ODDS_API_KEY`
- WNBA player props (PTS/REB/AST/3PM/STL/BLK) via The Odds API v4
- Expected: ~70-100 WNBA DK props/day for the 2-3 in-progress games
- The 3-tier odds fallback in `/api/tc` will then be 100% active (SGO → ESPN → Odds API)

## Verification
```bash
curl -s "https://api.the-odds-api.com/v4/sports/basketball_wnba/events?apiKey=<NEW_KEY>"
# Expected: 200 with array of events
```
