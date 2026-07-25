# TC Self-Edge vs. The Big Boys — Performance Report
**Generated: 2026-07-24 07:17 AM ET**

---

## 1. TC SELF-EDGE — WHAT WE GOT

| Metric | Value |
|---|---|
| Engine | `tc_math.py → over_under_signal(test="selfedge")` |
| Graded picks | **84** (all WNBA, all 2026-07-19) |
| Hits | **51** |
| Hit Rate | **60.7%** |
| Direction | 100% UNDER |
| Profit (at $1/unit) | +$18.00 |

### By Stat Category

| Stat | Picks | Hits | Rate |
|---|---|---|---|
| PTS | 21 | 14 | **66.7%** |
| P+R | 21 | 14 | **66.7%** |
| P+A | 21 | 12 | 57.1% |
| P+R+A | 21 | 11 | 52.4% |

### 100% Hit Players (11 players)
Cheyenne Parker, Diamond DeShields, Brionna Jones, Diana Taurasi, Marina Mabrey, Kelsey Plum, Lexie Brown, Natasha Howard, Satou Sabally, Skylar Diggins-Smith, Teaira McCowan

### 0% Miss Players (7 players)
Allisha Gray, Brittney Griner, DeWanna Bonner, Kahleah Copper, Arike Ogunbowale, Azura Stevens, Dearica Hamby

---

## 2. HOW THE SELF-EDGE ENGINE WORKS

The "self-edge" label means we use TC's own per-player projections as the benchmark line — not real sportsbook lines. The engine:

1. `gen_wnba_today.py` generates a custom projection for each player × stat
2. `tc_math.py` compares TC projection vs. season average to produce an edge signal
3. Every pick is **UNDER** — when the model sees a gap, it bets the player will go under

This is fundamentally different from comparing TC projections to DraftKings/FanDuel lines. We're betting that TC projections are sharper than the player's historical average.

---

## 3. THE BIG BOYS — INDUSTRY BENCHMARKS

### Win Rate Benchmarks

| Tier | Win Rate | Notes |
|---|---|---|
| Break-even (-110 odds) | **52.38%** | Just to not lose money |
| Recreational bettor avg | **45-48%** | 95% of bettors lose money |
| Small edge | **53%** | Profitable but thin margins |
| Solid sharp bettor | **55%** | Statistically significant edge |
| Elite syndicates (Pinnacle-level) | **55-57%** | Multi-million volume, long-term |
| ML model in production (Reddit study) | **56.3%** | 2,847 bets over 18 months, 12.7% ROI |
| PropsBot AI (high-confidence) | ~60%* | Claims 31% ROI; unverified methodology |
| Best individual tracked (Reddit) | **55.4%** | 2,047 bets, 3 years, Kelly sizing |

\* PropsBot's "high confidence" picks are a cherry-picked subset — not all picks.

### What the Industry Considers Elite

- **53-55%** at -110 odds = professional-level, 3-5% ROI[^1]
- **55-57%** = rare, top 1% of bettors[^2]
- **57%+** = usually unsustainable or small sample noise
- Sportsbook hold rate in 2024: **9.3%** on $149.8B handle[^3]
- Only **3-5%** of sports bettors are profitable long-term[^3]

---

## 4. HEAD-TO-HEAD COMPARISON

| Metric | TC Self-Edge | Industry Elite | Verdict |
|---|---|---|---|
| Hit rate | **60.7%** | 55-57% | TC higher |
| Sample size | **84** | 2,000-5,000+ | Industry dominates |
| Days tracked | **1** | 365-1,000+ | Industry dominates |
| Statistical significance (p) | **0.077** | <0.001 typical | Not yet proven |
| 95% Confidence Interval | **50.0% - 70.5%** | ~54-57% | Too wide to trust |
| Direction diversity | 0% (all UNDER) | Mixed | Red flag |
| Real market lines | **No** (self-projected) | Yes (DraftKings, Pinnacle) | Major gap |

### The Honest Math

60.7% on 84 picks sounds great — but the p-value of 0.077 means there's a **7.7% chance this is just luck**. We can't reject the null hypothesis at the standard 5% threshold.

For this hit rate to be statistically proven, we need:
- **~110 picks at 60.7%** to hit p<0.05
- **~200+ picks** for a tight confidence interval
- **Multiple weeks** of data across different game slates

---

## 5. THE REAL GAPS

### What We're Missing vs. Big Boys

1. **Real market lines**: Self-edge compares TC projections to TC projections. Big boys compare to DraftKings, FanDuel, Pinnacle closing lines. Without real lines, we can't know if we're beating the market or just beating ourselves.

2. **Scale**: 84 picks = 1 day. Big boys process thousands of bets across multiple sports, seasons, and market conditions.

3. **Direction balance**: 100% UNDER is a structural bias. If the model only sees UNDER value, it's not finding real edges — it's just fading every projection. A real edge model should find OVER signals too.

4. **Live odds feed**: Odds API is quota-capped. MLB is dead without it. WNBA runs on self-edge. This is not how the big boys operate.

5. **Kelly/bankroll management**: We track hit rate. Big boys track closing line value (CLV), expected value, and Kelly fraction sizing.

---

## 6. WHAT 60.7% WOULD MEAN IF REAL

If sustained over a meaningful sample with real market lines:

- At -110 odds: ~8-10% ROI (elite territory)
- At -105 (reduced juice): ~12% ROI
- 10 units/day × 250 days = 2,500 units/year
- At $100/unit: +$20K-$30K/year

That's professional-level income. But the sample is too small and the lines aren't real yet.

---

## 7. NEXT STEPS TO COMPETE

| Priority | Action | Impact |
|---|---|---|
| 🔴 P1 | Get live Odds API key or alternative odds source | Unlocks real market comparison |
| 🔴 P1 | Generate picks daily, not once | Builds sample size |
| 🟡 P2 | Track closing line value (CLV) | Industry-standard edge metric |
| 🟡 P2 | Add OVER signals to engine | Removes structural UNDER bias |
| 🟢 P3 | Kelly fraction sizing | Proper bankroll management |
| 🟢 P3 | Multi-sport when odds are available | Diversification |

---

## Bottom Line

**TC Self-Edge at 60.7% is promising but unproven.** The hit rate is above every industry benchmark, but on 84 picks from a single day with no real market lines, it doesn't mean much yet. The 95% confidence interval stretches from 50% to 70% — meaning the true long-term rate could be barely above break-even, or it could be elite. We don't know.

The big boys win with volume, real lines, and years of data. We have a good first step. Keep generating, get real odds, and let the math prove itself over 200+ picks.

[^1]: Webopedia, "Professional Betting ROI: Long-Term Growth Strategies" — 55% WR ≈ 4-5% ROI at -110
[^2]: SportBot AI, "Sports Betting Profitability Statistics 2026" — only 3-5% of bettors profitable
[^3]: Legal Sports Report, "US Sports Betting Revenue Tracker" — $13.71B revenue on $149.8B handle in 2024
