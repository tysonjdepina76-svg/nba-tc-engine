# Boxscore Combo Backtest (REAL Historical DK Lines)

Generated: 2026-06-10 22:55:38 ET

Source: The Odds API **historical** endpoint `/v4/historical/sports/{sport}/events/{eid}/odds?date={commence_time}`
Graded against ESPN final box scores (last 3 days).

**Methodology**: For every completed NBA/WNBA game, pull the snapshot of
DraftKings combo props (PRA/PR/PA) at game-tip time, then grade each side
(Over + Under) against the player's actual box-score combination. This is
a REAL backtest using actual closing lines (not reconstructed).

## Overall

- Games with real closing lines: 3
- Total legs graded: 72
- Hits: 36
- Misses: 36
- Hit rate: 50.0%

## By sport

| sport | games | legs | hits | HR |
|-------|-------|------|------|----|
| WNBA | 3 | 72 | 36 | 50.0% |

## By side

| side | legs | hits | HR |
|------|------|------|----|
| Over | 36 | 17 | 47.2% |
| Under | 36 | 19 | 52.8% |

## By combo type

| type | legs | hits | HR |
|------|------|------|----|
| PA | 24 | 12 | 50.0% |
| PR | 28 | 14 | 50.0% |
| PRA | 20 | 10 | 50.0% |

## By game

### ATL@CHI - 16/32 (50.0%)

| player | team | type | side | line | price | actual | result |
|--------|------|------|------|------|-------|--------|--------|
| Angel Reese | ATL | PA | Over | 17.5 | -125 | 21 | HIT |
| Jordin Canada | ATL | PA | Over | 18.5 | -104 | 20 | HIT |
| Kamilla Cardoso | CHI | PA | Over | 14.5 | -126 | 18 | HIT |
| Natasha Cloud | CHI | PA | Over | 12.5 | -107 | 22 | HIT |
| Angel Reese | ATL | PA | Under | 17.5 | -108 | 21 | miss |
| Jordin Canada | ATL | PA | Under | 18.5 | -131 | 20 | miss |
| Kamilla Cardoso | CHI | PA | Under | 14.5 | -107 | 18 | miss |
| Natasha Cloud | CHI | PA | Under | 12.5 | -127 | 22 | miss |
| Allisha Gray | ATL | PR | Over | 22.5 | -125 | 18 | miss |
| Angel Reese | ATL | PR | Over | 27.5 | -105 | 34 | HIT |
| Azura Stevens | CHI | PR | Over | 16.5 | -119 | 15 | miss |
| Jordin Canada | ATL | PR | Over | 15.5 | -114 | 15 | miss |
| Kamilla Cardoso | CHI | PR | Over | 21.5 | -109 | 15 | miss |
| Natasha Cloud | CHI | PR | Over | 11.5 | -113 | 24 | HIT |
| Naz Hillmon | ATL | PR | Over | 14.5 | -128 | 22 | HIT |
| Allisha Gray | ATL | PR | Under | 22.5 | -109 | 18 | HIT |
| Angel Reese | ATL | PR | Under | 27.5 | -129 | 34 | miss |
| Azura Stevens | CHI | PR | Under | 16.5 | -114 | 15 | HIT |
| Jordin Canada | ATL | PR | Under | 15.5 | -119 | 15 | HIT |
| Kamilla Cardoso | CHI | PR | Under | 21.5 | -125 | 15 | HIT |
| Natasha Cloud | CHI | PR | Under | 11.5 | -120 | 24 | miss |
| Naz Hillmon | ATL | PR | Under | 14.5 | -106 | 22 | miss |
| Allisha Gray | ATL | PRA | Over | 25.5 | -109 | 19 | miss |
| Angel Reese | ATL | PRA | Over | 30.5 | -113 | 38 | HIT |
| Jordin Canada | ATL | PRA | Over | 21.5 | -129 | 21 | miss |
| Natasha Cloud | CHI | PRA | Over | 15.5 | -119 | 28 | HIT |
| Rhyne Howard | ATL | PRA | Over | 24.5 | -129 | 25 | HIT |
| Allisha Gray | ATL | PRA | Under | 25.5 | -125 | 19 | HIT |
| Angel Reese | ATL | PRA | Under | 30.5 | -120 | 38 | miss |
| Jordin Canada | ATL | PRA | Under | 21.5 | -106 | 21 | HIT |
| Natasha Cloud | CHI | PRA | Under | 15.5 | -114 | 28 | miss |
| Rhyne Howard | ATL | PRA | Under | 24.5 | -105 | 25 | miss |

### IND@WSH - 13/26 (50.0%)

| player | team | type | side | line | price | actual | result |
|--------|------|------|------|------|-------|--------|--------|
| Aliyah Boston | IND | PA | Over | 16.5 | -104 | 17 | HIT |
| Caitlin Clark | IND | PA | Over | 26.5 | -126 | 24 | miss |
| Kelsey Mitchell | IND | PA | Over | 21.5 | -124 | 18 | miss |
| Shakira Austin | WSH | PA | Over | 17.5 | -109 | 14 | miss |
| Sonia Citron | WSH | PA | Over | 19.5 | -109 | 17 | miss |
| Aliyah Boston | IND | PA | Under | 16.5 | -131 | 17 | miss |
| Caitlin Clark | IND | PA | Under | 26.5 | -107 | 24 | HIT |
| Kelsey Mitchell | IND | PA | Under | 21.5 | -110 | 18 | HIT |
| Shakira Austin | WSH | PA | Under | 17.5 | -124 | 14 | HIT |
| Sonia Citron | WSH | PA | Under | 19.5 | -125 | 17 | HIT |
| Aliyah Boston | IND | PR | Over | 20.5 | -126 | 24 | HIT |
| Caitlin Clark | IND | PR | Over | 23.5 | -108 | 22 | miss |
| Shakira Austin | WSH | PR | Over | 22.5 | -110 | 19 | miss |
| Sonia Citron | WSH | PR | Over | 18.5 | -110 | 12 | miss |
| Aliyah Boston | IND | PR | Under | 20.5 | -108 | 24 | miss |
| Caitlin Clark | IND | PR | Under | 23.5 | -125 | 22 | HIT |
| Shakira Austin | WSH | PR | Under | 22.5 | -123 | 19 | HIT |
| Sonia Citron | WSH | PR | Under | 18.5 | -124 | 12 | HIT |
| Aliyah Boston | IND | PRA | Over | 23.5 | -110 | 27 | HIT |
| Caitlin Clark | IND | PRA | Over | 31.5 | -114 | 27 | miss |
| Shakira Austin | WSH | PRA | Over | 24.5 | -124 | 23 | miss |
| Sonia Citron | WSH | PRA | Over | 22.5 | -110 | 17 | miss |
| Aliyah Boston | IND | PRA | Under | 23.5 | -123 | 27 | miss |
| Caitlin Clark | IND | PRA | Under | 31.5 | -119 | 27 | HIT |
| Shakira Austin | WSH | PRA | Under | 24.5 | -109 | 23 | HIT |
| Sonia Citron | WSH | PRA | Under | 22.5 | -124 | 17 | HIT |

### NY@CON - 7/14 (50.0%)

| player | team | type | side | line | price | actual | result |
|--------|------|------|------|------|-------|--------|--------|
| Breanna Stewart | NY | PA | Over | 22.5 | -113 | 31 | HIT |
| Pauline Astier | NY | PA | Over | 13.5 | -123 | 10 | miss |
| Saniya Rivers | CON | PA | Over | 11.5 | -123 | 15 | HIT |
| Breanna Stewart | NY | PA | Under | 22.5 | -120 | 31 | miss |
| Pauline Astier | NY | PA | Under | 13.5 | -110 | 10 | HIT |
| Saniya Rivers | CON | PA | Under | 11.5 | -111 | 15 | miss |
| Breanna Stewart | NY | PR | Over | 27.5 | -114 | 37 | HIT |
| Diamond Miller | CON | PR | Over | 12.5 | -108 | 12 | miss |
| Satou Sabally | NY | PR | Over | 17.5 | -107 | 11 | miss |
| Breanna Stewart | NY | PR | Under | 27.5 | -119 | 37 | miss |
| Diamond Miller | CON | PR | Under | 12.5 | -126 | 12 | HIT |
| Satou Sabally | NY | PR | Under | 17.5 | -127 | 11 | HIT |
| Breanna Stewart | NY | PRA | Over | 30.5 | -115 | 40 | HIT |
| Breanna Stewart | NY | PRA | Under | 30.5 | -118 | 40 | miss |
