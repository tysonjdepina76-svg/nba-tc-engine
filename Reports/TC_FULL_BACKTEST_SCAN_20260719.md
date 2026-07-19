# TC Backtest — Full System Scan
## Generated: 2026-07-19 ~5:40 AM ET

---

## Data Sources Scanned

| Source | Rows | Graded | Hit Rate | Date Range |
|--------|------|--------|----------|------------|
| tc_pipeline.db (graded_picks) | 6,238 | 6,238 | 67.2% | 2026-07-16 (batch) |
| BACKTEST_RECONCILIATION (Daily_Log) | 16,294 | 4,148 | 64.2% | Jun 18 – Jul 9 |
| combined_backtest.csv | 1,161 | ~1,018 | 62-68% | Various |
| all_graded_picks.csv | 24,620 | 0 | N/A (ALL PENDING) | Jun 6 – current |
| data/backtest/*.csv | 1,304 | 0 | N/A (no grading) | 2025-26 |
| historical picks/*/picks.csv | ~15,000+ | 0 | N/A (ALL PENDING) | Jun 2026 |

---

## 1. tc_pipeline.db — 6,238 GRADED PICKS

**Overall: 6,238 picks | 4,189 hits | 67.2% hit rate | +$1,758.80 profit**

### By Sport
| Sport | Picks | Hits | Hit% | Avg Edge | Profit |
|-------|------:|-----:|-----:|---------:|-------:|
| WNBA | 6,230 | 4,181 | 67.1% | 6.92 | +$1,751.53 |
| WC | 5 | 5 | 100.0% | 6.28 | +$4.54 |
| MLB | 3 | 3 | 100.0% | 4.70 | +$2.73 |

### WNBA — By Stat (6,230 picks)
| Stat | Picks | Hits | Hit% |
|------|------:|-----:|-----:|
| 3PM | 980 | 745 | **76.0%** |
| BLK | 800 | 558 | 69.8% |
| STL | 1,020 | 683 | 67.0% |
| AST | 1,140 | 757 | 66.4% |
| REB | 1,120 | 734 | 65.5% |
| PTS | 1,160 | 697 | 60.1% |

---

## 2. BACKTEST RECONCILIATION — 4,148 GRADED PICKS (Jun 18 – Jul 9)

### By Sport
| Sport | Picks | Hits | Hit% |
|-------|------:|-----:|-----:|
| MLB | 4,146 | 2,664 | 64.25% |
| WNBA | 2 | 1 | 50.0% |

### MLB — By Stat
| Stat | Picks | Hits | Hit% |
|------|------:|-----:|-----:|
| strikeouts | 48 | 41 | **85.42%** |
| hr | 30 | 24 | **80.0%** |
| total_bases | 1,018 | 719 | 70.63% |
| hits_allowed | 58 | 39 | 67.24% |
| hits | 991 | 632 | 63.77% |
| rbi | 977 | 607 | 62.13% |
| runs | 977 | 577 | 59.06% |
| earned_runs | 47 | 25 | 53.19% |

### MLB — Direction
| Direction | Picks | Hits | Hit% |
|-----------|------:|-----:|-----:|
| **UNDER** | 2,881 | 2,144 | **74.42%** |
| OVER | 1,267 | 521 | 41.12% |

### MLB — Edge Brackets (THE MONEY ZONE)
| Edge | Picks | Hits | Hit% |
|------|------:|-----:|-----:|
| < 0.5 | 2,149 | 1,239 | 57.65% |
| 0.5 – 1 | 1,193 | 752 | 63.03% |
| 1 – 2 | 441 | 341 | 77.32% |
| 2 – 3 | 277 | 249 | **89.89%** |
| 3 – 5 | 62 | 58 | **93.55%** |
| **5+** | **26** | **26** | **💯 100%** |

### MLB — by Source
| Source | Picks | Hit% |
|--------|------:|-----:|
| SDIO Lines (real) | 4,047 | 65.16% |
| TC Internal Fallback | 99 | 27.27% |

---

## 3. combined_backtest.csv — 1,161 PICKS

| Sport | Picks | Graded | Hits | Hit% |
|-------|------:|-------:|-----:|-----:|
| NBA | 606 | 606 | 375 | 61.9% |
| WNBA | 372 | 372 | 251 | 67.5% |
| WC | 180 | 14 | 6 | 42.9% |
| MLB | 1 | 1 | 0 | 0% |
| NFL | 1 | 1 | 0 | 0% |
| NHL | 1 | 1 | 0 | 0% |

### NBA — By Stat
| Stat | Picks | Hit% |
|------|------:|-----:|
| REB OVER | 90 | **85.6%** |
| PTS OVER | 195 | 80.5% |
| AST OVER | 101 | 69.3% |
| 3PM OVER | 99 | 55.6% |
| STL OVER | 90 | 44.4% |
| BLK OVER | 31 | 35.5% |

### WNBA — By Stat
| Stat | Picks | Hit% |
|------|------:|-----:|
| BLK OVER | 31 | **100.0%** |
| AST OVER | 77 | 75.3% |
| REB OVER | 88 | 61.8% |
| PTS OVER | 146 | 60.3% |

---

## 4. GAPS — What We're Missing

| Gap | Impact | Fix |
|-----|--------|-----|
| No NBA 2023-25 backtest | Missing 2 seasons of NBA data | Need box score API to grade historical picks |
| No NFL 2023-26 backtest | Zero NFL grading exists | NFL picks never ran/graded |
| No WNBA 2023-24 backtest | Only 2025-26 partial | Historical WNBA box scores needed |
| 24,620 picks UNGRADED | Mass of PENDING data | Need automated grading pipeline |
| Odds API quota maxed | WC lines from self-edge only | Upgrade to Pro tier |
| No playoff/finals specific | ECF/WCF/Finals not tagged | Add playoff flag to picks schema |

---

## 5. TRUTH SUMMARY

```
TC Pipeline Lifetime:
  Total picks generated:  ~40,000+
  Actually graded:         ~11,500
  Overall hit rate:        64-67%
  Profit (graded only):    +$1,758.80

WNBA is the strongest sport (67% hit, 6,230 graded picks)
MLB UNDER plays dominate (74% hit rate on 2,881 picks)
NBA REB/PTS plays reliable (80-86% on graded)
Edge ≥ 2% = 90% hit rate
Edge ≥ 5% = 100% hit rate (26/26)
```
