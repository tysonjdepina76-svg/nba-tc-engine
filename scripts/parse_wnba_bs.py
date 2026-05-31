#!/usr/bin/env python3
"""WNBA boxscore parser from ESPN HTML"""
import re

def parse_bs(html_path, away_abbr, home_abbr):
    with open(html_path) as f:
        content = f.read()
    
    # Extract all athlete name spans
    name_spans = re.findall(r'<span class="[^"]*Boxscore__AthleteName[^"]*"[^>]*>([^<]+)</span>', content)
    name_spans = [n.strip().replace('&#x27;', "'").replace('&amp;', '&') for n in name_spans if n.strip()]
    
    # Extract all stat cells
    stat_cells = re.findall(r'<td class="Table__TD[^"]*"[^>]*>([\d\-]+|[\d]+-[\d]+)</td>', content)
    
    # Find team separators
    team_sections = content.split('class="featuredTeam"')
    # Each featuredTeam section has players for one team
    
    players = []
    
    # Parse per section
    # Each team section has players in rows, each row has name spans followed by stat cells
    # Format: Full Name, Short Name, (then stat cells)
    # For each player row, we get: min, fgm-fga, 3pm-3pa, ftm-fta, pts, reb, ast, etc.
    
    # Let's count: first team has ~15 players, stats per player ~8+ (min, fgm-fga, 3pm-3pa, ftm-fta, pts, reb, ast, stl, blk, to, pf)
    # That's 11 stat columns
    
    stat_cols = 11  # MIN, FG, 3PT, FT, PTS, REB, AST, STL, BLK, TO, PF
    
    # Process all stat cells into rows
    rows = []
    for i in range(0, len(stat_cells), stat_cols):
        row = stat_cells[i:i+stat_cols]
        if len(row) == stat_cols:
            rows.append(row)
    
    # First N rows are away team, rest are home team
    away_count = name_spans.count(next((n for n in name_spans if ' ' in n), name_spans[0]))
    # Actually we need to figure out where teams split
    # Look for team name headers in the HTML
    # Find the away and home team sections
    sections = content.split('class="featuredTeam"')
    print(f"Team sections: {len(sections)}")
    
    # Each section has one team's players - count stat rows in each
    # Actually easier: we know name_spans has alternating full/short names per player
    # Each player has 2 name entries + stat row
    # Count players per team by finding team label in the content
    # The team name appears in the header
    
    team_labels = re.findall(r'class="Boxscore__TeamName[^"]*"[^>]*>([^<]+)</div>', content)
    print(f"Team labels: {team_labels}")
    
    # Count rows by finding Table__TR rows with player content
    tr_rows = re.findall(r'<tr class="Table__TR[^"]*"[^>]*>(.*?)</tr>', content, re.DOTALL)
    away_rows = []
    home_rows = []
    is_away = True
    for row in tr_rows:
        cells = re.findall(r'<td class="Table__TD[^"]*"[^>]*>([\d\-]+|[\d]+-[\d]+)</td>', row)
        if len(cells) >= stat_cols:
            if is_away:
                away_rows.append(cells[:stat_cols])
            else:
                home_rows.append(cells[:stat_cols])
        elif cells and 'DNP' in row:
            continue
        elif 'featuredTeam' in row or 'nonFeatured' in row:
            is_away = not is_away
    
    print(f"Away rows: {len(away_rows)}, Home rows: {len(home_rows)}")
    print(f"Away names count: {len(name_spans)//2}, Home names count: {len(name_spans) - len(name_spans)//2}")
    
    return name_spans, away_rows, home_rows

for path, away, home in [
    ('/tmp/wnba_bs_401856949.html', 'SEA', 'TOR'),
    ('/tmp/wnba_bs_401856950.html', 'CON', 'LA'),
    ('/tmp/wnba_bs_401856951.html', 'POR', 'IND'),
]:
    parse_bs(path, away, home)
