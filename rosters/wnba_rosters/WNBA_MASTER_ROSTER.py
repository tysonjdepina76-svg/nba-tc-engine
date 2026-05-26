"""
WNBA Master Roster — Live Scrape May 22, 2026
Source: wnba.com team roster pages
"""

from dataclasses import dataclass


@dataclass
class Player:
    name: str
    pos: str
    ht: str
    ppg: float
    rpg: float
    apg: float
    tpm: float
    status: str = "ACTIVE"


# All players keyed by team code
ROSTER = {
    "ATL": [
        Player("Naz Hillmon", "F", "6-2", 7.3, 5.0, 1.0, 0.7),
        Player("Amy Okonkwo", "F", "6-2", 0.0, 0.0, 0.0, 0.0),
        Player("Te-Hina Paopao", "G", "5-9", 9.0, 3.3, 2.3, 0.9),
        Player("Jordin Canada", "G", "5-6", 14.0, 4.0, 5.3, 1.4),
        Player("Angel Reese", "F", "6-4", 10.7, 12.7, 2.3, 1.1),
        Player("Rhyne Howard", "G", "6-2", 14.5, 4.5, 4.5, 1.5),
        Player("Madina Okot", "C", "6-6", 7.3, 6.7, 0.3, 0.7),
        Player("Allisha Gray", "G", "6-0", 25.0, 7.0, 1.3, 2.5),
        Player("Isobel Borlase", "G", "5-11", 1.0, 0.3, 0.0, 0.1),
        Player("Indya Nivar", "G", "5-10", 0.0, 3.5, 1.5, 0.0),
        Player("Sika Kone", "F", "6-3", 0.0, 0.7, 0.0, 0.0),
        Player("Aaliyah Nye", "G-F", "6-0", 0.0, 0.0, 0.0, 0.0),
        Player("Brionna Jones", "F", "6-3", 0.0, 0.0, 0.0, 0.0),
    ],

    "CHI": [
        Player("Jacy Sheldon", "G", "5-10", 9.0, 2.4, 2.8, 0.9),
        Player("Elizabeth Williams", "C-F", "6-3", 4.0, 4.4, 0.8, 0.4),
        Player("Skylar Diggins", "G", "5-9", 12.8, 4.8, 5.3, 1.3),
        Player("Rickea Jackson", "F", "6-2", 18.0, 4.8, 2.0, 1.8),
        Player("DiJonai Carrington", "G-F", "5-11", 0.0, 0.0, 0.0, 0.0),
        Player("Natasha Cloud", "G", "5-10", 11.5, 5.3, 4.8, 1.2),
        Player("Kamilla Cardoso", "C", "6-7", 14.4, 10.4, 2.4, 1.4),
        Player("Gabriela Jaquez", "G", "6-0", 12.4, 5.6, 1.4, 1.2),
        Player("Sydney Taylor", "G", "5-9", 3.3, 0.3, 0.7, 0.3),
        Player("Maddy Westbeld", "F", "6-3", 0.0, 0.0, 0.0, 0.0),
        Player("Courtney Vandersloot", "G", "5-8", 0.0, 0.0, 0.0, 0.0),
        Player("Rachel Banham", "G", "5-10", 6.2, 0.2, 0.8, 0.6),
        Player("Azura Stevens", "F-C", "6-6", 0.0, 0.0, 0.0, 0.0),
        Player("Aicha Coulibaly", "G", "6-0", 4.0, 1.5, 0.8, 0.4),
    ],

    "CON": [
        Player("Diamond Miller", "F", "6-1", 8.2, 2.5, 0.7, 0.8),
        Player("Hailey Van Lith", "G", "5-9", 9.3, 1.0, 2.8, 0.9),
        Player("Ashlon Jackson", "G", "6-0", 4.0, 1.0, 1.0, 0.4),
        Player("Charlisse Leger-Walker", "G", "5-10", 8.0, 1.7, 2.3, 0.8),
        Player("Gianna Kneepkens", "G", "5-11", 3.5, 2.2, 0.5, 0.4),
        Player("Aaliyah Edwards", "F", "6-3", 10.0, 3.0, 1.0, 1.0),
        Player("Olivia Nelson-Ododa", "C", "6-5", 6.7, 3.0, 2.3, 0.7),
        Player("Raegan Beers", "F", "6-4", 5.6, 3.8, 0.8, 0.6),
        Player("Saniya Rivers", "G", "6-1", 6.7, 2.3, 4.8, 0.7),
        Player("Aneesah Morrow", "F", "6-1", 12.0, 9.7, 1.2, 1.2),
        Player("Kennedy Burke", "G-F", "6-1", 7.7, 4.2, 3.3, 0.8),
        Player("Nell Angloma", "F", "6-1", 7.7, 2.7, 0.3, 0.8),
        Player("Brittney Griner", "C", "6-9", 15.0, 5.7, 2.0, 1.5),
        Player("Leila Lacan", "G", "5-11", 0.0, 0.0, 0.0, 0.0),
    ],

    "DAL": [
        Player("Odyssey Sims", "G", "5-8", 8.4, 0.8, 3.2, 0.8),
        Player("Paige Bueckers", "G", "6-0", 20.8, 2.8, 5.2, 2.1),
        Player("Costanza Verona", "G", "5-6", 0.0, 0.0, 0.0, 0.0),
        Player("Alysha Clark", "F", "5-11", 2.0, 1.5, 0.0, 0.2),
        Player("Alanna Smith", "F", "6-4", 4.8, 4.0, 2.2, 0.5),
        Player("Aziaha James", "G", "5-10", 6.4, 2.4, 0.4, 0.6),
        Player("JJ Quinerly", "G", "5-8", 0.0, 0.0, 0.0, 0.0),
        Player("Dulcy Fankam Mendjiadeu", "F-C", "6-3", 0.0, 0.0, 0.0, 0.0),
        Player("Maddy Siegrist", "F", "6-2", 7.2, 2.2, 0.8, 0.7),
        Player("Arike Ogunbowale", "G", "5-8", 17.4, 2.2, 3.0, 1.7),
        Player("Li Yueru", "C", "6-7", 3.7, 4.3, 1.0, 0.4),
        Player("Jessica Shepard", "F", "6-4", 12.4, 9.8, 6.8, 1.2),
        Player("Awak Kuier", "F", "6-6", 3.0, 2.0, 1.2, 0.3),
        Player("Azzi Fudd", "G", "5-11", 8.8, 1.0, 1.0, 0.9),
    ],

    "GSV": [
        Player("Gabby Williams", "F", "5-11", 15.0, 4.5, 2.5, 1.5),
        Player("Kaitlyn Chen", "G", "5-9", 5.5, 2.5, 1.3, 0.6),
        Player("Laeticia Amihere", "F", "6-3", 6.0, 4.8, 1.8, 0.6),
        Player("Juste Jocyte", "G-F", "6-0", 0.0, 0.0, 0.0, 0.0),
        Player("Kayla Thornton", "F", "6-1", 10.8, 5.5, 0.5, 1.1),
        Player("Kaila Charles", "G-F", "6-1", 8.0, 6.5, 1.5, 0.8),
        Player("Miela Sowah", "G", "5-10", 0.0, 0.0, 0.0, 0.0),
        Player("Ashten Prechtel", "F", "6-5", 0.0, 0.0, 0.0, 0.0),
        Player("Iliana Rupert", "C", "6-4", 0.0, 0.0, 0.0, 0.0),
        Player("Janelle Salaun", "F", "6-2", 14.8, 3.0, 1.0, 1.5),
        Player("Tiffany Hayes", "G", "5-10", 5.0, 0.5, 1.5, 0.5),
        Player("Veronica Burton", "G", "5-9", 14.5, 3.0, 7.3, 1.5),
        Player("Cecilia Zandalasini", "F", "6-2", 8.0, 2.0, 1.0, 0.8),
        Player("Ndjakalenga Mwenentanda", "G", "6-2", 0.0, 0.0, 0.0, 0.0),
        Player("Kiah Stokes", "C", "6-3", 5.0, 5.3, 2.0, 0.5),
    ],

    "IND": [
        Player("Kelsey Mitchell", "G", "5-8", 23.0, 1.0, 2.0, 2.3),
        Player("Myisha Hines-Allen", "F", "6-2", 5.8, 3.8, 3.4, 0.6),
        Player("Raven Johnson", "G", "5-8", 2.6, 2.2, 1.2, 0.3),
        Player("Aliyah Boston", "C-F", "6-5", 15.0, 5.8, 2.3, 1.5),
        Player("Sophie Cunningham", "G", "6-1", 8.2, 3.4, 1.4, 0.8),
        Player("Lexie Hull", "G", "6-2", 7.0, 3.6, 0.8, 0.7),
        Player("Damiris Dantas", "C-F", "6-4", 4.0, 1.0, 0.3, 0.4),
        Player("Justine Pissott", "G-F", "6-4", 0.0, 0.0, 0.0, 0.0),
        Player("Makayla Timpson", "F-C", "6-2", 4.2, 3.0, 0.6, 0.4),
        Player("Caitlin Clark", "G", "6-0", 24.3, 5.0, 9.0, 2.4),
        Player("Bree Hall", "G", "6-1", 0.0, 0.0, 0.0, 0.0),
        Player("Monique Billings", "F", "6-4", 8.0, 6.5, 1.8, 0.8),
        Player("Tyasha Harris", "G", "5-10", 2.6, 1.2, 2.4, 0.3),
    ],

    "LVA": [
        Player("Jackie Young", "G", "6-0", 11.2, 5.0, 6.2, 1.1),
        Player("Kierstan Bell", "F", "6-1", 0.0, 2.3, 0.7, 0.0),
        Player("Janiah Barker", "F", "6-4", 0.0, 0.0, 0.0, 0.0),
        Player("NaLyssa Smith", "F", "6-4", 9.2, 5.4, 1.2, 0.9),
        Player("Stephanie Talbot", "F", "6-2", 3.0, 2.4, 1.4, 0.3),
        Player("Dana Evans", "G", "5-6", 0.0, 0.0, 0.0, 0.0),
        Player("Chelsea Gray", "G", "5-11", 12.0, 4.4, 6.6, 1.2),
        Player("Brianna Turner", "F-C", "6-3", 0.8, 3.0, 0.2, 0.1),
        Player("A'ja Wilson", "C", "6-4", 25.0, 5.6, 2.4, 2.5),
        Player("Chennedy Carter", "G", "5-9", 19.4, 2.8, 2.0, 1.9),
        Player("Jewell Loyd", "G", "5-11", 6.4, 3.2, 1.6, 0.6),
        Player("Cheyenne Parker-Tyus", "F", "6-4", 4.0, 2.4, 0.6, 0.4),
    ],

    "LAS": [
        Player("Ta'Niya Latson", "G", "5-8", 0.7, 0.3, 0.0, 0.1),
        Player("Chance Gray", "G", "5-9", 1.2, 0.8, 0.4, 0.1),
        Player("Laura Ziegler", "F", "6-2", 0.0, 0.0, 0.0, 0.0),
        Player("Dearica Hamby", "F", "6-3", 19.0, 8.8, 2.4, 1.9),
        Player("Jihyun Park", "G", "6-1", 1.3, 0.7, 1.0, 0.1),
        Player("Ariel Atkins", "G", "5-10", 7.0, 2.3, 2.3, 0.7),
        Player("Kelsey Plum", "G", "5-8", 24.6, 1.4, 5.8, 2.5),
        Player("Rae Burrell", "G-F", "6-2", 8.4, 2.6, 1.6, 0.8),
        Player("Erica Wheeler", "G", "5-7", 4.6, 1.4, 4.6, 0.5),
        Player("Sania Feagin", "F", "6-3", 0.0, 0.0, 0.0, 0.0),
        Player("Kate Martin", "G", "6-0", 3.7, 0.3, 0.0, 0.4),
        Player("Cameron Brink", "F", "6-4", 8.0, 3.6, 1.0, 0.8),
        Player("Nneka Ogwumike", "F", "6-2", 15.6, 6.6, 2.0, 1.6),
        Player("Emma Cannon", "F", "6-2", 3.0, 0.0, 0.0, 0.3),
    ],

    "MIN": [
        Player("Natasha Howard", "F", "6-2", 15.2, 7.2, 3.6, 1.5),
        Player("Liatu King", "F", "5-11", 9.0, 7.0, 0.0, 0.9),
        Player("Maya Caldwell", "G", "5-11", 5.4, 1.8, 1.6, 0.5),
        Player("Olivia Miles", "G", "5-10", 15.2, 4.2, 5.6, 1.5),
        Player("Anastasiia Olairi Kosu", "F", "6-1", 3.0, 1.4, 0.6, 0.3),
        Player("Antonia Delaere", "G", "5-11", 2.6, 0.4, 1.6, 0.3),
        Player("Courtney Williams", "G", "5-8", 15.6, 5.4, 4.0, 1.6),
        Player("Eliska Hamzova", "G", "6-0", 2.0, 2.3, 0.7, 0.2),
        Player("Nia Coffey", "F", "6-1", 7.8, 5.4, 1.2, 0.8),
        Player("Dorka Juhasz", "F", "6-5", 0.0, 0.0, 0.0, 0.0),
        Player("Kayla McBride", "G", "5-11", 15.6, 4.6, 1.8, 1.6),
        Player("Emma Cechova", "C", "6-4", 8.3, 3.7, 0.0, 0.8),
        Player("Napheesa Collier", "F", "6-1", 0.0, 0.0, 0.0, 0.0),
        Player("Emese Hof", "C", "6-3", 2.5, 1.5, 1.0, 0.2),
    ],

    "NYL": [
        Player("Satou Sabally", "F", "6-4", 5.0, 4.0, 2.0, 0.5),
        Player("Marine Fauthoux", "G", "5-9", 0.0, 0.0, 0.0, 0.0),
        Player("Rebekah Gardner", "G", "6-1", 10.4, 3.2, 2.2, 1.0),
        Player("Rebecca Allen", "F-G", "6-2", 4.0, 2.0, 1.5, 0.4),
        Player("Alex Fowler", "F", "6-2", 6.0, 0.0, 0.5, 0.6),
        Player("Leonie Fiebich", "F", "6-4", 0.0, 0.0, 0.0, 0.0),
        Player("Raquel Carrera", "C", "6-3", 0.0, 0.0, 0.0, 0.0),
        Player("Pauline Astier", "G", "5-11", 14.8, 4.0, 3.6, 1.5),
        Player("Sabrina Ionescu", "G", "5-11", 0.0, 0.0, 0.0, 0.0),
        Player("Han Xu", "C", "6-11", 4.0, 1.8, 0.6, 0.4),
        Player("Marine Johannes", "G", "5-10", 12.6, 3.2, 4.2, 1.3),
        Player("Breanna Stewart", "F", "6-4", 22.0, 9.0, 2.6, 2.2),
        Player("Jonquel Jones", "C", "6-6", 12.4, 7.4, 2.4, 1.2),
        Player("Betnijah Laney-Hamilton", "G-F", "6-0", 8.3, 2.3, 2.3, 0.8),
        Player("Julie Vanloo", "G", "5-8", 5.8, 2.0, 5.4, 0.6),
    ],

    "PHX": [
        Player("Noemie Brochant", "F-G", "5-11", 4.0, 2.2, 0.3, 0.4),
        Player("Kahleah Copper", "G-F", "6-1", 18.5, 2.5, 2.5, 1.9),
        Player("Natasha Mack", "F-C", "6-3", 10.3, 8.7, 1.7, 1.0),
        Player("Shay Ciezki", "G", "5-7", 0.0, 0.0, 0.0, 0.0),
        Player("Monique Akoa Makani", "G", "5-10", 0.0, 0.0, 0.0, 0.0),
        Player("Valeriane Ayayi", "F", "6-1", 4.3, 2.8, 1.3, 0.4),
        Player("Quionche Carter", "F", "5-11", 0.7, 0.7, 0.3, 0.1),
        Player("Kiana Williams", "G", "5-8", 5.3, 0.3, 0.5, 0.5),
        Player("DeWanna Bonner", "F-G", "6-4", 10.7, 6.3, 1.5, 1.1),
        Player("Alyssa Thomas", "F", "6-2", 17.7, 7.2, 8.2, 1.8),
        Player("Jovana Nogic", "G", "6-0", 15.3, 1.2, 2.2, 1.5),
        Player("Kyara Linskens", "C", "6-4", 2.8, 2.2, 0.6, 0.3),
        Player("Sami Whitcomb", "G", "5-10", 0.0, 0.0, 0.0, 0.0),
        Player("Marta Suarez", "F", "6-3", 6.0, 1.0, 0.0, 0.6),
    ],

    "POR": [
        Player("Carla Leite", "G", "5-9", 15.0, 2.7, 3.3, 1.5),
        Player("Jordan Harrison", "G", "5-6", 4.0, 0.0, 4.0, 0.4),
        Player("Sarah Ashlee Barker", "G", "6-0", 10.0, 3.8, 1.8, 1.0),
        Player("Bridget Carleton", "F", "6-2", 16.8, 3.0, 1.8, 1.7),
        Player("Holly Winterburn", "G", "5-11", 3.0, 1.5, 2.5, 0.3),
        Player("Teja Oblak", "G", "5-8", 0.0, 0.0, 0.0, 0.0),
        Player("Nyadiew Puoch", "F", "6-3", 5.6, 2.2, 0.8, 0.6),
        Player("Luisa Geiselsoder", "C", "6-4", 6.6, 4.0, 2.2, 0.7),
        Player("Megan Gustafson", "C", "6-4", 7.4, 2.6, 0.4, 0.7),
        Player("Frieda Buhner", "F-C", "6-2", 2.0, 1.7, 0.0, 0.2),
        Player("Emily Engstler", "F", "6-1", 8.2, 2.8, 1.0, 0.8),
        Player("Serah Williams", "F", "6-4", 2.5, 2.8, 0.5, 0.2),
        Player("Karlie Samuelson", "G", "6-0", 0.0, 0.0, 0.0, 0.0),
    ],

    "SEA": [
        Player("Natisha Hiedeman", "G", "5-8", 12.2, 2.0, 3.6, 1.2),
        Player("Flau'jae Johnson", "G", "5-10", 10.8, 4.6, 1.0, 1.1),
        Player("Taylor Thierry", "G-F", "6-1", 6.0, 2.0, 0.0, 0.6),
        Player("Jade Melbourne", "G", "5-10", 13.0, 1.4, 4.2, 1.3),
        Player("Zia Cooke", "G", "5-9", 9.8, 3.2, 1.8, 1.0),
        Player("Lexie Brown", "G", "5-9", 5.0, 2.2, 1.4, 0.5),
        Player("Awa Fam", "C", "6-4", 0.0, 0.0, 0.0, 0.0),
        Player("Ezi Magbegor", "F-C", "6-6", 0.0, 0.0, 0.0, 0.0),
        Player("Dominique Malonga", "C", "6-6", 16.0, 7.3, 0.3, 1.6),
        Player("Taina Mair", "G", "5-9", 0.0, 0.0, 1.0, 0.0),
        Player("Jordan Horston", "F", "6-2", 1.4, 2.8, 1.0, 0.1),
        Player("Stefanie Dolson", "C", "6-5", 7.4, 4.0, 1.4, 0.7),
        Player("Katie Lou Samuelson", "G", "6-3", 0.0, 0.0, 0.0, 0.0),
        Player("Mackenzie Holmes", "F", "6-3", 5.8, 4.0, 0.6, 0.6),
    ],

    "TOR": [
        Player("Kiki Rice", "G", "5-11", 11.3, 3.8, 2.2, 1.1),
        Player("Laura Juskaite", "F", "6-4", 7.8, 3.8, 1.2, 0.8),
        Player("Marina Mabrey", "G", "6-1", 17.8, 3.8, 2.2, 1.8),
        Player("Teonni Key", "F", "6-4", 3.3, 3.0, 0.3, 0.3),
        Player("Nyara Sabally", "F", "6-5", 9.3, 6.0, 2.5, 0.9),
        Player("Maria Conde", "F", "6-3", 5.7, 3.3, 1.0, 0.6),
        Player("Kia Nurse", "G", "6-0", 6.5, 1.3, 0.8, 0.7),
        Player("Lexi Held", "G", "5-9", 1.0, 0.3, 0.7, 0.1),
        Player("Temi Fagbenle", "C", "6-5", 2.0, 1.0, 1.0, 0.2),
        Player("Brittney Sykes", "G", "5-11", 22.3, 4.3, 4.7, 2.2),
        Player("Isabelle Harrison", "F", "6-5", 0.0, 0.0, 0.0, 0.0),
        Player("Julie Allemand", "G", "5-10", 3.3, 2.3, 4.0, 0.3),
        Player("Nikolina Milic", "C", "6-3", 3.5, 1.0, 0.5, 0.4),
        Player("Mariella Fasoula", "C", "6-4", 2.0, 1.0, 0.5, 0.2),
    ],

    "WAS": [
        Player("Shakira Austin", "C", "6-5", 16.3, 8.5, 3.0, 1.6),
        Player("Alicia Florez Getino", "G", "5-9", 0.0, 0.0, 0.0, 0.0),
        Player("Rori Harmon", "G", "5-6", 1.5, 1.8, 2.3, 0.2),
        Player("Alex Wilson", "G", "5-9", 3.0, 1.8, 0.8, 0.3),
        Player("Darianna Littlepage-Buggs", "G-F", "6-1", 0.0, 0.0, 0.0, 0.0),
        Player("Georgia Amoore", "G", "5-6", 5.8, 1.3, 4.3, 0.6),
        Player("Michaela Onyenwere", "F", "6-0", 0.0, 0.0, 0.0, 0.0),
        Player("Cassandre Prosper", "G", "6-3", 4.5, 2.0, 1.3, 0.5),
        Player("Sonia Citron", "G", "6-1", 20.0, 3.5, 1.8, 2.0),
        Player("Cotie McMahon", "G", "6-0", 10.0, 3.0, 1.5, 1.0),
        Player("Angela Dugalic", "F", "6-4", 2.3, 2.5, 0.3, 0.2),
        Player("Lucy Olsen", "G", "5-10", 4.3, 0.0, 1.3, 0.4),
        Player("Kiki Iriafen", "F", "6-3", 16.5, 12.8, 2.3, 1.7),
        Player("Lauren Betts", "C", "6-7", 5.5, 3.0, 0.5, 0.6),
    ],

}

# Total: 207 players across 15 teams