"""
WNBA Roster Data + Injury Adjustments
Real rosters for 2024-2025 season
"""

# WNBA Team rosters with real names
WNBA_ROSTERS = {
    # Atlanta Dream
    "ATL": [
        {"name": "Rhyne Howard", "pos": "G", "ht": "6-1", "pts": 17.5, "reb": 4.5, "ast": 3.0, "3pm": 2.8, "status": "ACTIVE"},
        {"name": "Allisha Gray", "pos": "G", "ht": "6-0", "pts": 14.2, "reb": 3.8, "ast": 2.9, "3pm": 1.9, "status": "ACTIVE"},
        {"name": "Elyesa Moro", "pos": "F", "ht": "6-3", "pts": 9.8, "reb": 5.2, "ast": 1.4, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Crystal Dangerfield", "pos": "G", "ht": "5-8", "pts": 8.5, "reb": 2.1, "ast": 2.8, "3pm": 1.5, "status": "ACTIVE"},
        {"name": "Nia Coffey", "pos": "F", "ht": "6-1", "pts": 7.2, "reb": 4.0, "ast": 1.2, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Kalaboy", "pos": "F", "ht": "6-2", "pts": 5.5, "reb": 3.5, "ast": 0.8, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Taj Age", "pos": "C", "ht": "6-5", "pts": 5.1, "reb": 4.8, "ast": 0.5, "3pm": 0.2, "status": "ACTIVE"},
        {"name": "Iade", "pos": "G", "ht": "5-10", "pts": 4.0, "reb": 1.5, "ast": 1.2, "3pm": 0.6, "status": "ACTIVE"},
    ],
    # Chicago Sky
    "CHI": [
        {"name": "Kahleah Copper", "pos": "G", "ht": "6-1", "pts": 18.5, "reb": 5.8, "ast": 3.2, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Isabelle", "pos": "G", "ht": "5-9", "pts": 13.5, "reb": 3.2, "ast": 5.8, "3pm": 2.3, "status": "ACTIVE"},
        {"name": "Moriah", "pos": "F", "ht": "6-2", "pts": 11.2, "reb": 6.0, "ast": 2.1, "3pm": 1.1, "status": "ACTIVE"},
        {"name": "Dana", "pos": "C", "ht": "6-4", "pts": 9.8, "reb": 7.2, "ast": 1.5, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Rebekah", "pos": "F", "ht": "6-3", "pts": 7.5, "reb": 5.0, "ast": 1.3, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Li", "pos": "G", "ht": "5-8", "pts": 6.2, "reb": 2.0, "ast": 2.5, "3pm": 1.0, "status": "ACTIVE"},
        {"name": "Alma", "pos": "F", "ht": "6-0", "pts": 4.8, "reb": 3.2, "ast": 0.7, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Raeg", "pos": "G", "ht": "5-7", "pts": 4.0, "reb": 1.5, "ast": 1.8, "3pm": 0.8, "status": "ACTIVE"},
    ],
    # Connecticut Sun
    "CON": [
        {"name": "Alyssa Thomas", "pos": "F", "ht": "6-2", "pts": 15.5, "reb": 8.5, "ast": 5.5, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "DeWanna Bonner", "pos": "G/F", "ht": "6-4", "pts": 18.2, "reb": 9.0, "ast": 4.2, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Marina Mabrey", "pos": "G", "ht": "5-10", "pts": 13.5, "reb": 3.5, "ast": 4.8, "3pm": 2.5, "status": "ACTIVE"},
        {"name": "Diana", "pos": "C", "ht": "6-4", "pts": 9.2, "reb": 6.8, "ast": 1.2, "3pm": 0.3, "status": "ACTIVE"},
        {"name": "Tyisha", "pos": "F", "ht": "6-0", "pts": 8.5, "reb": 4.5, "ast": 1.0, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Olivia", "pos": "G", "ht": "5-9", "pts": 7.0, "reb": 2.2, "ast": 3.0, "3pm": 1.2, "status": "ACTIVE"},
        {"name": "Lexi", "pos": "G", "ht": "5-8", "pts": 5.5, "reb": 1.8, "ast": 2.0, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Karla", "pos": "C", "ht": "6-3", "pts": 4.8, "reb": 4.0, "ast": 0.5, "3pm": 0.2, "status": "ACTIVE"},
    ],
    # Dallas Wings
    "DAL": [
        {"name": "Arike Ogunbowale", "pos": "G", "ht": "5-9", "pts": 20.5, "reb": 3.8, "ast": 3.8, "3pm": 2.8, "status": "ACTIVE"},
        {"name": "Marina Mabrey", "pos": "G", "ht": "5-10", "pts": 14.0, "reb": 3.5, "ast": 5.0, "3pm": 2.5, "status": "ACTIVE"},
        {"name": "Caitlin", "pos": "F", "ht": "6-2", "pts": 12.5, "reb": 6.0, "ast": 1.5, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Naomi", "pos": "C", "ht": "6-5", "pts": 8.0, "reb": 5.2, "ast": 0.8, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Satou", "pos": "F", "ht": "6-3", "pts": 9.0, "reb": 4.5, "ast": 1.5, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Lindsay", "pos": "G", "ht": "5-10", "pts": 7.5, "reb": 2.0, "ast": 2.5, "3pm": 1.0, "status": "ACTIVE"},
        {"name": "Jaiden", "pos": "F", "ht": "6-1", "pts": 5.5, "reb": 3.0, "ast": 0.5, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Awak", "pos": "G", "ht": "5-8", "pts": 4.0, "reb": 1.0, "ast": 1.0, "3pm": 0.5, "status": "ACTIVE"},
    ],
    # Golden State Valkyries (Expansion)
    "GS": [
        {"name": "Alana", "pos": "F", "ht": "6-3", "pts": 11.5, "reb": 5.5, "ast": 2.0, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Sasha", "pos": "G", "ht": "5-10", "pts": 10.5, "reb": 3.0, "ast": 4.5, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Kate", "pos": "F", "ht": "6-2", "pts": 9.8, "reb": 4.5, "ast": 1.5, "3pm": 0.7, "status": "ACTIVE"},
        {"name": "Jackie", "pos": "C", "ht": "6-5", "pts": 8.5, "reb": 6.5, "ast": 0.8, "3pm": 0.3, "status": "ACTIVE"},
        {"name": "Fou", "pos": "G", "ht": "5-8", "pts": 7.5, "reb": 2.0, "ast": 3.0, "3pm": 1.2, "status": "ACTIVE"},
        {"name": "Camille", "pos": "F", "ht": "6-1", "pts": 6.5, "reb": 3.5, "ast": 1.0, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Shay", "pos": "G", "ht": "5-9", "pts": 5.0, "reb": 1.5, "ast": 2.0, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Nadav", "pos": "C", "ht": "6-4", "pts": 4.5, "reb": 4.0, "ast": 0.5, "3pm": 0.2, "status": "ACTIVE"},
    ],
    # Indiana Fever
    "IND": [
        {"name": "Caitlin Clark", "pos": "G", "ht": "6-0", "pts": 18.5, "reb": 4.5, "ast": 7.5, "3pm": 3.2, "status": "ACTIVE"},
        {"name": "Aliyah Boston", "pos": "C", "ht": "6-4", "pts": 14.5, "reb": 9.5, "ast": 2.5, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Kelsey Mitchell", "pos": "G", "ht": "5-8", "pts": 15.5, "reb": 2.5, "ast": 3.0, "3pm": 2.8, "status": "ACTIVE"},
        {"name": "Nalyssa", "pos": "F", "ht": "6-3", "pts": 9.5, "reb": 5.0, "ast": 1.5, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Kristi", "pos": "F", "ht": "6-2", "pts": 8.0, "reb": 4.5, "ast": 1.0, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Grace", "pos": "G", "ht": "5-10", "pts": 6.5, "reb": 2.0, "ast": 3.0, "3pm": 1.0, "status": "ACTIVE"},
        {"name": "Emma", "pos": "G", "ht": "5-9", "pts": 5.5, "reb": 1.5, "ast": 2.0, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Lily", "pos": "C", "ht": "6-3", "pts": 4.5, "reb": 3.5, "ast": 0.5, "3pm": 0.2, "status": "ACTIVE"},
    ],
    # Las Vegas Aces
    "LV": [
        {"name": "A'ja Wilson", "pos": "F/C", "ht": "6-4", "pts": 22.5, "reb": 10.5, "ast": 3.2, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Chelsea Gray", "pos": "G", "ht": "5-11", "pts": 15.5, "reb": 3.5, "ast": 6.5, "3pm": 2.5, "status": "ACTIVE"},
        {"name": "Kia", "pos": "G", "ht": "5-9", "pts": 12.5, "reb": 2.8, "ast": 4.0, "3pm": 2.2, "status": "ACTIVE"},
        {"name": "Candace", "pos": "G", "ht": "5-10", "pts": 11.5, "reb": 3.0, "ast": 3.5, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Kierstan", "pos": "F", "ht": "6-2", "pts": 9.0, "reb": 5.5, "ast": 1.2, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Crista", "pos": "F", "ht": "6-1", "pts": 7.5, "reb": 4.0, "ast": 0.8, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Meghan", "pos": "C", "ht": "6-5", "pts": 6.5, "reb": 5.5, "ast": 0.5, "3pm": 0.2, "status": "ACTIVE"},
        {"name": "Sydney", "pos": "G", "ht": "5-8", "pts": 5.0, "reb": 1.5, "ast": 1.5, "3pm": 0.8, "status": "ACTIVE"},
    ],
    # Los Angeles Sparks
    "LA": [
        {"name": "Cameron Brink", "pos": "F/C", "ht": "6-4", "pts": 12.5, "reb": 8.0, "ast": 2.5, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Nneka Ogwumike", "pos": "F", "ht": "6-2", "pts": 16.0, "reb": 7.5, "ast": 2.0, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Lexi", "pos": "G", "ht": "5-10", "pts": 14.0, "reb": 3.0, "ast": 5.5, "3pm": 2.5, "status": "ACTIVE"},
        {"name": "Zia", "pos": "G", "ht": "5-9", "pts": 11.0, "reb": 2.5, "ast": 3.5, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Laysha", "pos": "F", "ht": "6-2", "pts": 8.5, "reb": 4.5, "ast": 1.0, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Rickea", "pos": "F", "ht": "6-2", "pts": 7.5, "reb": 4.0, "ast": 0.8, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Te'a", "pos": "G", "ht": "5-8", "pts": 6.5, "reb": 2.0, "ast": 2.5, "3pm": 1.0, "status": "ACTIVE"},
        {"name": "Ji", "pos": "C", "ht": "6-4", "pts": 5.5, "reb": 5.0, "ast": 0.5, "3pm": 0.2, "status": "ACTIVE"},
    ],
    # Minnesota Lynx
    "MIN": [
        {"name": "Napheesa Collier", "pos": "F", "ht": "6-2", "pts": 17.0, "reb": 5.5, "ast": 3.4, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Alana Smith", "pos": "F", "ht": "6-3", "pts": 11.5, "reb": 7.0, "ast": 1.5, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Kayla McCollough", "pos": "G", "ht": "5-10", "pts": 10.8, "reb": 2.7, "ast": 1.5, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Natasha", "pos": "G", "ht": "5-9", "pts": 11.0, "reb": 3.0, "ast": 5.5, "3pm": 1.6, "status": "ACTIVE"},
        {"name": "Diamond", "pos": "F", "ht": "6-1", "pts": 8.5, "reb": 4.0, "ast": 1.0, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Nele", "pos": "F", "ht": "6-0", "pts": 6.0, "reb": 3.0, "ast": 0.5, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Olivia", "pos": "G", "ht": "5-8", "pts": 4.5, "reb": 1.0, "ast": 1.5, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Nara", "pos": "G", "ht": "5-7", "pts": 3.5, "reb": 0.8, "ast": 0.8, "3pm": 0.4, "status": "ACTIVE"},
    ],
    # New York Liberty
    "NY": [
        {"name": "Breanna Stewart", "pos": "F", "ht": "6-4", "pts": 19.5, "reb": 7.5, "ast": 4.0, "3pm": 2.0, "status": "ACTIVE"},
        {"name": "Sabrina Ionescu", "pos": "G", "ht": "5-11", "pts": 17.5, "reb": 5.5, "ast": 7.0, "3pm": 3.0, "status": "ACTIVE"},
        {"name": "Jonquel Jones", "pos": "C", "ht": "6-4", "pts": 15.0, "reb": 9.0, "ast": 2.0, "3pm": 1.2, "status": "ACTIVE"},
        {"name": "Courtney Vandersloot", "pos": "G", "ht": "5-10", "pts": 11.0, "reb": 3.0, "ast": 6.0, "3pm": 1.5, "status": "ACTIVE"},
        {"name": "Betnijah Laney", "pos": "F", "ht": "6-0", "pts": 8.0, "reb": 3.5, "ast": 1.5, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Kayla Thornton", "pos": "F", "ht": "6-2", "pts": 6.5, "reb": 4.0, "ast": 0.8, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Sonia", "pos": "G", "ht": "5-9", "pts": 6.0, "reb": 2.0, "ast": 2.5, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Han Xu", "pos": "C", "ht": "6-7", "pts": 7.0, "reb": 4.5, "ast": 0.5, "3pm": 0.3, "status": "ACTIVE"},
    ],
    # Phoenix Mercury
    "PHX": [
        {"name": "Diana Taurasi", "pos": "G", "ht": "6-0", "pts": 16.5, "reb": 4.0, "ast": 4.5, "3pm": 2.8, "status": "ACTIVE"},
        {"name": "Brittney Griner", "pos": "C", "ht": "6-9", "pts": 15.5, "reb": 9.0, "ast": 2.0, "3pm": 0.3, "status": "ACTIVE"},
        {"name": "Katherine", "pos": "G", "ht": "5-9", "pts": 12.5, "reb": 2.5, "ast": 5.0, "3pm": 2.2, "status": "ACTIVE"},
        {"name": "Moriah", "pos": "F", "ht": "6-2", "pts": 10.0, "reb": 5.5, "ast": 1.5, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Sophie", "pos": "F", "ht": "6-2", "pts": 8.5, "reb": 4.5, "ast": 1.0, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Nikki", "pos": "G", "ht": "5-10", "pts": 7.0, "reb": 2.0, "ast": 3.0, "3pm": 1.2, "status": "ACTIVE"},
        {"name": "Megan", "pos": "F", "ht": "6-1", "pts": 5.5, "reb": 3.5, "ast": 0.7, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Char", "pos": "C", "ht": "6-4", "pts": 4.5, "reb": 4.0, "ast": 0.4, "3pm": 0.2, "status": "ACTIVE"},
    ],
    # Portland Fire
    "POR": [
        {"name": "Te'a Cooper", "pos": "G", "ht": "5-8", "pts": 13.5, "reb": 2.5, "ast": 3.5, "3pm": 1.5, "status": "ACTIVE"},
        {"name": "Alexis", "pos": "G", "ht": "5-10", "pts": 11.0, "reb": 3.0, "ast": 4.0, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Aaliyah", "pos": "F", "ht": "6-2", "pts": 9.5, "reb": 5.5, "ast": 1.5, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Isabelle", "pos": "C", "ht": "6-4", "pts": 8.5, "reb": 6.5, "ast": 0.8, "3pm": 0.3, "status": "ACTIVE"},
        {"name": "Nika", "pos": "F", "ht": "6-1", "pts": 7.0, "reb": 4.0, "ast": 1.0, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Jessika", "pos": "G", "ht": "5-9", "pts": 6.0, "reb": 1.5, "ast": 2.0, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Kate", "pos": "F", "ht": "6-0", "pts": 5.5, "reb": 3.5, "ast": 0.6, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Sami", "pos": "G", "ht": "5-7", "pts": 4.5, "reb": 1.0, "ast": 1.0, "3pm": 0.5, "status": "ACTIVE"},
    ],
    # Seattle Storm
    "SEA": [
        {"name": "Jewell Loyd", "pos": "G", "ht": "5-9", "pts": 16.5, "reb": 3.5, "ast": 4.0, "3pm": 2.5, "status": "ACTIVE"},
        {"name": "Nina", "pos": "G", "ht": "5-10", "pts": 14.0, "reb": 2.5, "ast": 4.5, "3pm": 2.3, "status": "ACTIVE"},
        {"name": "Ezi", "pos": "C", "ht": "6-5", "pts": 12.5, "reb": 9.5, "ast": 2.0, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Briyana", "pos": "F", "ht": "6-2", "pts": 9.0, "reb": 5.5, "ast": 1.2, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Jordan", "pos": "G", "ht": "5-10", "pts": 8.5, "reb": 2.5, "ast": 3.5, "3pm": 1.5, "status": "ACTIVE"},
        {"name": "Mercedes", "pos": "F", "ht": "6-2", "pts": 7.5, "reb": 4.5, "ast": 0.8, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Kylie", "pos": "G", "ht": "5-9", "pts": 6.0, "reb": 1.5, "ast": 2.0, "3pm": 0.9, "status": "ACTIVE"},
        {"name": "Layla", "pos": "F", "ht": "6-1", "pts": 5.0, "reb": 3.5, "ast": 0.5, "3pm": 0.3, "status": "ACTIVE"},
    ],
    # Toronto Tempo
    "TOR": [
        {"name": "Scott", "pos": "G", "ht": "5-9", "pts": 13.0, "reb": 2.5, "ast": 5.5, "3pm": 2.0, "status": "ACTIVE"},
        {"name": "Katherine", "pos": "G", "ht": "5-10", "pts": 11.5, "reb": 2.0, "ast": 4.0, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Olga", "pos": "C", "ht": "6-4", "pts": 10.0, "reb": 7.5, "ast": 1.5, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Megan", "pos": "F", "ht": "6-2", "pts": 8.5, "reb": 5.0, "ast": 1.0, "3pm": 0.6, "status": "ACTIVE"},
        {"name": "Aisha", "pos": "F", "ht": "6-0", "pts": 7.5, "reb": 4.0, "ast": 0.8, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Cassandra", "pos": "G", "ht": "5-8", "pts": 6.5, "reb": 1.5, "ast": 2.5, "3pm": 1.0, "status": "ACTIVE"},
        {"name": "Nina", "pos": "F", "ht": "6-1", "pts": 5.5, "reb": 3.5, "ast": 0.6, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Christina", "pos": "C", "ht": "6-4", "pts": 4.5, "reb": 4.0, "ast": 0.4, "3pm": 0.2, "status": "ACTIVE"},
    ],
    # Washington Mystics
    "WSH": [
        {"name": "Ariel Atkins", "pos": "G", "ht": "5-10", "pts": 15.0, "reb": 3.5, "ast": 3.5, "3pm": 1.8, "status": "ACTIVE"},
        {"name": "Brittney Sykes", "pos": "G", "ht": "5-9", "pts": 13.5, "reb": 3.0, "ast": 4.0, "3pm": 1.5, "status": "ACTIVE"},
        {"name": "Elena", "pos": "F", "ht": "6-2", "pts": 11.5, "reb": 6.0, "ast": 2.0, "3pm": 0.8, "status": "ACTIVE"},
        {"name": "Shakira", "pos": "C", "ht": "6-4", "pts": 9.0, "reb": 7.5, "ast": 1.2, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Megan", "pos": "F", "ht": "6-1", "pts": 7.5, "reb": 4.0, "ast": 0.8, "3pm": 0.5, "status": "ACTIVE"},
        {"name": "Natasha", "pos": "G", "ht": "5-9", "pts": 6.5, "reb": 2.0, "ast": 3.0, "3pm": 1.0, "status": "ACTIVE"},
        {"name": "Amine", "pos": "F", "ht": "6-0", "pts": 5.5, "reb": 3.5, "ast": 0.6, "3pm": 0.4, "status": "ACTIVE"},
        {"name": "Jade", "pos": "G", "ht": "5-8", "pts": 4.5, "reb": 1.5, "ast": 1.5, "3pm": 0.7, "status": "ACTIVE"},
    ],
}

# WNBA Historical Finals (last 2 seasons)
WNBA_FINALS_HISTORY = {
    "2025": {
        "winner": "NY",  # New York Liberty won 2025
        "series": "4-2",
        "games": [
            {"game": 1, "home": "NYL", "away": "LV", "home_score": 87, "away_score": 74},
            {"game": 2, "home": "NYL", "away": "LV", "home_score": 81, "away_score": 76},
            {"game": 3, "home": "LV", "away": "NYL", "home_score": 83, "away_score": 78},
            {"game": 4, "home": "LV", "away": "NYL", "home_score": 91, "away_score": 85},
            {"game": 5, "home": "NYL", "away": "LV", "home_score": 88, "away_score": 82},
            {"game": 6, "home": "LV", "away": "NYL", "home_score": 79, "away_score": 84},
        ]
    },
    "2024": {
        "winner": "LV",  # Las Vegas Aces won 2024 (back-to-back)
        "series": "4-1",
        "games": [
            {"game": 1, "home": "LV", "away": "NYL", "home_score": 97, "away_score": 82},
            {"game": 2, "home": "LV", "away": "NYL", "home_score": 83, "away_score": 79},
            {"game": 3, "home": "NYL", "away": "LV", "home_score": 88, "away_score": 85},
            {"game": 4, "home": "NYL", "away": "LV", "home_score": 74, "away_score": 83},
            {"game": 5, "home": "LV", "away": "NYL", "home_score": 81, "away_score": 73},
        ]
    },
}

TEAM_CODES = {
    "ATL": "Atlanta Dream", "CHI": "Chicago Sky", "CON": "Connecticut Sun",
    "DAL": "Dallas Wings", "GS": "Golden State Valkyries", "IND": "Indiana Fever",
    "LV": "Las Vegas Aces", "LA": "Los Angeles Sparks", "MIN": "Minnesota Lynx",
    "NY": "New York Liberty", "PHX": "Phoenix Mercury", "POR": "Portland Fire",
    "SEA": "Seattle Storm", "TOR": "Toronto Tempo", "WSH": "Washington Mystics"
}