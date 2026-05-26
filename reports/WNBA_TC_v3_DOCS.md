# WNBA TC ENGINE v3.0 — Complete League Coverage

## Setup for Live Odds

**Step 1: Get API Key**
1. Sign up at https://the-odds-api.com/account/
2. Copy your API key (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

**Step 2: Add to Zo Secrets**
1. Go to [Settings > Advanced](/?t=settings&s=advanced)
2. In the **Secrets** section, add:
   - Key: `ODDS_API_KEY`
   - Value: your API key
3. Save

**Step 3: Test**
```bash
python wnba_tc_v3.py --live 'NY @ LV'
```

---

## Commands

| Command | Description |
|---------|-------------|
| `--backtest` | Run 5-game historical validation |
| `--live 'AWAY @ HOME'` | Generate TC report with live odds |
| `--total 175.5` | Override market total |
| `--list-teams` | Show all 15 WNBA teams |

---

## All 15 WNBA Teams

| Abbr | Team | Key Players |
|------|------|-------------|
| ATL | Atlanta Dream | Rhyne Howard, Allisha Gray |
| CHI | Chicago Sky | Angel Reese, Kamilla Cardoso |
| CON | Connecticut Sun | Alyssa Thomas, DeWanna Bonner |
| DAL | Dallas Wings | Arike Ogunbowale, Satou Sabally |
| GS | Golden State Valkyries | Kate Martin, Tiffany Hayes |
| IND | Indiana Fever | **Caitlin Clark**, Aliyah Boston |
| LV | Las Vegas Aces | **A'ja Wilson**, Chelsea Gray |
| LA | Los Angeles Sparks | Rickea Jackson, Dearica Hamby |
| MIN | Minnesota Lynx | Napheesa Collier, Kayla McBride |
| NY | New York Liberty | **Breanna Stewart**, Sabrina Ionescu |
| PHX | Phoenix Mercury | Kahleah Copper, Brittney Griner |
| POR | Portland Fire | Sedona Prince, Aari McDonald |
| SEA | Seattle Storm | Jewell Loyd, Skylar Diggins-Smith |
| TOR | Toronto Tempo | Kia Nurse, Natalie Achonwa |
| WSH | Washington Mystics | Elena Delle Donne, Shakira Austin |

---

## TC Formula

```
TC = pts×0.85 + reb×0.12 + ast×0.10 + tpm×0.08
LINE = (TC + 4.5) × 0.88
```

**Injury Adjustments:**
- QUESTIONABLE → TC × 0.55
- OUT → 0

---

## Sample Output

```
NY @ LV | WNBA
Series: Regular Season | Total: 170.5

-- NY New York Liberty (Away)--
Player                 POS  HT      PTS   REB   AST  3PM  TC_TOT  LINE  EDGE
Breanna Stewart        F    6-4    22.5   9.1   3.8  1.8    20.7    22  -1.3
Sabrina Ionescu        G    5-11   18.3   5.5   6.2  3.1    17.1    19  -1.9
...

Team TC: 72.5 (pts:65.9 + reb:3.65 + ast:2.21 + tpm:0.71)

TC Combined: 145.8 | Market: 170.5 | Edge: +13.8
Signal: UNDER | Confidence: HIGH
```

---

## File

- **Google Drive:** https://drive.google.com/file/d/1JDOcBR3hdNAUornDULwnIOlLuvlsQZ7E

---

## Notes

- WNBA games typically total 160-180 points (lower than NBA)
- Historical gap adjusted to +4.5 for WNBA scoring
- Home pace adjustment: ×1.02
- API supports DraftKings, FanDuel, BetMGM, Caesars odds
