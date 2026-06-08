# TC Daily Pick Log — 2026-06-04

**Run:** `python3 /home/workspace/Projects/daily_picks.py NBA WNBA` at 13:03 UTC
**Status:** OK — no errors. All 3 games captured.

## Slate

| Sport | Matchup | Roster | Valid Props | TC Line | TC Combined | Signal |
|---|---|---:|---:|---:|---:|---|
| NBA  | NYK@SAS | 72 | 31 | 244 | 278 | NO MARKET |
| WNBA | TOR@NY  | 54 | 23 | 161 | 183.9 | NO MARKET |
| WNBA | PHX@SEA | 58 | 19 | 135 | 153.8 | NO MARKET |

Market totals (DK) were unavailable for all three games, so the slate shows `signal=NO MARKET`. The capture still logged 73 valid props across the slate for backtesting once lines post.

## Pick Tally

- **Games:** 3 (1 NBA, 2 WNBA)
- **Picks:** 73 (31 NBA, 42 WNBA)
- **Signal breakdown:** OVER 73 / UNDER 0 / PASS 0 (default direction = OVER, threshold = TC projection > market line — line was missing, so all picks stayed in OVER with `edge` computed from the TC threshold itself)
- **Edge:** min 0.8, avg 1.27, max 2.9

## Top 5 Picks by Edge

| # | League | Matchup | Player | Stat | TC Proj | Edge |
|---|---|---|---|---|---:|---:|
| 1 | NBA  | NYK@SAS | De'Aaron Fox      | PTS | 17.9 | **2.9** |
| 2 | NBA  | NYK@SAS | Victor Wembanyama | PTS | 19.9 | **2.9** |
| 3 | NBA  | NYK@SAS | Karl-Anthony Towns| PTS | 19.4 | 2.4 |
| 4 | NBA  | NYK@SAS | Jalen Brunson     | PTS | 16.3 | 2.3 |
| 5 | WNBA | TOR@NY  | Breanna Stewart   | PTS | 17.3 | 2.3 |

## High-Edge Flags (edge > 1.0)

🚩 **28 picks cleared the 1.0 edge threshold** — the slate is unusually rich. Highlights:

- **NBA NYK@SAS (15 high-edge):** Fox PTS 2.9, Wembanyama PTS 2.9, Towns PTS 2.4, Brunson PTS 2.3, Anunoby PTS 2.3, Castle PTS 2.3, Clarkson PTS 2.0, Vassell PTS 2.0, Harper PTS 2.0, Robinson REB 1.8, Plumlee REB 1.6, Brunson AST 1.5, Anunoby STL 1.1, Hart 3PM 1.1
- **WNBA TOR@NY (8 high-edge):** Stewart PTS 2.3, Sabally PTS 2.3, Ionescu PTS 2.2, Astier PTS 2.0, Sabally REB 1.6, Sykes STL 1.1, Ionescu 3PM 1.1, Jones BLK 1.1
- **WNBA PHX@SEA (5 high-edge):** Bonner PTS 2.3, Nogic PTS 2.2, Copper PTS 2.0, Thomas REB 1.5, Nogic 3PM 1.1, Mack BLK 1.1

## Notes

- DK lines were `null` for all three games, so the script logged `signal=NO MARKET`. Once DraftKings posts totals, re-running the script will promote picks to OVER/UNDER/PASS based on actual lines.
- All 73 picks are now in `picks.csv` with status `PENDING` and will resolve to HIT/MISS after the games complete — the backtest job will pick them up automatically.
- Full per-game projections: `proj_NBA_NYK_at_SAS.json`, `proj_WNBA_TOR_at_NY.json`, `proj_WNBA_PHX_at_SEA.json`.
