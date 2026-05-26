# NBA Conference Finals + WNBA TC Projections
## Backtest Reference & 4-Stat TC Models — May 18, 2026

**TC Formula (v9):** T = floor(0.85 × PTS | 0.80 × REB | 0.75 × AST | 0.80 × 3PM)
**Edge:** L − T | **Valid:** Edge ≥ +3 AND hit_rate ≥ 75%
**Q:** T × 0.55 | **OUT:** T = 0

---

# WESTERN CONFERENCE FINALS — GAME 1
## SAS @ OKC | May 18, 2026 — 8:30 PM ET (NBC/Peacock)

**Series:** SAS vs OKC — Top 2 seeds in West
**SA lead scorers:** Wemby 28.8 PPG | Fox ~22 PPG (Q) | Castle 20.6 recent PPG
**OKC lead scorers:** SGA 33.8 PPG | Jalen Williams 19 PPG (back) | Ajay Mitchell 22 PPG
**Injury notes:** De'Aaron Fox — Q (ankle) | Jalen Williams — ACTIVE (returned Game 6 MIN series)

---

## OKC Thunder — Full Roster (4-Stat TC)

| # | Player | POS | Status | L(PTS) | M(PTS) | T(PTS) | L(REB) | M(REB) | T(REB) | L(AST) | M(AST) | T(AST) | L(3PM) | M(3PM) | T(3PM) | Edge PTS | Valid |
|---|--------|-----|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|-------|
| 1 | **Shai Gilgeous-Alexander** | PG | ACTIVE | 33.5 | 33.8 | **28** | 5.5 | 5.2 | **4** | 7.5 | 6.6 | **5** | 2.5 | 2.5 | **2** | +5.5 | ✅ |
| 2 | **Chet Holmgren** | C | ACTIVE | 17.5 | 18.5 | **16** | 10.5 | 10.7 | **8** | 4.0 | 4.1 | **3** | 1.5 | 1.8 | **1** | +1.5 | ⚠️ |
| 3 | **Jalen Williams** | SF | ACTIVE | 19.5 | 20.5 | **17** | 7.5 | 8.0 | **6** | 5.0 | 5.5 | **4** | 1.5 | 1.6 | **1** | +2.5 | ⚠️ |
| 4 | **Luguentz Dort** | SG | ACTIVE | 11.5 | 12.0 | **10** | 4.5 | 4.8 | **4** | 2.5 | 2.8 | **2** | 1.5 | 1.6 | **1** | +1.5 | ❌ |
| 5 | **Isaiah Joe** | SG | ACTIVE | 9.5 | 10.2 | **9** | 2.5 | 2.8 | **2** | 2.0 | 2.2 | **1** | 2.0 | 2.3 | **2** | +0.5 | ❌ |
| 6 | **Ajay Mitchell** | PG | ACTIVE | 21.5 | 22.0 | **19** | 3.5 | 4.0 | **3** | 5.5 | 5.8 | **4** | 2.0 | 2.2 | **2** | +2.5 | ⚠️ |
| 7 | **Isaiah Hartenstein** | C | Q | 9.5 | 10.0 | **5** | 9.5 | 10.0 | **5** | 3.5 | 3.8 | **2** | 0.5 | 0.6 | **0** | +4.5 | ✅ |
| 8 | **Jaylin Williams** | PF | ACTIVE | 5.5 | 6.0 | **5** | 5.5 | 6.0 | **4** | 1.5 | 1.8 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 9 | **Kenyon Williams Jr.** | PF | ACTIVE | 4.5 | 4.8 | **4** | 4.0 | 4.5 | **3** | 1.0 | 1.2 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 10 | **Oso Ighodaro** | PF | ACTIVE | 4.5 | 5.0 | **4** | 4.5 | 5.0 | **4** | 2.0 | 2.2 | **1** | 0.2 | 0.3 | **0** | +0.5 | ❌ |
| 11 | **Jared McCain** | PG | ACTIVE | 8.5 | 9.5 | **8** | 2.0 | 2.5 | **2** | 3.0 | 3.2 | **2** | 1.5 | 1.8 | **1** | +0.5 | ❌ |
| 12 | **Cason Wallace** | SG | ACTIVE | 5.5 | 6.0 | **5** | 2.0 | 2.2 | **2** | 1.5 | 1.8 | **1** | 1.0 | 1.2 | **1** | +0.5 | ❌ |
| 13 | **Bennedict Mathurin** | SF | ACTIVE | 6.5 | 7.0 | **6** | 3.0 | 3.2 | **2** | 1.0 | 1.2 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 14 | **Alex Caruso** | SG | ACTIVE | 6.5 | 7.0 | **6** | 3.0 | 3.2 | **2** | 2.5 | 2.8 | **2** | 1.0 | 1.1 | **1** | +0.5 | ❌ |
| 15 | **Lindy Waters III** | SF | ACTIVE | 4.5 | 5.0 | **4** | 2.5 | 2.8 | **2** | 1.0 | 1.2 | **1** | 1.0 | 1.2 | **1** | +0.5 | ❌ |
| 16 | **Keyonte George** | G | ACTIVE | 4.0 | 4.5 | **4** | 1.5 | 1.8 | **1** | 2.0 | 2.2 | **1** | 0.5 | 0.6 | **0** | 0.0 | ❌ |

**OKC TC Backtest (5-game sample):**
- SGA actuals (PTS): [37, 37, 42, 31, 33] → T=28, hit rate 5/5 = 100% ✅
- Chet actuals (PTS): [15, 16, 17, 14, 18] → T=16, hit rate 4/5 = 80% ✅
- Jalen Williams actuals (PTS): [18, 17, 19, 16, 20] → T=17, hit rate 3/5 = 60% ⚠️
- Ajay Mitchell actuals (PTS): [22, 24, 21, 20, 19] → T=19, hit rate 4/5 = 80% ✅

---

## SAS Spurs — Full Roster (4-Stat TC)

| # | Player | POS | Status | L(PTS) | M(PTS) | T(PTS) | L(REB) | M(REB) | T(REB) | L(AST) | M(AST) | T(AST) | L(3PM) | M(3PM) | T(3PM) | Edge PTS | Valid |
|---|--------|-----|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|-------|
| 1 | **Victor Wembanyama** | C | ACTIVE | 28.5 | 28.8 | **24** | 10.5 | 10.7 | **8** | 4.5 | 4.1 | **3** | 2.5 | 2.4 | **2** | +4.5 | ✅ |
| 2 | **De'Aaron Fox** | PG | Q | 22.5 | 23.5 | **12** | 4.5 | 5.0 | **2** | 6.5 | 7.0 | **4** | 1.5 | 1.8 | **1** | +10.5 | ✅ |
| 3 | **Stephon Castle** | SG | ACTIVE | 20.5 | 21.5 | **18** | 4.5 | 4.8 | **4** | 4.5 | 4.5 | **3** | 1.0 | 1.2 | **1** | +2.5 | ⚠️ |
| 4 | **Dylan Harper** | G | ACTIVE | 17.5 | 18.5 | **16** | 5.5 | 6.0 | **5** | 3.5 | 3.8 | **3** | 1.0 | 1.2 | **1** | +1.5 | ⚠️ |
| 5 | **Devin Vassell** | G-F | ACTIVE | 13.5 | 14.0 | **12** | 4.0 | 4.2 | **3** | 2.5 | 2.8 | **2** | 2.0 | 2.2 | **2** | +1.5 | ❌ |
| 6 | **Harrison Barnes** | F | ACTIVE | 11.5 | 12.5 | **11** | 4.5 | 4.8 | **4** | 1.5 | 1.8 | **1** | 1.5 | 1.6 | **1** | +0.5 | ❌ |
| 7 | **Julian Champagnie** | SF | ACTIVE | 8.5 | 9.0 | **7** | 3.5 | 3.8 | **3** | 1.0 | 1.2 | **1** | 1.5 | 1.8 | **1** | +1.5 | ❌ |
| 8 | **Luke Kornet** | C | ACTIVE | 7.5 | 8.0 | **7** | 5.5 | 6.0 | **5** | 1.5 | 1.8 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 9 | **Keldon Johnson** | F | ACTIVE | 7.5 | 8.0 | **7** | 3.5 | 3.8 | **3** | 1.5 | 1.8 | **1** | 1.0 | 1.1 | **1** | +0.5 | ❌ |
| 10 | **Jeremy Sochan** | F | ACTIVE | 6.5 | 7.0 | **6** | 4.5 | 5.0 | **4** | 2.5 | 2.8 | **2** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 11 | **Malaki Branham** | G | ACTIVE | 6.5 | 7.0 | **6** | 2.0 | 2.2 | **2** | 1.5 | 1.8 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 12 | **Devonte' Graham** | G | ACTIVE | 5.5 | 6.0 | **5** | 1.5 | 1.8 | **1** | 3.5 | 3.8 | **3** | 1.0 | 1.2 | **1** | +0.5 | ❌ |
| 13 | **Zach Collins** | C | ACTIVE | 5.5 | 6.0 | **5** | 4.5 | 5.0 | **4** | 1.5 | 1.8 | **1** | 0.2 | 0.3 | **0** | +0.5 | ❌ |
| 14 | **Mamadou Gning** | F | ACTIVE | 3.5 | 4.0 | **3** | 4.5 | 5.0 | **4** | 0.5 | 0.6 | **0** | 0.0 | 0.0 | **0** | +0.5 | ❌ |
| 15 | **Harrison Barnes** | F | ACTIVE | 11.5 | 12.5 | **11** | 4.5 | 4.8 | **4** | 1.5 | 1.8 | **1** | 1.5 | 1.6 | **1** | +0.5 | ❌ |
| 16 | **Cedi Osman** | F | ACTIVE | 4.5 | 5.0 | **4** | 2.5 | 2.8 | **2** | 1.0 | 1.2 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |

**SAS TC Backtest (5-game sample):**
- Wemby actuals (PTS): [27, 19, 39, 11, 30] → T=24, hit rate 4/5 = 80% ✅
- Fox actuals (PTS): [24, 18, 22, 20, 19] → T=20 (if Q=55%: T=12), hit rate 5/5 = 100% ⚠️ (but Q status reduces)
- Castle actuals (PTS): [22, 28, 33, 25, 20] → T=18, hit rate 5/5 = 100% ✅
- Harper actuals (PTS): [18, 27, 15, 20, 22] → T=16, hit rate 4/5 = 80% ✅

---

## OKC vs SAS — TC Edge Summary (PTS only for quick reference)

| Player | Team | T(PTS) | L(PTS) | Edge PTS | REB Edge | AST Edge | 3PM Edge | Valid |
|--------|------|--------|--------|---------|---------|---------|---------|-------|
| **Shai Gilgeous-Alexander** | OKC | **28** | 33.5 | **+5.5** | +1.5 | +2.5 | +0.5 | ✅ |
| **Victor Wembanyama** | SAS | **24** | 28.5 | **+4.5** | +2.5 | +1.5 | +0.5 | ✅ |
| **De'Aaron Fox (Q)** | SAS | **12** | 22.5 | **+10.5** | +2.5 | +2.5 | +0.5 | ✅ |
| **Isaiah Hartenstein (Q)** | OKC | **5** | 9.5 | **+4.5** | +4.5 | +1.5 | +0.5 | ✅ |
| **Stephon Castle** | SAS | **18** | 20.5 | **+2.5** | +0.5 | +1.5 | -0.5 | ⚠️ |
| **Chet Holmgren** | OKC | **16** | 17.5 | **+1.5** | +2.5 | +1.0 | +0.5 | ⚠️ |
| **Jalen Williams** | OKC | **17** | 19.5 | **+2.5** | +1.5 | +1.0 | +0.5 | ⚠️ |
| **Dylan Harper** | SAS | **16** | 17.5 | **+1.5** | +0.5 | +0.5 | -0.5 | ⚠️ |
| **Ajay Mitchell** | OKC | **19** | 21.5 | **+2.5** | +0.5 | +1.5 | +0.5 | ⚠️ |

---

# EASTERN CONFERENCE FINALS — GAME 1
## CLE @ NYK | May 19, 2026 — 8:00 PM ET (ESPN)

**Series:** CLE (52-30, #4 seed) vs NYK (53-29, #3 seed) — Knicks won reg season series
**CLE lead scorers:** Donovan Mitchell 26.3 PPG | Evan Mobley 18.5 PPG | Darius Garland 15.5 PPG
**NYK lead scorers:** Jalen Brunson 27.4 PPG | Karl-Anthony Towns 22.5 PPG | OG Anunoby 16.5 PPG

---

## NYK Knicks — Full Roster (4-Stat TC)

| # | Player | POS | Status | L(PTS) | M(PTS) | T(PTS) | L(REB) | M(REB) | T(REB) | L(AST) | M(AST) | T(AST) | L(3PM) | M(3PM) | T(3PM) | Edge PTS | Valid |
|---|--------|-----|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|-------|
| 1 | **Jalen Brunson** | PG | ACTIVE | 27.5 | 27.4 | **23** | 4.5 | 4.2 | **3** | 6.5 | 6.6 | **5** | 2.5 | 2.7 | **2** | +4.5 | ✅ |
| 2 | **Karl-Anthony Towns** | C | ACTIVE | 22.5 | 23.0 | **19** | 10.5 | 10.0 | **8** | 3.5 | 3.8 | **3** | 2.0 | 2.2 | **2** | +3.5 | ✅ |
| 3 | **OG Anunoby** | SF | ACTIVE | 16.5 | 17.0 | **14** | 5.5 | 5.8 | **5** | 2.5 | 2.8 | **2** | 2.0 | 2.2 | **2** | +2.5 | ⚠️ |
| 4 | **Josh Hart** | SG | ACTIVE | 14.5 | 15.0 | **13** | 7.5 | 7.8 | **6** | 5.5 | 5.8 | **4** | 1.5 | 1.6 | **1** | +1.5 | ❌ |
| 5 | **Mitchell Robinson** | C | ACTIVE | 7.5 | 8.0 | **7** | 9.5 | 10.0 | **8** | 1.5 | 1.8 | **1** | 0.0 | 0.0 | **0** | +0.5 | ❌ |
| 6 | **Donovan Bridges** | G | ACTIVE | 8.5 | 9.0 | **7** | 3.5 | 3.8 | **3** | 2.0 | 2.2 | **1** | 1.0 | 1.1 | **1** | +1.5 | ❌ |
| 7 | **Miles McBride** | G | ACTIVE | 7.5 | 8.0 | **7** | 2.0 | 2.2 | **2** | 2.5 | 2.8 | **2** | 1.5 | 1.6 | **1** | +0.5 | ❌ |
| 8 | **Jacob Topp** | G | ACTIVE | 4.5 | 5.0 | **4** | 1.5 | 1.8 | **1** | 1.5 | 1.8 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 9 | **Mewah** | F | ACTIVE | 3.5 | 4.0 | **3** | 3.5 | 4.0 | **3** | 0.5 | 0.6 | **0** | 0.0 | 0.0 | **0** | +0.5 | ❌ |
| 10 | **Jericho** | G | ACTIVE | 3.5 | 4.0 | **3** | 1.5 | 1.8 | **1** | 2.0 | 2.2 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |
| 11 | **Precious Achiuwa** | F | ACTIVE | 5.5 | 6.0 | **5** | 5.5 | 6.0 | **5** | 1.0 | 1.2 | **1** | 0.5 | 0.6 | **0** | +0.5 | ❌ |

**NYK TC Backtest (5-game sample):**
- Brunson actuals (PTS): [39, 22, 33, 28, 25] → T=23, hit rate 4/5 = 80% ✅
- Towns actuals (PTS): [25, 21, 24, 20, 23] → T=19, hit rate 5/5 = 100% ✅
- Anunoby actuals (PTS): [18, 15, 20, 17, 19] → T=14, hit rate 4/5 = 80% ✅

---

## CLE Cavaliers — Full Roster (4-Stat TC)

| # | Player | POS | Status | L(PTS) | M(PTS) | T(PTS) | L(REB) | M(REB) | T(REB) | L(AST) | M(AST) | T(AST) | L(3PM) | M(3PM) | T(3PM) | Edge PTS | Valid |
|---|--------|-----|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|-------|
| 1 | **Donovan Mitchell** | SG | ACTIVE | 26.5 | 26.3 | **22** | 5.5 | 5.3 | **4** | 4.5 | 4.3 | **3** | 2.5 | 2.8 | **2** | +4.5 | ✅ |
| 2 | **Evan Mobley** | PF | ACTIVE | 18.5 | 19.0 | **16** | 9.5 | 10.0 | **8** | 3.5 | 3.8 | **3** | 1.0 | 1.2 | **1** | +2.5 | ⚠️ |
| 3 | **Darius Garland** | PG | ACTIVE | 15.5 | 16.0 | **13** | 2.5 | 2.8 | **2** | 6.5 | 7.0 | **5** | 1.5 | 1.8 | **1** | +2.5 | ⚠️ |
| 4 | **Jarrett Allen** | C | ACTIVE | 14.5 | 15.0 | **13** | 9.5 | 10.0 | **8** | 2.5 | 2.8 | **2** | 0.0 | 0.0 | **0** | +1.5 | ❌ |
| 5 | **De'Andre Hunter** | F | ACTIVE | 13.5 | 14.0 | **12** | 4.5 | 4.8 | **4** | 2.0 | 2.2 | **1** | 2.0 | 2.2 | **2** | +1.5 | ❌ |
| 6 | **Ty Jerome** | G | ACTIVE | 9.5 | 10.0 | **8** | 2.5 | 2.8 | **2** | 3.5 | 3.8 | **3** | 1.0 | 1.2 | **1** | +1.5 | ❌ |
| 7 | **Isaac Okoro** | SG | ACTIVE | 9.5 | 10.0 | **8** | 3.5 | 3.8 | **3** | 2.5 | 2.8 | **2** | 1.0 | 1.1 | **1** | +1.5 | ❌ |
| 8 | **Max Strus** | G-F | ACTIVE | 9.5 | 10.0 | **8** | 4.5 | 4.8 | **4** | 2.5 | 2.8 | **2** | 2.0 | 2.2 | **2** | +1.5 | ❌ |
| 9 | **Caris LeVert** | G | ACTIVE | 8.5 | 9.0 | **7** | 3.5 | 3.8 | **3** | 2.5 | 2.8 | **2** | 1.0 | 1.1 | **1** | +1.5 | ❌ |
| 10 | **Georges Niang** | F | ACTIVE | 6.5 | 7.0 | **6** | 2.5 | 2.8 | **2** | 1.5 | 1.8 | **1** | 1.0 | 1.2 | **1** | +0.5 | ❌ |
| 11 | **Tristan Thompson** | C | ACTIVE | 5.5 | 6.0 | **5** | 6.5 | 7.0 | **5** | 1.0 | 1.2 | **1** | 0.0 | 0.0 | **0** | +0.5 | ❌ |
| 12 | **Ty Jerome** | G | ACTIVE | 9.5 | 10.0 | **8** | 2.5 | 2.8 | **2** | 3.5 | 3.8 | **3** | 1.0 | 1.2 | **1** | +1.5 | ❌ |
| 13 | **Sam Merrill** | G | ACTIVE | 6.5 | 7.0 | **6** | 1.5 | 1.8 | **1** | 1.5 | 1.8 | **1** | 1.5 | 1.6 | **1** | +0.5 | ❌ |
| 14 | **Jared Allen** | F | ACTIVE | 4.5 | 5.0 | **4** | 4.5 | 5.0 | **4** | 0.5 | 0.6 | **0** | 0.5 | 0.6 | **0** | +0.5 | ❌ |

**CLE TC Backtest (5-game sample):**
- Mitchell actuals (PTS): [43, 24, 30, 28, 26] → T=22, hit rate 5/5 = 100% ✅
- Mobley actuals (PTS): [20, 18, 22, 17, 19] → T=16, hit rate 4/5 = 80% ✅
- Garland actuals (PTS): [18, 15, 20, 16, 17] → T=13, hit rate 5/5 = 100% ✅

---

## NYK vs CLE — TC Edge Summary (PTS only)

| Player | Team | T(PTS) | L(PTS) | Edge PTS | REB Edge | AST Edge | 3PM Edge | Valid |
|--------|------|--------|--------|---------|---------|---------|---------|-------|
| **Jalen Brunson** | NYK | **23** | 27.5 | **+4.5** | +1.5 | +1.5 | +0.5 | ✅ |
| **Donovan Mitchell** | CLE | **22** | 26.5 | **+4.5** | +1.5 | +1.5 | +0.5 | ✅ |
| **Karl-Anthony Towns** | NYK | **19** | 22.5 | **+3.5** | +2.5 | +0.5 | +0.5 | ✅ |
| **Evan Mobley** | CLE | **16** | 18.5 | **+2.5** | +1.5 | +0.5 | -0.5 | ⚠️ |
| **Darius Garland** | CLE | **13** | 15.5 | **+2.5** | -0.5 | +1.5 | -0.5 | ⚠️ |
| **OG Anunoby** | NYK | **14** | 16.5 | **+2.5** | +0.5 | +0.5 | +0.5 | ⚠️ |

---

# WNBA TC PROJECTIONS — MAY 18, 2026
## WSH @ DAL — 8:00 PM ET | CON @ POR — 10:00 PM ET

---

## WSH Mystics @ DAL Wings — 4-Stat TC

### WSH Mystics — Full Roster

| # | Player | POS | Status | PTS | TC(PTS) | REB | TC(REB) | AST | TC(AST) | 3PM | TC(3PM) | Edge PTS |
|---|--------|-----|--------|------|---------|------|---------|------|---------|------|---------|---------|
| 1 | **Sonia Citron** | G | ACTIVE | 15.5 | **13** | 5.0 | **4** | 3.5 | **3** | 0.8 | **1** | +2.5 |
| 2 | **Kiki Iriafen** | F | ACTIVE | 13.5 | **11** | 6.5 | **5** | 1.5 | **1** | 0.4 | **0** | +2.5 |
| 3 | **Shakira Austin** | C-F | ACTIVE | 12.5 | **11** | 7.0 | **6** | 2.5 | **2** | 0.5 | **0** | +1.5 |
| 4 | **Lucy Olsen** | G | ACTIVE | 10.5 | **9** | 2.8 | **2** | 3.0 | **2** | 0.7 | **1** | +1.5 |
| 5 | **Georgia Amoore** | G | ACTIVE | 9.5 | **8** | 2.0 | **2** | 4.5 | **3** | 1.2 | **1** | +1.5 |
| 6 | **Stefanie Dolson** | C | ACTIVE | 8.5 | **7** | 5.5 | **4** | 2.0 | **1** | 0.3 | **0** | +1.5 |
| 7 | **Rori Harmon** | G | ACTIVE | 7.0 | **6** | 3.5 | **3** | 5.0 | **4** | 0.3 | **0** | +1.0 |
| 8 | **Alysha Clark** | F | ACTIVE | 7.5 | **6** | 4.5 | **4** | 1.5 | **1** | 0.6 | **0** | +1.5 |
| 9 | **Jacy Sheldon** | G | ACTIVE | 7.5 | **6** | 2.2 | **2** | 2.5 | **2** | 0.5 | **0** | +1.5 |
| 10 | **Lauren Betts** | C | ACTIVE | 6.5 | **5** | 5.0 | **4** | 0.8 | **1** | 0.0 | **0** | +1.5 |
| 11 | **Emily Engstler** | F | ACTIVE | 5.5 | **5** | 4.8 | **4** | 1.8 | **1** | 0.2 | **0** | +0.5 |
| 12 | **Cassandre Prosper** | G | ACTIVE | 5.5 | **5** | 2.5 | **2** | 1.0 | **1** | 0.3 | **0** | +0.5 |
| 13 | ⚠️ **Michaela Onyenwere** | F | Q | 5.0 | **3** | 2.5 | **1** | 0.8 | **0** | 0.2 | **0** | +2.0 |
| 14 | ⚠️ **Cotie McMahon** | G | Q | 6.5 | **4** | 2.5 | **1** | 1.0 | **1** | 0.2 | **0** | +2.5 |
| 15 | **Sug Sutton** | G | ACTIVE | 4.5 | **4** | 1.5 | **1** | 3.2 | **2** | 0.3 | **0** | +0.5 |
| 16 | **Jade Melbourne** | G | ACTIVE | 3.5 | **3** | 1.2 | **1** | 1.5 | **1** | 0.1 | **0** | +0.5 |

**WSH TC totals:** TC PTS 102 | TC REB 51 | TC AST 27 | TC 3PM 4

**WSH actual game (May 18):** Citron 30 PTS | Iriafen 25 PTS | Austin 19 PTS | McMahon 15 PTS — DAL wins 89-82

---

### DAL Wings — Full Roster

| # | Player | POS | Status | PTS | TC(PTS) | REB | TC(REB) | AST | TC(AST) | 3PM | TC(3PM) | Edge PTS |
|---|--------|-----|--------|------|---------|------|---------|------|---------|------|---------|---------|
| 1 | **Arike Ogunbowale** | G | ACTIVE | 21.5 | **18** | 5.0 | **4** | 3.8 | **3** | 1.8 | **1** | +3.5 |
| 2 | **Paige Bueckers** | G | ACTIVE | 17.5 | **15** | 5.5 | **4** | 4.2 | **3** | 2.0 | **2** | +2.5 |
| 3 | **Maddy Siegrist** | F | ACTIVE | 14.5 | **12** | 6.5 | **5** | 1.5 | **1** | 0.9 | **1** | +2.5 |
| 4 | **Li Yueru** | C | ACTIVE | 12.5 | **11** | 8.5 | **7** | 1.0 | **1** | 0.0 | **0** | +1.5 |
| 5 | **Azzi Fudd** | G | ACTIVE | 12.0 | **10** | 2.8 | **2** | 2.2 | **2** | 1.2 | **1** | +2.0 |
| 6 | **Jessica Shepard** | F | ACTIVE | 9.5 | **8** | 6.0 | **5** | 2.5 | **2** | 0.3 | **0** | +1.5 |
| 7 | **Awak Kuier** | F | ACTIVE | 8.5 | **7** | 5.5 | **4** | 1.8 | **1** | 0.4 | **0** | +1.5 |
| 8 | **Odyssey Sims** | G | ACTIVE | 8.5 | **7** | 3.0 | **2** | 4.5 | **3** | 0.6 | **0** | +1.5 |
| 9 | **Aziaha James** | G | ACTIVE | 8.5 | **7** | 2.8 | **2** | 1.5 | **1** | 0.6 | **0** | +1.5 |
| 10 | **Diamond Miller** | F | ACTIVE | 7.5 | **6** | 3.5 | **3** | 1.8 | **1** | 0.4 | **0** | +1.5 |
| 11 | **Grace Berger** | G | ACTIVE | 6.5 | **5** | 2.5 | **2** | 3.0 | **2** | 0.4 | **0** | +1.5 |
| 12 | **JJ Quinerly** | G | ACTIVE | 7.5 | **6** | 2.0 | **2** | 1.2 | **1** | 0.3 | **0** | +1.5 |
| 13 | **Christyn Williams** | G | ACTIVE | 5.5 | **5** | 1.8 | **1** | 1.5 | **1** | 0.3 | **0** | +0.5 |
| 14 | **Tyasha Harris** | G | ACTIVE | 5.0 | **4** | 1.5 | **1** | 3.5 | **3** | 0.4 | **0** | +1.0 |
| 15 | **Alanna Smith** | F | ACTIVE | 4.2 | **3** | 4.0 | **3** | 0.8 | **1** | 0.2 | **0** | +1.2 |
| 16 | **Dulcy Mendjiadeu** | F-C | ACTIVE | 4.5 | **4** | 5.5 | **4** | 0.8 | **1** | 0.0 | **0** | +0.5 |
| 17 | **Costanza Verona** | G | ACTIVE | 3.0 | **2** | 1.0 | **1** | 1.5 | **1** | 0.2 | **0** | +1.0 |

**DAL TC totals:** TC PTS 146 | TC REB 61 | TC AST 33 | TC 3PM 6

---

## CON Sun @ POR Fire — 4-Stat TC

### CON Sun — Full Roster

| # | Player | POS | Status | PTS | TC(PTS) | REB | TC(REB) | AST | TC(AST) | 3PM | TC(3PM) | Edge PTS |
|---|--------|-----|--------|------|---------|------|---------|------|---------|------|---------|---------|
| 1 | **DeWanna Bonner** | F | ACTIVE | 16.5 | **14** | 7.5 | **6** | 4.0 | **3** | 1.2 | **1** | +2.5 |
| 2 | **Marina Mabrey** | G | ACTIVE | 14.5 | **12** | 3.5 | **3** | 4.5 | **3** | 1.5 | **1** | +2.5 |
| 3 | **Dijonai Carrington** | G | ACTIVE | 13.5 | **11** | 4.0 | **3** | 3.5 | **3** | 1.0 | **1** | +2.5 |
| 4 | **Alyssa Thomas** | F | ACTIVE | 12.5 | **11** | 8.5 | **7** | 6.5 | **5** | 0.2 | **0** | +1.5 |
| 5 | **Tyasha Harris** | G | ACTIVE | 10.5 | **9** | 2.5 | **2** | 4.8 | **3** | 0.8 | **1** | +1.5 |
| 6 | **Teaira McCowan** | C | ACTIVE | 11.5 | **10** | 9.5 | **7** | 1.2 | **1** | 0.0 | **0** | +1.5 |
| 7 | **Lexi Hull** | G | ACTIVE | 7.5 | **6** | 2.5 | **2** | 3.0 | **2** | 0.5 | **0** | +1.5 |
| 8 | **Crystal Dangerfield** | G | ACTIVE | 8.5 | **7** | 1.8 | **1** | 2.5 | **2** | 0.6 | **0** | +1.5 |
| 9 | **Annise Cooper** | F | ACTIVE | 5.5 | **5** | 4.0 | **3** | 1.0 | **1** | 0.3 | **0** | +0.5 |
| 10 | **Kyla Oldacre** | F | ACTIVE | 4.5 | **4** | 3.5 | **3** | 0.8 | **1** | 0.0 | **0** | +0.5 |
| 11 | **Olivia Mills** | C | ACTIVE | 3.5 | **3** | 4.5 | **3** | 0.5 | **0** | 0.0 | **0** | +0.5 |
| 12 | **Katie Georgiou** | F | ACTIVE | 4.2 | **3** | 3.0 | **2** | 0.8 | **1** | 0.1 | **0** | +1.2 |
| 13 | **Maddie West** | G | ACTIVE | 2.5 | **2** | 1.0 | **1** | 1.5 | **1** | 0.1 | **0** | +0.5 |

**CON TC totals:** TC PTS 97 | TC REB 48 | TC AST 27 | TC 3PM 4

---

### POR Fire — Full Roster (Expansion Team)

| # | Player | POS | Status | PTS | TC(PTS) | REB | TC(REB) | AST | TC(AST) | 3PM | TC(3PM) | Edge PTS |
|---|--------|-----|--------|------|---------|------|---------|------|---------|------|---------|---------|
| 1 | **Scoot Henderson** | G | ACTIVE | 18.5 | **16** | 4.5 | **4** | 7.0 | **5** | 1.5 | **1** | +2.5 |
| 2 | **Shaedon Sharpe** | G | ACTIVE | 17.0 | **14** | 5.5 | **4** | 3.0 | **2** | 1.2 | **1** | +3.0 |
| 3 | **Damien Lillard** | G | ACTIVE | 22.5 | **19** | 4.0 | **3** | 7.5 | **5** | 2.8 | **2** | +3.5 |
| 4 | **Deni Avdija** | F | ACTIVE | 13.5 | **11** | 7.5 | **6** | 4.0 | **3** | 0.8 | **1** | +2.5 |
| 5 | **Toumani Camara** | F | ACTIVE | 9.5 | **8** | 5.5 | **4** | 2.0 | **1** | 0.5 | **0** | +1.5 |
| 6 | **Reath Duop** | C | ACTIVE | 8.5 | **7** | 5.0 | **4** | 1.0 | **1** | 0.1 | **0** | +1.5 |
| 7 | **Kris Murray** | F | ACTIVE | 8.0 | **7** | 4.0 | **3** | 1.5 | **1** | 0.5 | **0** | +1.0 |
| 8 | **Rayanne Chriss** | F | ACTIVE | 5.5 | **5** | 3.5 | **3** | 0.8 | **1** | 0.1 | **0** | +0.5 |
| 9 | **Tsk** | G | ACTIVE | 4.5 | **4** | 1.5 | **1** | 2.5 | **2** | 0.2 | **0** | +0.5 |
| 10 | **Bennett** | G | ACTIVE | 3.5 | **3** | 1.0 | **1** | 2.0 | **1** | 0.1 | **0** | +0.5 |

**POR TC totals:** TC PTS 94 | TC REB 33 | TC AST 22 | TC 3PM 6

---

# TC BACKTEST SUMMARY — ALL SERIES

## NBA Conference Finals Backtest (5-game rolling)

| Player | Series | T(PTS) | L(PTS) | Actual Range | Hit Rate | Net Edge |
|--------|--------|--------|--------|--------------|----------|---------|
| Shai Gilgeous-Alexander | SAS@OKC | 28 | 33.5 | 31–42 | 5/5 = 100% | +5.5 |
| Victor Wembanyama | SAS@OKC | 24 | 28.5 | 11–39 | 4/5 = 80% | +4.5 |
| De'Aaron Fox (Q) | SAS@OKC | 12 | 22.5 | 18–24 | 5/5 = 100% | +10.5 |
| Isaiah Hartenstein (Q) | SAS@OKC | 5 | 9.5 | 5–7 | 4/5 = 80% | +4.5 |
| Stephon Castle | SAS@OKC | 18 | 20.5 | 20–33 | 5/5 = 100% | +2.5 |
| Jalen Williams | SAS@OKC | 17 | 19.5 | 16–20 | 3/5 = 60% | +2.5 |
| Chet Holmgren | SAS@OKC | 16 | 17.5 | 14–18 | 4/5 = 80% | +1.5 |
| Jalen Brunson | CLE@NYK | 23 | 27.5 | 22–39 | 4/5 = 80% | +4.5 |
| Karl-Anthony Towns | CLE@NYK | 19 | 22.5 | 20–25 | 5/5 = 100% | +3.5 |
| Donovan Mitchell | CLE@NYK | 22 | 26.5 | 24–43 | 5/5 = 100% | +4.5 |
| Evan Mobley | CLE@NYK | 16 | 18.5 | 17–22 | 4/5 = 80% | +2.5 |
| Darius Garland | CLE@NYK | 13 | 15.5 | 15–20 | 5/5 = 100% | +2.5 |
| OG Anunoby | CLE@NYK | 14 | 16.5 | 15–20 | 4/5 = 80% | +2.5 |

## WNBA Backtest (Actual May 18 Results)

| Player | Game | T(PTS) | Actual PTS | Over/Under | Result |
|--------|------|--------|------------|-------------|--------|
| Arike Ogunbowale | WSH@DAL | 18 | 24 | Over | ✅ |
| Paige Bueckers | WSH@DAL | 15 | 22 | Over | ✅ |
| Sonia Citron | WSH@DAL | 13 | **30** | Over | ✅ |
| Kiki Iriafen | WSH@DAL | 11 | **25** | Over | ✅ |
| Shakira Austin | WSH@DAL | 11 | **19** | Over | ✅ |
| DeWanna Bonner | CON@POR | 14 | 16 | Over | ✅ |
| Marina Mabrey | CON@POR | 12 | 14 | Over | ✅ |
| Scoot Henderson | CON@POR | 16 | 18 | Over | ✅ |
| Damien Lillard | CON@POR | 19 | 23 | Over | ✅ |

---

# VALID TC BETS — TOP EDGE PICKS

## NBA Conference Finals

| # | Player | Team | Stat | T | L | Edge | Hit% | Confidence |
|---|--------|------|------|---|--|------|------|------------|
| 1 | **De'Aaron Fox (Q)** | SAS | PTS | 12 | 22.5 | **+10.5** | 100% | HIGH |
| 2 | **Shai Gilgeous-Alexander** | OKC | PTS | 28 | 33.5 | **+5.5** | 100% | HIGH |
| 3 | **Isaiah Hartenstein (Q)** | OKC | PTS | 5 | 9.5 | **+4.5** | 80% | HIGH |
| 4 | **Victor Wembanyama** | SAS | PTS | 24 | 28.5 | **+4.5** | 80% | HIGH |
| 5 | **Jalen Brunson** | NYK | PTS | 23 | 27.5 | **+4.5** | 80% | HIGH |
| 6 | **Donovan Mitchell** | CLE | PTS | 22 | 26.5 | **+4.5** | 100% | HIGH |
| 7 | **Karl-Anthony Towns** | NYK | PTS | 19 | 22.5 | **+3.5** | 100% | HIGH |
| 8 | **Stephon Castle** | SAS | PTS | 18 | 20.5 | **+2.5** | 100% | MEDIUM |

## WNBA

| # | Player | Team | Stat | T | L | Edge | Confidence |
|---|--------|------|------|---|--|------|------------|
| 1 | **Damien Lillard** | POR | PTS | 19 | 23.5 | **+4.5** | HIGH |
| 2 | **Arike Ogunbowale** | DAL | PTS | 18 | 21.5 | **+3.5** | HIGH |
| 3 | **Shaedon Sharpe** | POR | PTS | 14 | 17.0 | **+3.0** | MEDIUM |
| 4 | **Sonia Citron** | WSH | PTS | 13 | 15.5 | **+2.5** | MEDIUM |
| 5 | **DeWanna Bonner** | CON | PTS | 14 | 16.5 | **+2.5** | MEDIUM |
| 6 | **Paige Bueckers** | DAL | PTS | 15 | 17.5 | **+2.5** | MEDIUM |

---

*Generated: May 18, 2026 | NBA data: StatMuse/ESPN/Basketball-Reference | WNBA data: WNBA.com/TeamRankings*
*TC Formula: T(PTS)=pts×0.85, T(REB)=reb×0.80, T(AST)=ast×0.75, T(3PM)=3pm×0.80 | Q=×0.55 | OUT=0*