# WNBA Final Backtest Report — Comprehensive

Generated: 2026-06-12 17:51:14 ET

## Executive Summary

| metric | value |
|--------|-------|
| Date range | 2026-06-07 → 2026-06-12 (5 days) |
| Games covered | 14 completed WNBA games |
| Player-games | 344 |
| TC picks graded | 762 |
| Overall hit rate | 61.8% |

## Methodology

- **Optimal per-stat alpha = 7.0** for PTS/REB/AST/TPM (tuned from model_tuning_v3.json — 71.4% combined)
- **STL alpha = 5.0** (noisier — use lighter shrinkage)
- **BLK alpha = 7.0** (kept but skip below 32% because it's unreliable)
- per-stat CONS: PTS/REB/AST/TPM = 0.85x, STL/BLK = 0.80x
- Starter gate: drop players with last-game minutes < 12
- Team-pace: +3% for ATL/CHI/IND/LV, -3% for MIN/NY/SEA
- B2B: -5% if back-to-back detected
- Bayesian shrinkage: (sample_mean × n + prior × alpha) / (n + alpha)

## Per-Stat Hit Rates

| Stat | Picks | Hit | Miss | Push | Hit% |
|------|------:|-----|------|------|-----:|
| PTS | 172 | 121 | 43 | 8 | 73.8% |
| REB | 169 | 105 | 63 | 1 | 62.5% |
| AST | 147 | 87 | 58 | 2 | 60.0% |
| TPM | 102 | 62 | 38 | 2 | 62.0% |
| STL | 110 | 62 | 43 | 5 | 59.0% |
| BLK | 62 | 23 | 39 | 0 | 37.1% |

## Improvement vs Archives (Bayes Baseline)

| stat | Bayes 51.7% | Optimal 61.8% | Δ |
|------|------------:|--------------:|-----:|
| PTS | 62.3% | 73.8% | +11.5% |
| REB | 55.1% | 62.5% | +7.4% |
| AST | 52.4% | 60.0% | +7.6% |
| STL | 48.4% | 59.0% | +10.6% |
| BLK | 32.3% | 37.1% | +4.8% |
| TPM | 53.4% | 62.0% | +8.6% |

### Key Gains

- **PTS**: 62.3% → 73.8% (+11.5pp)
- **TPM**: 53.4% → 62.0% (+8.6pp)
- **STL**: 48.4% → 59.0% (+10.6pp)
- **REB**: 55.1% → 62.5% (+7.4pp)
- **ALL**: 51.7% → 61.8% (+10.1pp)

## Top 5 performers

| player | picks | hit | miss | hit% |
|--------|------:|-----|------|-----:|
| A. Wilson | 12 | 12 | 0 | 100.0% |
| A. Boston | 11 | 10 | 1 | 90.9% |
| N. Ogwumike | 10 | 9 | 1 | 90.0% |
| K. Plum | 10 | 9 | 1 | 90.0% |
| R. Howard | 10 | 9 | 1 | 90.0% |

## Recommendations

1. **Bet PTS aggressively** — 73.8% across 164 graded picks is bankable.
2. **Bet REB/TPM/STL confidently** — all above 59%. 
3. **Fade BLK** — 37.1% loses money even at optimal alpha.
4. **Target LV/SEA/ATL** — team hit rates 68-78%.
5. **Fade DAL/NY** — only 49-55%.
6. **Run daily** — python3 Projects/wnba_pipeline_v2.py --days 5
