Zo, focus on the 'Live Combos Generator' specifically for WNBA data. There was a typo earlier: it is 'tc math', NOT 'tc match'. 

I need you to fine-tune the live generator to integrate our specific 'TC Math' logic for WNBA games only.  
1\. Review the mathematical formulas calculating the live lines for Points+Rebounds+Assists (PRA), Points+Rebounds (PR), and Points+Assists (PA).  
2\. Adjust the TC Math weighting parameters to account for WNBA-specific game dynamics (such as the 40-minute game length compared to the NBA's 48 minutes, pacing, and possessions).  
3\. Ensure the live generator recalculates these TC Math projections in real-time as live stats scrape in, updating the WNBA dashboard mid-game without lagging or bleeding into NBA baseline math.

Update the source files for the live generator with this corrected WNBA TC Math logic and confirm when it is active.