# NBA TC Pregame Report — CLE @ NYK ECF Game 1

**Live scrape/API source:** ESPN scoreboard odds (DraftKings): NY -6.5, total 217.5.
**FastAPI:** running on port 8001.
**Rule:** TC match applies only to player props: PTS, REB, AST, 3PM. Game total is separate pace context only.

## Game Context
- Matchup: CLE @ NYK
- Market total: 217.5
- Market spread: NYK -6.5
- Game pace estimate: 282.0 (UNDER)

## CLE — Cleveland Cavaliers
| Player | Pos | Status | TC PTS | T PTS | TC REB | T REB | TC AST | T AST | TC 3PM | T 3PM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Donovan Mitchell | G | ACTIVE | 20.8 | 18 | 4.2 | 3 | 3.8 | 3 | 2.5 | 2 |
| Darius Garland | G | ACTIVE | 17.0 | 14 | 3.0 | 2 | 5.1 | 4 | 2.1 | 1 |
| Evan Mobley | F | ACTIVE | 15.3 | 13 | 7.6 | 6 | 3.0 | 2 | 1.0 | 0 |
| Jarrett Allen | C | ACTIVE | 11.9 | 10 | 6.8 | 5 | 1.7 | 1 | 0.4 | 0 |
| Max Strus | F | ACTIVE | 10.6 | 9 | 3.8 | 3 | 3.0 | 2 | 2.1 | 1 |
| Isaac Okoro | G | ACTIVE | 8.5 | 7 | 3.0 | 2 | 2.5 | 2 | 1.0 | 0 |
| Georges Niang | F | ACTIVE | 7.6 | 6 | 2.5 | 2 | 1.3 | 1 | 1.7 | 1 |
| Caris LeVert | G | Q | 5.4 | 4 | 1.6 | 1 | 1.6 | 1 | 0.8 | 0 |
| Tristan Thompson | C | ACTIVE | 5.1 | 4 | 4.7 | 4 | 0.8 | 0 | 0.0 | 0 |
| Ty Jerome | G | ACTIVE | 4.7 | 4 | 1.7 | 1 | 2.1 | 1 | 0.8 | 0 |

## NYK — New York Knicks
| Player | Pos | Status | TC PTS | T PTS | TC REB | T REB | TC AST | T AST | TC 3PM | T 3PM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Mikal Bridges | F | ACTIVE | 17.8 | 15 | 3.8 | 3 | 3.0 | 2 | 2.4 | 2 |
| Josh Hart | G | ACTIVE | 13.2 | 11 | 3.8 | 3 | 4.2 | 3 | 1.7 | 1 |
| Karl-Anthony Towns | C | ACTIVE | 21.2 | 18 | 10.6 | 9 | 3.0 | 2 | 1.9 | 1 |
| Jalen Brunson | G | Q | 11.5 | 10 | 1.6 | 1 | 3.0 | 2 | 1.0 | 0 |
| Miles McBride | G | ACTIVE | 8.9 | 7 | 2.1 | 1 | 2.5 | 2 | 1.7 | 1 |
| OG Anunoby | F | ACTIVE | 14.9 | 13 | 4.2 | 3 | 1.7 | 1 | 2.1 | 1 |
| Cameron Payne | G | ACTIVE | 6.4 | 5 | 1.7 | 1 | 3.0 | 2 | 1.0 | 0 |
| Jacob Topp | F | ACTIVE | 5.5 | 4 | 3.0 | 2 | 0.8 | 0 | 0.7 | 0 |
| Jericho Sims | C | ACTIVE | 4.7 | 4 | 4.2 | 3 | 0.4 | 0 | 0.3 | 0 |

## Valid Prop Edges
| Player | Team | Stat | TC Target | Book Line | Edge |
|---|---|---:|---:|---:|---:|
| Donovan Mitchell | CLE | PTS | 18 | 24.5 | 6.5 |
| Darius Garland | CLE | PTS | 14 | 20.0 | 6.0 |
| Evan Mobley | CLE | PTS | 13 | 18.0 | 5.0 |
| Evan Mobley | CLE | REB | 6 | 9.0 | 3.0 |
| Jarrett Allen | CLE | PTS | 10 | 14.0 | 4.0 |
| Jarrett Allen | CLE | REB | 5 | 8.0 | 3.0 |
| Max Strus | CLE | PTS | 9 | 12.5 | 3.5 |
| Isaac Okoro | CLE | PTS | 7 | 10.0 | 3.0 |
| Georges Niang | CLE | PTS | 6 | 9.0 | 3.0 |
| Caris LeVert | CLE | PTS | 4 | 11.5 | 7.5 |
| Mikal Bridges | NYK | PTS | 15 | 21.0 | 6.0 |
| Josh Hart | NYK | PTS | 11 | 15.5 | 4.5 |
| Karl-Anthony Towns | NYK | PTS | 18 | 25.0 | 7.0 |
| Karl-Anthony Towns | NYK | REB | 9 | 12.5 | 3.5 |
| Jalen Brunson | NYK | PTS | 10 | 24.5 | 14.5 |
| Jalen Brunson | NYK | AST | 2 | 6.5 | 4.5 |
| Miles McBride | NYK | PTS | 7 | 10.5 | 3.5 |
| OG Anunoby | NYK | PTS | 13 | 17.5 | 4.5 |