# Boxscore Combo Backtest (Reconstructed Lines)

Generated: 2026-06-10 22:43:40 ET

Source: ESPN final box scores (last 4 days).

**Methodology**: The Odds API ($30 tier) does not store player combo props
for completed games. To backtest, we reconstruct the implied DK line for each
player's PRA/PR/PA as `round(combo_avg + offset - 0.5) + 0.5`, offsetting by
-2.5, 0.0, and 2.5 (the typical sportsbook posture of pricing 0.5-2.5 below
true average to drive OVER action). For each line, we grade whether the
player's actual combo stat beat the line. This approximates a real DK backtest.

## Overall

| offset | legs | hits | HR |
|--------|------|------|----|
| -2.5 | 267 | 267 | 100.0% |
| 0.0 | 267 | 150 | 56.2% |
| 2.5 | 267 | 0 | 0.0% |

## By sport

| sport | games | legs | hits | HR |
|-------|-------|------|------|----|
| NBA | 1 | 90 | 42 | 46.7% |
| WNBA | 8 | 711 | 375 | 52.7% |

## By combo type

| type | legs | hits | HR |
|------|------|------|----|
| PA | 267 | 139 | 52.1% |
| PR | 267 | 139 | 52.1% |
| PRA | 267 | 139 | 52.1% |

## By game (offset=0.0 only, the 'typical DK posture')

### ATL@CHI — 21/30 (70.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Angel Reese | ATL | PA | 38.5 | 38 | miss by 0.5 |
| Natasha Cloud | CHI | PA | 28.5 | 28 | miss by 0.5 |
| Rhyne Howard | ATL | PA | 24.5 | 25 | HIT |
| Naz Hillmon | ATL | PA | 22.5 | 23 | HIT |
| Skylar Diggins | CHI | PA | 22.5 | 23 | HIT |
| Jordin Canada | ATL | PA | 20.5 | 21 | HIT |
| Kamilla Cardoso | CHI | PA | 20.5 | 20 | miss by 0.5 |
| Allisha Gray | ATL | PA | 18.5 | 19 | HIT |
| Azura Stevens | CHI | PA | 14.5 | 15 | HIT |
| Jacy Sheldon | CHI | PA | 8.5 | 9 | HIT |
| Angel Reese | ATL | PR | 38.5 | 38 | miss by 0.5 |
| Natasha Cloud | CHI | PR | 28.5 | 28 | miss by 0.5 |
| Rhyne Howard | ATL | PR | 24.5 | 25 | HIT |
| Naz Hillmon | ATL | PR | 22.5 | 23 | HIT |
| Skylar Diggins | CHI | PR | 22.5 | 23 | HIT |
| Jordin Canada | ATL | PR | 20.5 | 21 | HIT |
| Kamilla Cardoso | CHI | PR | 20.5 | 20 | miss by 0.5 |
| Allisha Gray | ATL | PR | 18.5 | 19 | HIT |
| Azura Stevens | CHI | PR | 14.5 | 15 | HIT |
| Jacy Sheldon | CHI | PR | 8.5 | 9 | HIT |
| Angel Reese | ATL | PRA | 38.5 | 38 | miss by 0.5 |
| Natasha Cloud | CHI | PRA | 28.5 | 28 | miss by 0.5 |
| Rhyne Howard | ATL | PRA | 24.5 | 25 | HIT |
| Naz Hillmon | ATL | PRA | 22.5 | 23 | HIT |
| Skylar Diggins | CHI | PRA | 22.5 | 23 | HIT |
| Jordin Canada | ATL | PRA | 20.5 | 21 | HIT |
| Kamilla Cardoso | CHI | PRA | 20.5 | 20 | miss by 0.5 |
| Allisha Gray | ATL | PRA | 18.5 | 19 | HIT |
| Azura Stevens | CHI | PRA | 14.5 | 15 | HIT |
| Jacy Sheldon | CHI | PRA | 8.5 | 9 | HIT |

### CHI@TOR — 21/27 (77.8%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Marina Mabrey | TOR | PA | 18.5 | 19 | HIT |
| Jacy Sheldon | CHI | PA | 14.5 | 15 | HIT |
| Maria Conde | TOR | PA | 12.5 | 13 | HIT |
| Elizabeth Williams | CHI | PA | 8.5 | 9 | HIT |
| Rachel Banham | CHI | PA | 6.5 | 6 | miss by 0.5 |
| Saylor Poffenbarger | CHI | PA | 4.5 | 4 | miss by 0.5 |
| Teonni Key | TOR | PA | 4.5 | 5 | HIT |
| Kia Nurse | TOR | PA | 2.5 | 3 | HIT |
| Tima Pouye | TOR | PA | 0.5 | 1 | HIT |
| Marina Mabrey | TOR | PR | 18.5 | 19 | HIT |
| Jacy Sheldon | CHI | PR | 14.5 | 15 | HIT |
| Maria Conde | TOR | PR | 12.5 | 13 | HIT |
| Elizabeth Williams | CHI | PR | 8.5 | 9 | HIT |
| Rachel Banham | CHI | PR | 6.5 | 6 | miss by 0.5 |
| Saylor Poffenbarger | CHI | PR | 4.5 | 4 | miss by 0.5 |
| Teonni Key | TOR | PR | 4.5 | 5 | HIT |
| Kia Nurse | TOR | PR | 2.5 | 3 | HIT |
| Tima Pouye | TOR | PR | 0.5 | 1 | HIT |
| Marina Mabrey | TOR | PRA | 18.5 | 19 | HIT |
| Jacy Sheldon | CHI | PRA | 14.5 | 15 | HIT |
| Maria Conde | TOR | PRA | 12.5 | 13 | HIT |
| Elizabeth Williams | CHI | PRA | 8.5 | 9 | HIT |
| Rachel Banham | CHI | PRA | 6.5 | 6 | miss by 0.5 |
| Saylor Poffenbarger | CHI | PRA | 4.5 | 4 | miss by 0.5 |
| Teonni Key | TOR | PRA | 4.5 | 5 | HIT |
| Kia Nurse | TOR | PRA | 2.5 | 3 | HIT |
| Tima Pouye | TOR | PRA | 0.5 | 1 | HIT |

### DAL@MIN — 18/30 (60.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Courtney Williams | MIN | PA | 26.5 | 26 | miss by 0.5 |
| Aziaha James | DAL | PA | 14.5 | 14 | miss by 0.5 |
| Anastasiia Olairi Kosu | MIN | PA | 12.5 | 13 | HIT |
| Costanza Verona | DAL | PA | 6.5 | 6 | miss by 0.5 |
| Li Yueru | DAL | PA | 4.5 | 4 | miss by 0.5 |
| Antonia Delaere | MIN | PA | 4.5 | 5 | HIT |
| Maya Caldwell | MIN | PA | 4.5 | 5 | HIT |
| JJ Quinerly | DAL | PA | 2.5 | 3 | HIT |
| Alysha Clark | DAL | PA | 0.5 | 1 | HIT |
| Teaira McCowan | MIN | PA | 0.5 | 1 | HIT |
| Courtney Williams | MIN | PR | 26.5 | 26 | miss by 0.5 |
| Aziaha James | DAL | PR | 14.5 | 14 | miss by 0.5 |
| Anastasiia Olairi Kosu | MIN | PR | 12.5 | 13 | HIT |
| Costanza Verona | DAL | PR | 6.5 | 6 | miss by 0.5 |
| Li Yueru | DAL | PR | 4.5 | 4 | miss by 0.5 |
| Antonia Delaere | MIN | PR | 4.5 | 5 | HIT |
| Maya Caldwell | MIN | PR | 4.5 | 5 | HIT |
| JJ Quinerly | DAL | PR | 2.5 | 3 | HIT |
| Alysha Clark | DAL | PR | 0.5 | 1 | HIT |
| Teaira McCowan | MIN | PR | 0.5 | 1 | HIT |
| Courtney Williams | MIN | PRA | 26.5 | 26 | miss by 0.5 |
| Aziaha James | DAL | PRA | 14.5 | 14 | miss by 0.5 |
| Anastasiia Olairi Kosu | MIN | PRA | 12.5 | 13 | HIT |
| Costanza Verona | DAL | PRA | 6.5 | 6 | miss by 0.5 |
| Li Yueru | DAL | PRA | 4.5 | 4 | miss by 0.5 |
| Antonia Delaere | MIN | PRA | 4.5 | 5 | HIT |
| Maya Caldwell | MIN | PRA | 4.5 | 5 | HIT |
| JJ Quinerly | DAL | PRA | 2.5 | 3 | HIT |
| Alysha Clark | DAL | PRA | 0.5 | 1 | HIT |
| Teaira McCowan | MIN | PRA | 0.5 | 1 | HIT |

### IND@WSH — 24/30 (80.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Aliyah Boston | IND | PA | 26.5 | 27 | HIT |
| Caitlin Clark | IND | PA | 26.5 | 27 | HIT |
| Shakira Austin | WSH | PA | 22.5 | 23 | HIT |
| Kelsey Mitchell | IND | PA | 20.5 | 20 | miss by 0.5 |
| Michaela Onyenwere | WSH | PA | 20.5 | 20 | miss by 0.5 |
| Sonia Citron | WSH | PA | 16.5 | 17 | HIT |
| Georgia Amoore | WSH | PA | 16.5 | 17 | HIT |
| Cotie McMahon | WSH | PA | 16.5 | 17 | HIT |
| Sophie Cunningham | IND | PA | 12.5 | 13 | HIT |
| Lexie Hull | IND | PA | 10.5 | 11 | HIT |
| Aliyah Boston | IND | PR | 26.5 | 27 | HIT |
| Caitlin Clark | IND | PR | 26.5 | 27 | HIT |
| Shakira Austin | WSH | PR | 22.5 | 23 | HIT |
| Kelsey Mitchell | IND | PR | 20.5 | 20 | miss by 0.5 |
| Michaela Onyenwere | WSH | PR | 20.5 | 20 | miss by 0.5 |
| Sonia Citron | WSH | PR | 16.5 | 17 | HIT |
| Georgia Amoore | WSH | PR | 16.5 | 17 | HIT |
| Cotie McMahon | WSH | PR | 16.5 | 17 | HIT |
| Sophie Cunningham | IND | PR | 12.5 | 13 | HIT |
| Lexie Hull | IND | PR | 10.5 | 11 | HIT |
| Aliyah Boston | IND | PRA | 26.5 | 27 | HIT |
| Caitlin Clark | IND | PRA | 26.5 | 27 | HIT |
| Shakira Austin | WSH | PRA | 22.5 | 23 | HIT |
| Kelsey Mitchell | IND | PRA | 20.5 | 20 | miss by 0.5 |
| Michaela Onyenwere | WSH | PRA | 20.5 | 20 | miss by 0.5 |
| Sonia Citron | WSH | PRA | 16.5 | 17 | HIT |
| Georgia Amoore | WSH | PRA | 16.5 | 17 | HIT |
| Cotie McMahon | WSH | PRA | 16.5 | 17 | HIT |
| Sophie Cunningham | IND | PRA | 12.5 | 13 | HIT |
| Lexie Hull | IND | PRA | 10.5 | 11 | HIT |

### NY@CON — 9/30 (30.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Breanna Stewart | NY | PA | 40.5 | 40 | miss by 0.5 |
| Olivia Nelson-Ododa | CON | PA | 24.5 | 24 | miss by 0.5 |
| Aaliyah Edwards | CON | PA | 20.5 | 20 | miss by 0.5 |
| Saniya Rivers | CON | PA | 20.5 | 20 | miss by 0.5 |
| Betnijah Laney-Hamilton | NY | PA | 16.5 | 16 | miss by 0.5 |
| Diamond Miller | CON | PA | 14.5 | 14 | miss by 0.5 |
| Leila Lacan | CON | PA | 14.5 | 14 | miss by 0.5 |
| Leonie Fiebich | NY | PA | 12.5 | 13 | HIT |
| Pauline Astier | NY | PA | 12.5 | 13 | HIT |
| Satou Sabally | NY | PA | 12.5 | 13 | HIT |
| Breanna Stewart | NY | PR | 40.5 | 40 | miss by 0.5 |
| Olivia Nelson-Ododa | CON | PR | 24.5 | 24 | miss by 0.5 |
| Aaliyah Edwards | CON | PR | 20.5 | 20 | miss by 0.5 |
| Saniya Rivers | CON | PR | 20.5 | 20 | miss by 0.5 |
| Betnijah Laney-Hamilton | NY | PR | 16.5 | 16 | miss by 0.5 |
| Diamond Miller | CON | PR | 14.5 | 14 | miss by 0.5 |
| Leila Lacan | CON | PR | 14.5 | 14 | miss by 0.5 |
| Leonie Fiebich | NY | PR | 12.5 | 13 | HIT |
| Pauline Astier | NY | PR | 12.5 | 13 | HIT |
| Satou Sabally | NY | PR | 12.5 | 13 | HIT |
| Breanna Stewart | NY | PRA | 40.5 | 40 | miss by 0.5 |
| Olivia Nelson-Ododa | CON | PRA | 24.5 | 24 | miss by 0.5 |
| Aaliyah Edwards | CON | PRA | 20.5 | 20 | miss by 0.5 |
| Saniya Rivers | CON | PRA | 20.5 | 20 | miss by 0.5 |
| Betnijah Laney-Hamilton | NY | PRA | 16.5 | 16 | miss by 0.5 |
| Diamond Miller | CON | PRA | 14.5 | 14 | miss by 0.5 |
| Leila Lacan | CON | PRA | 14.5 | 14 | miss by 0.5 |
| Leonie Fiebich | NY | PRA | 12.5 | 13 | HIT |
| Pauline Astier | NY | PRA | 12.5 | 13 | HIT |
| Satou Sabally | NY | PRA | 12.5 | 13 | HIT |

### PHX@GS — 9/30 (30.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Alyssa Thomas | PHX | PA | 38.5 | 39 | HIT |
| Veronica Burton | GS | PA | 36.5 | 36 | miss by 0.5 |
| Gabby Williams | GS | PA | 30.5 | 30 | miss by 0.5 |
| Monique Akoa Makani | PHX | PA | 24.5 | 25 | HIT |
| Natasha Mack | PHX | PA | 20.5 | 20 | miss by 0.5 |
| Kayla Thornton | GS | PA | 18.5 | 18 | miss by 0.5 |
| Janelle Salaun | GS | PA | 16.5 | 16 | miss by 0.5 |
| Kahleah Copper | PHX | PA | 14.5 | 14 | miss by 0.5 |
| Kaila Charles | GS | PA | 10.5 | 10 | miss by 0.5 |
| DeWanna Bonner | PHX | PA | 6.5 | 7 | HIT |
| Alyssa Thomas | PHX | PR | 38.5 | 39 | HIT |
| Veronica Burton | GS | PR | 36.5 | 36 | miss by 0.5 |
| Gabby Williams | GS | PR | 30.5 | 30 | miss by 0.5 |
| Monique Akoa Makani | PHX | PR | 24.5 | 25 | HIT |
| Natasha Mack | PHX | PR | 20.5 | 20 | miss by 0.5 |
| Kayla Thornton | GS | PR | 18.5 | 18 | miss by 0.5 |
| Janelle Salaun | GS | PR | 16.5 | 16 | miss by 0.5 |
| Kahleah Copper | PHX | PR | 14.5 | 14 | miss by 0.5 |
| Kaila Charles | GS | PR | 10.5 | 10 | miss by 0.5 |
| DeWanna Bonner | PHX | PR | 6.5 | 7 | HIT |
| Alyssa Thomas | PHX | PRA | 38.5 | 39 | HIT |
| Veronica Burton | GS | PRA | 36.5 | 36 | miss by 0.5 |
| Gabby Williams | GS | PRA | 30.5 | 30 | miss by 0.5 |
| Monique Akoa Makani | PHX | PRA | 24.5 | 25 | HIT |
| Natasha Mack | PHX | PRA | 20.5 | 20 | miss by 0.5 |
| Kayla Thornton | GS | PRA | 18.5 | 18 | miss by 0.5 |
| Janelle Salaun | GS | PRA | 16.5 | 16 | miss by 0.5 |
| Kahleah Copper | PHX | PRA | 14.5 | 14 | miss by 0.5 |
| Kaila Charles | GS | PRA | 10.5 | 10 | miss by 0.5 |
| DeWanna Bonner | PHX | PRA | 6.5 | 7 | HIT |

### POR@LA — 18/30 (60.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Nneka Ogwumike | LA | PA | 38.5 | 39 | HIT |
| Dearica Hamby | LA | PA | 34.5 | 34 | miss by 0.5 |
| Kelsey Plum | LA | PA | 28.5 | 29 | HIT |
| Megan Gustafson | POR | PA | 26.5 | 27 | HIT |
| Emily Engstler | POR | PA | 18.5 | 18 | miss by 0.5 |
| Bridget Carleton | POR | PA | 16.5 | 16 | miss by 0.5 |
| Sarah Ashlee Barker | POR | PA | 14.5 | 15 | HIT |
| Rae Burrell | LA | PA | 14.5 | 14 | miss by 0.5 |
| Erica Wheeler | LA | PA | 10.5 | 11 | HIT |
| Teja Oblak | POR | PA | 8.5 | 9 | HIT |
| Nneka Ogwumike | LA | PR | 38.5 | 39 | HIT |
| Dearica Hamby | LA | PR | 34.5 | 34 | miss by 0.5 |
| Kelsey Plum | LA | PR | 28.5 | 29 | HIT |
| Megan Gustafson | POR | PR | 26.5 | 27 | HIT |
| Emily Engstler | POR | PR | 18.5 | 18 | miss by 0.5 |
| Bridget Carleton | POR | PR | 16.5 | 16 | miss by 0.5 |
| Sarah Ashlee Barker | POR | PR | 14.5 | 15 | HIT |
| Rae Burrell | LA | PR | 14.5 | 14 | miss by 0.5 |
| Erica Wheeler | LA | PR | 10.5 | 11 | HIT |
| Teja Oblak | POR | PR | 8.5 | 9 | HIT |
| Nneka Ogwumike | LA | PRA | 38.5 | 39 | HIT |
| Dearica Hamby | LA | PRA | 34.5 | 34 | miss by 0.5 |
| Kelsey Plum | LA | PRA | 28.5 | 29 | HIT |
| Megan Gustafson | POR | PRA | 26.5 | 27 | HIT |
| Emily Engstler | POR | PRA | 18.5 | 18 | miss by 0.5 |
| Bridget Carleton | POR | PRA | 16.5 | 16 | miss by 0.5 |
| Sarah Ashlee Barker | POR | PRA | 14.5 | 15 | HIT |
| Rae Burrell | LA | PRA | 14.5 | 14 | miss by 0.5 |
| Erica Wheeler | LA | PRA | 10.5 | 11 | HIT |
| Teja Oblak | POR | PRA | 8.5 | 9 | HIT |

### SA@NY — 12/30 (40.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| Victor Wembanyama | SA | PA | 46.5 | 46 | miss by 0.5 |
| Jalen Brunson | NY | PA | 42.5 | 42 | miss by 0.5 |
| OG Anunoby | NY | PA | 34.5 | 34 | miss by 0.5 |
| Stephon Castle | SA | PA | 32.5 | 33 | HIT |
| Josh Hart | NY | PA | 30.5 | 30 | miss by 0.5 |
| Dylan Harper | SA | PA | 26.5 | 26 | miss by 0.5 |
| De'Aaron Fox | SA | PA | 22.5 | 23 | HIT |
| Karl-Anthony Towns | NY | PA | 20.5 | 20 | miss by 0.5 |
| Devin Vassell | SA | PA | 14.5 | 15 | HIT |
| Mikal Bridges | NY | PA | 8.5 | 9 | HIT |
| Victor Wembanyama | SA | PR | 46.5 | 46 | miss by 0.5 |
| Jalen Brunson | NY | PR | 42.5 | 42 | miss by 0.5 |
| OG Anunoby | NY | PR | 34.5 | 34 | miss by 0.5 |
| Stephon Castle | SA | PR | 32.5 | 33 | HIT |
| Josh Hart | NY | PR | 30.5 | 30 | miss by 0.5 |
| Dylan Harper | SA | PR | 26.5 | 26 | miss by 0.5 |
| De'Aaron Fox | SA | PR | 22.5 | 23 | HIT |
| Karl-Anthony Towns | NY | PR | 20.5 | 20 | miss by 0.5 |
| Devin Vassell | SA | PR | 14.5 | 15 | HIT |
| Mikal Bridges | NY | PR | 8.5 | 9 | HIT |
| Victor Wembanyama | SA | PRA | 46.5 | 46 | miss by 0.5 |
| Jalen Brunson | NY | PRA | 42.5 | 42 | miss by 0.5 |
| OG Anunoby | NY | PRA | 34.5 | 34 | miss by 0.5 |
| Stephon Castle | SA | PRA | 32.5 | 33 | HIT |
| Josh Hart | NY | PRA | 30.5 | 30 | miss by 0.5 |
| Dylan Harper | SA | PRA | 26.5 | 26 | miss by 0.5 |
| De'Aaron Fox | SA | PRA | 22.5 | 23 | HIT |
| Karl-Anthony Towns | NY | PRA | 20.5 | 20 | miss by 0.5 |
| Devin Vassell | SA | PRA | 14.5 | 15 | HIT |
| Mikal Bridges | NY | PRA | 8.5 | 9 | HIT |

### SEA@LV — 18/30 (60.0%)

| player | team | type | line | actual | result |
|--------|------|------|------|--------|--------|
| A'ja Wilson | LV | PA | 54.5 | 55 | HIT |
| Jackie Young | LV | PA | 38.5 | 38 | miss by 0.5 |
| Natisha Hiedeman | SEA | PA | 26.5 | 27 | HIT |
| Dominique Malonga | SEA | PA | 24.5 | 24 | miss by 0.5 |
| NaLyssa Smith | LV | PA | 24.5 | 25 | HIT |
| Chelsea Gray | LV | PA | 24.5 | 25 | HIT |
| Flau'jae Johnson | SEA | PA | 22.5 | 22 | miss by 0.5 |
| Awa Fam | SEA | PA | 20.5 | 20 | miss by 0.5 |
| Jade Melbourne | SEA | PA | 10.5 | 11 | HIT |
| Jewell Loyd | LV | PA | 6.5 | 7 | HIT |
| A'ja Wilson | LV | PR | 54.5 | 55 | HIT |
| Jackie Young | LV | PR | 38.5 | 38 | miss by 0.5 |
| Natisha Hiedeman | SEA | PR | 26.5 | 27 | HIT |
| Dominique Malonga | SEA | PR | 24.5 | 24 | miss by 0.5 |
| NaLyssa Smith | LV | PR | 24.5 | 25 | HIT |
| Chelsea Gray | LV | PR | 24.5 | 25 | HIT |
| Flau'jae Johnson | SEA | PR | 22.5 | 22 | miss by 0.5 |
| Awa Fam | SEA | PR | 20.5 | 20 | miss by 0.5 |
| Jade Melbourne | SEA | PR | 10.5 | 11 | HIT |
| Jewell Loyd | LV | PR | 6.5 | 7 | HIT |
| A'ja Wilson | LV | PRA | 54.5 | 55 | HIT |
| Jackie Young | LV | PRA | 38.5 | 38 | miss by 0.5 |
| Natisha Hiedeman | SEA | PRA | 26.5 | 27 | HIT |
| Dominique Malonga | SEA | PRA | 24.5 | 24 | miss by 0.5 |
| NaLyssa Smith | LV | PRA | 24.5 | 25 | HIT |
| Chelsea Gray | LV | PRA | 24.5 | 25 | HIT |
| Flau'jae Johnson | SEA | PRA | 22.5 | 22 | miss by 0.5 |
| Awa Fam | SEA | PRA | 20.5 | 20 | miss by 0.5 |
| Jade Melbourne | SEA | PRA | 10.5 | 11 | HIT |
| Jewell Loyd | LV | PRA | 6.5 | 7 | HIT |
