# NBA TC Backtest Log — April 29, 2026

> Fill in ACTUAL scores after each game to measure TC model accuracy.

---

## TC PROJECTIONS (Pre-Game)

| \# | Game | Date | Network | Series | Pick | TC Total | Game Line | Edge | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ORL @ DET | Apr 29 | Amazon Prime | ORL leads 3-1 | DET -4 | 187.0 | 208 | \-21.0 UNDER | *pending* |
| 2 | TOR @ CLE | Apr 29 | TNT | Tied 2-2 | CLE -8.5 | 193.4 | 215.5 | \-22.1 UNDER | *pending* |
| 3 | HOU @ LAL | Apr 29 | ESPN | LAL leads 3-1 | LAL -4 | 167.7 | 218 | \-50.3 UNDER | *pending* |

---

## BACKTEST ENTRY — Fill After Each Game

### Game 1: ORL @ DET

| Field | Value |
| --- | --- |
| **Actual Score** | ORL \__\_ / DET \__\_ |
| **Actual Total** |  |
| **TC Projection** | 187.0 |
| **Pick** | UNDER 208 |
| **Result** | WIN / LOSS / PUSH |
| **Edge (Actual - Line)** |  |
| **Notes** |  |

---

### Game 2: TOR @ CLE

| Field | Value |
| --- | --- |
| **Actual Score** | TOR \__\_ / CLE \__\_ |
| **Actual Total** |  |
| **TC Projection** | 193.4 |
| **Pick** | UNDER 215.5 |
| **Result** | WIN / LOSS / PUSH |
| **Edge (Actual - Line)** |  |
| **Notes** |  |

---

### Game 3: HOU @ LAL

| Field | Value |
| --- | --- |
| **Actual Score** | HOU \__\_ / LAL \__\_ |
| **Actual Total** |  |
| **TC Projection** | 167.7 |
| **Pick** | UNDER 218 |
| **Result** | WIN / LOSS / PUSH |
| **Edge (Actual - Line)** |  |
| **Notes** |  |

---

## SEASON TOTALS (Update After Each Game)

| Metric | Value |
| --- | --- |
| Games Played | 0 |
| ATS Wins | 0 |
| ATS Losses | 0 |
| ATS Pushes | 0 |
| Under Wins | 0 |
| Under Losses | 0 |
| Under Pushes | 0 |
| Total Units | 0 |

---

## HOW TO USE THIS LOG

1. **Before the game** — projections are locked in `file nba_tc_template_v5.py` and `file NBA_TC_Projections_Apr29_2026.md`
2. **After the game** — fill in actual scores and calculate:
   - `Actual Total = Away Score + Home Score`
   - `Edge = TC Total - Game Line` (what we projected)
   - `Actual Edge = Actual Total - Game Line` (what actually happened)
3. **Compare** — did the edge lean hold? Did the UNDER hit?

---

*Generated: April 29, 2026*
*Files: `file nba_tc_template_v5.py` | `file NBA_TC_Projections_Apr29_2026.md` | `file nba_tc_rosters_apr29.csv`*