"""
WNBA Master Roster — All 14 Teams
Updated: 2026-05-21
Source: Live ESPN scrape > SportBusy stats > Manual boxscore
"""
from dataclasses import dataclass

@dataclass
class Player:
    name: str; pos: str; ht: str
    ppg: float; rpg: float; apg: float; tpm: float
    status: str = "ACTIVE"; injury: str = ""

# ATL — Atlanta Dream
STARTERS_ATL = [
    Player("Allisha Gray","G","6\'0\"",8.3,2.3,0.4,0.0),
    Player("Rhyne Howard","G","6\'0\"",7.3,2.3,2.3,0.0),
    Player("Jordin Canada","G","6\'0\"",4.7,1.3,1.8,0.0),
    Player("Angel Reese","F","6\'0\"",3.6,4.2,0.8,0.0),
    Player("Te-Hina Paopao","G","6\'0\"",3.0,1.1,0.8,0.0),
]
BENCH_ATL = [
    Player("Naz Hillmon","F","6\'0\"",2.4,1.7,0.3,0.0),
    Player("Madina Okot","C","6\'0\"",2.4,2.2,0.1,0.0),
    Player("Isobel Borlase","G","6\'0\"",0.3,0.1,0.0,0.0),
    Player("Aaliyah Nye","G","6\'0\"",0.0,0.0,0.0,0.0),
    Player("Sika Kone","F","6\'0\"",0.0,0.2,0.0,0.0),
    Player("Indya Nivar","G","6\'0\"",0.0,1.8,0.8,0.0),
]

# CHI — Chicago Sky
STARTERS_CHI = [
    Player("Skylar Diggins","G","5\'9\"",16.3,2.9,5.3,1.3),
    Player("Rickea Jackson","F","6\'2\"",14.2,3.6,1.6,1.4),
    Player("Gabriela Jaquez","G","6\'0\"",12.5,5.8,1.3,0.8),
    Player("Kamilla Cardoso","C","6\'7\"",11.9,8.4,2.1,0.0),
    Player("Azura Stevens","F","6\'6\"",10.1,5.6,1.3,1.1),
]
BENCH_CHI = [
    Player("Courtney Vandersloot","G","5\'8\"",10.0,3.2,6.6,0.9),
    Player("Natasha Cloud","G","5\'10\"",8.8,3.3,5.3,1.0),
    Player("Elizabeth Williams","C","6\'3\"",8.6,5.8,1.4,0.0),
    Player("DiJonai Carrington","G","5\'11\"",8.5,3.5,1.2,0.6),
    Player("Jacy Sheldon","G","5\'10\"",6.5,2.0,2.3,1.0),
    Player("Rachel Banham","G","5\'10\"",5.8,1.2,1.6,1.2),
    Player("Aicha Coulibaly","G","6\'0\"",5.3,1.3,0.7,0.0),
    Player("Maddy Westbeld","F","6\'3\"",4.1,2.4,0.9,0.7),
    Player("Sydney Taylor","G","5\'9\"",3.3,0.3,0.7,0.3),
]

# CON — Connecticut Sun
STARTERS_CON = [
    Player("Brittney Griner","C","6\'9\"",16.8,7.1,1.8,0.1),
    Player("Leila Lacan","G","5\'11\"",10.4,2.4,3.7,0.6),
    Player("Saniya Rivers","G","6\'1\"",8.7,2.7,3.0,1.0),
    Player("Aneesah Morrow","F","6\'1\"",8.3,7.3,0.6,0.5),
    Player("Diamond Miller","F","6\'3\"",6.7,2.2,1.3,0.6),
]
BENCH_CON = [
    Player("Aaliyah Edwards","F","6\'3\"",6.5,4.6,0.9,0.0),
    Player("Charlisse Leger-Walker","G","5\'10\"",6.4,1.6,2.2,0.8),
    Player("Kennedy Burke","G","6\'1\"",5.3,1.8,0.9,0.6),
    Player("Olivia Nelson-Ododa","C","6\'5\"",5.1,3.6,0.6,0.0),
    Player("Hailey Van Lith","G","5\'9\"",4.6,1.1,1.8,0.4),
    Player("Raegan Beers","F","6\'4\"",4.5,2.8,0.5,0.0),
    Player("Nell Angloma","F","6\'1\"",4.0,0.5,0.5,0.0),
    Player("Gianna Kneepkens","G","5\'11\"",3.8,2.4,0.6,0.4),
    Player("Ashlon Jackson","G","6\'0\"",0.0,0.0,0.0,0.0),
]

# DAL — Dallas Wings
STARTERS_DAL = [
    Player("Arike Ogunbowale","G","5\'8\"",19.9,3.2,3.9,2.4),
    Player("Paige Bueckers","G","6\'0\"",19.3,3.8,5.4,1.2),
    Player("Odyssey Sims","G","5\'8\"",11.1,2.4,3.8,0.7),
    Player("Maddy Siegrist","F","6\'2\"",8.0,2.8,0.6,0.5),
    Player("Azzi Fudd","G","5\'11\"",7.7,1.3,1.0,0.3),
]
BENCH_DAL = [
    Player("Aziaha James","G","5\'10\"",7.5,2.8,1.5,0.9),
    Player("Alanna Smith","F","6\'4\"",7.3,4.5,2.0,0.8),
    Player("Jessica Shepard","F","6\'4\"",7.0,6.6,2.8,0.1),
    Player("Alysha Clark","F","5\'11\"",6.5,3.4,1.4,0.9),
    Player("JJ Quinerly","G","5\'8\"",6.5,1.9,2.3,0.6),
    Player("Li Yueru","C","6\'7\"",4.7,3.6,0.6,0.3),
    Player("Dulcy Fankam Mendjiadeu","F","6\'3\"",3.4,3.9,0.3,0.0),
    Player("Awak Kuier","F","6\'6\"",2.7,2.5,0.7,0.1),
    Player("Costanza Verona","G","5\'7\"",0.0,0.0,0.0,0.0),
]

# GS — Golden State Valkyries
STARTERS_GS = [
    Player("Cecilia Zandalasini","F","6\'0\"",8.0,2.0,1.0,0.0),
    Player("Janelle Salaun","F","6\'0\"",5.2,0.7,0.3,0.0),
    Player("Veronica Burton","G","6\'0\"",5.0,0.9,2.4,0.0),
    Player("Gabby Williams","F","6\'0\"",4.9,1.8,0.9,0.0),
    Player("Kayla Thornton","F","6\'0\"",3.6,1.9,0.1,0.0),
]
BENCH_GS = [
    Player("Kaitlyn Chen","G","6\'0\"",2.2,1.1,0.4,0.0),
    Player("Kaila Charles","G","6\'0\"",2.1,2.1,0.6,0.0),
    Player("Laeticia Amihere","F","6\'0\"",2.1,1.2,0.8,0.0),
    Player("Kiah Stokes","C","6\'0\"",1.6,2.0,0.6,0.0),
    Player("Tiffany Hayes","G","6\'0\"",1.0,0.0,1.0,0.0),
    Player("Miela Sowah","G","6\'0\"",0.0,0.0,0.0,0.0),
    Player("Ndjakalenga Mwenentanda","G","6\'0\"",0.0,0.0,0.0,0.0),
]

# IND — Indiana Fever
STARTERS_IND = [
    Player("Caitlin Clark","G","6\'0\"",18.9,5.5,8.6,2.9),
    Player("Kelsey Mitchell","G","5\'8\"",17.5,2.0,2.9,2.4),
    Player("Shakira Austin","C","6-5",14.5,8.0,3.0,0.5),
    Player("Aliyah Boston","C","6\'5\"",14.4,8.4,3.0,0.1),
    Player("Cotie McMahon","G","6-1",13.0,5.0,2.0,1.0),
]
BENCH_IND = [
    Player("NaLyssa Smith","F","6-2",11.0,6.5,2.0,0.5),
    Player("Erica Wheeler","G","5-6",10.0,2.5,5.5,1.5),
    Player("Kristine Anigwe","C","6-4",8.5,6.0,1.0,0.0),
    Player("Lexie Hull","G","5-11",8.0,3.5,3.0,1.2),
    Player("Sophie Cunningham","G","6\'1\"",7.9,2.8,1.4,1.4),
    Player("Myisha Hines-Allen","F","6\'2\"",7.8,5.0,2.1,0.5),
    Player("Damiris Dantas","C","6\'4\"",6.9,3.8,1.4,0.8),
    Player("Kaitlyn Zaragoza","F","6-3",6.5,4.0,1.5,0.5),
    Player("Tyasha Harris","G","5\'10\"",6.4,1.3,2.5,0.9),
    Player("Monique Billings","F","6\'4\"",6.3,5.6,0.9,0.1),
    Player("Shatori Walker-Kimbrough","G","5\'9\"",5.6,1.5,1.2,0.6),
    Player("Makayla Timpson","F","6\'2\"",2.9,1.9,0.1,0.0),
    Player("Raven Johnson","G","5\'8\"",1.0,2.0,1.3,0.0),
    Player("Bree Hall","G","6\'1\"",0.8,0.8,0.0,0.0),
    Player("Justine Pissott","G","6\'4\"",0.0,0.0,0.0,0.0),
]

# LAS — Los Angeles Sparks
STARTERS_LAS = [
    Player("Rickea Jackson","F","6-3",15.5,6.0,2.0,1.0),
    Player("Brittany Sykes","G","5-9",12.0,3.5,4.0,0.8),
    Player("Aerial Powers","F","6-1",10.5,4.5,2.0,0.8),
    Player("Erica Wheeler","G","5-6",10.0,2.5,7.0,1.5),
    Player("Layshia Clarendon","G","5-11",9.5,3.5,5.5,1.2),
]
BENCH_LAS = [
    Player("Elizabeth Williams","C","6-5",9.0,5.5,2.0,0.5),
    Player("Kelsey Plum","G","6\'0\"",6.7,0.4,1.4,0.0),
    Player("Jazmine Montaque","G","5-10",6.5,2.5,3.0,0.7),
    Player("Dearica Hamby","F","6\'0\"",4.3,1.8,0.6,0.0),
    Player("Nneka Ogwumike","F","6\'0\"",4.1,1.7,0.5,0.0),
    Player("Emma Cannon","F","6\'0\"",3.0,0.0,0.0,0.0),
    Player("Kate Martin","G","6\'0\"",2.8,0.3,0.0,0.0),
    Player("Ariel Atkins","G","6\'0\"",2.5,1.5,1.3,0.0),
    Player("Rae Burrell","G","6\'0\"",1.9,0.8,0.4,0.0),
    Player("Cameron Brink","F","6\'0\"",1.8,0.8,0.3,0.0),
    Player("Jihyun Park","F","6\'0\"",0.5,0.3,0.5,0.0),
    Player("Chance Gray","G","6\'0\"",0.4,0.3,0.1,0.0),
    Player("Ta&#x27;Niya Latson","G","6\'0\"",0.2,0.1,0.0,0.0),
    Player("Sania Feagin","F","6\'0\"",0.0,0.0,0.0,0.0),
]

# LVA — Las Vegas Aces
STARTERS_LVA = [
    Player("A'ja Wilson","F","6-4",45.0,9.0,4.0,1.0),
    Player("Kelsey Plum","G","5-9",12.5,2.5,3.5,2.0),
    Player("Jackie Lou","F","6-2",10.5,5.5,1.5,0.8),
    Player("Kia Wilson","G","5-10",9.5,3.0,4.5,1.0),
    Player("Tiffany Hayes","G","5-10",9.5,3.0,3.5,0.9),
]
BENCH_LVA = [
    Player("Kenyon Carter Jr","F","6-2",8.5,4.0,2.5,0.5),
    Player("Sydny Weaver","C","6-5",7.5,5.0,1.0,0.0),
    Player("Rabiya Mateo","F","6-3",6.5,4.0,1.0,0.5),
    Player("Sydney Colson","G","5-8",5.5,2.0,3.0,0.6),
    Player("A&#x27;ja Wilson","C","6\'0\"",5.0,1.1,0.5,0.0),
    Player("Chennedy Carter","G","6\'0\"",3.9,0.6,0.4,0.0),
    Player("Chelsea Gray","G","6\'0\"",2.4,0.9,1.3,0.0),
    Player("Jackie Young","G","6\'0\"",2.2,1.0,1.2,0.0),
    Player("NaLyssa Smith","F","6\'0\"",1.8,1.1,0.2,0.0),
    Player("Jewell Loyd","G","6\'0\"",1.3,0.6,0.3,0.0),
    Player("Cheyenne Parker-Tyus","F","6\'0\"",0.8,0.5,0.1,0.0),
    Player("Stephanie Talbot","F","6\'0\"",0.6,0.5,0.3,0.0),
    Player("Brianna Turner","F","6\'0\"",0.2,0.6,0.0,0.0),
    Player("Kierstan Bell","F","6\'0\"",0.0,0.8,0.2,0.0),
]

# MIN — Minnesota Lynx
STARTERS_MIN = [
    Player("Kayla McBride","G","6\'0\"",4.1,1.2,0.5,0.0),
    Player("Natasha Howard","F","6\'0\"",4.0,1.9,0.9,0.0),
    Player("Courtney Williams","G","6\'0\"",4.0,1.2,1.1,0.0),
    Player("Olivia Miles","G","6\'0\"",3.9,1.1,1.4,0.0),
    Player("Emma Cechova","F","6\'0\"",2.8,1.2,0.0,0.0),
]
BENCH_MIN = [
    Player("Nia Coffey","F","6\'0\"",1.9,1.5,0.3,0.0),
    Player("Emese Hof","C","6\'0\"",1.3,0.8,0.5,0.0),
    Player("Maya Caldwell","G","6\'0\"",0.7,0.4,0.3,0.0),
    Player("Antonia Delaere","F","6\'0\"",0.6,0.1,0.3,0.0),
    Player("Anastasiia Olairi Kosu","F","6\'0\"",0.6,0.2,0.2,0.0),
    Player("Eliska Hamzova","G","6\'0\"",0.5,0.3,0.0,0.0),
]

# NY — New York Liberty
STARTERS_NY = [
    Player("Alex Fowler","F","6\'0\"",12.0,0.0,1.0,0.0),
    Player("Breanna Stewart","F","6\'0\"",5.8,2.3,0.7,0.0),
    Player("Pauline Astier","G","6\'0\"",4.2,0.9,1.0,0.0),
    Player("Marine Johannes","G","6\'0\"",4.0,0.8,1.3,0.0),
    Player("Rebecca Allen","G","6\'0\"",3.0,0.0,1.0,0.0),
]
BENCH_NY = [
    Player("Jonquel Jones","C","6\'0\"",2.9,1.8,0.6,0.0),
    Player("Rebekah Gardner","G","6\'0\"",2.5,0.9,0.7,0.0),
    Player("Betnijah Laney-Hamilton","G","6\'0\"",2.1,0.6,0.6,0.0),
    Player("Julie Vanloo","G","6\'0\"",1.7,0.5,1.2,0.0),
    Player("Han Xu","C","6\'0\"",0.9,0.6,0.2,0.0),
    Player("Aubrey Griffin","F","6\'0\"",0.1,0.1,0.0,0.0),
]

# PHX — Phoenix Mercury
STARTERS_PHX = [
    Player("Kahleah Copper","G","6\'0\"",3.6,0.4,0.5,0.0),
    Player("Alyssa Thomas","F","6\'0\"",3.3,1.4,1.7,0.0),
    Player("Jovana Nogic","G","6\'0\"",3.1,0.2,0.4,0.0),
    Player("DeWanna Bonner","F","6\'0\"",2.2,1.3,0.3,0.0),
    Player("Natasha Mack","F","6\'0\"",2.1,1.7,0.3,0.0),
]
BENCH_PHX = [
    Player("Valeriane Ayayi","F","6\'0\"",1.9,1.0,0.6,0.0),
    Player("Kiana Williams","G","6\'0\"",1.2,0.1,0.1,0.0),
    Player("Noemie Brochant","F","6\'0\"",1.0,0.4,0.0,0.0),
    Player("Kyara Linskens","C","6\'0\"",0.6,0.4,0.1,0.0),
    Player("Sha Carter","G","6\'0\"",0.5,0.5,0.3,0.0),
    Player("Anneli Maley","F","6\'0\"",0.3,0.5,0.0,0.0),
    Player("Peyton Williams","F","6\'0\"",0.0,0.0,2.0,0.0),
]

# POR — Portland Fire
STARTERS_POR = [
    Player("Carla Leite","G","5\'9\"",7.9,1.4,2.2,0.4),
    Player("Nyadiew Puoch","F","6\'3\"",7.0,2.5,1.0,0.8),
    Player("Luisa Geiselsoder","C","6\'4\"",6.9,4.8,1.7,1.1),
    Player("Sug Sutton","G","5\'8\"",6.1,1.7,3.5,0.7),
    Player("Bridget Carleton","F","6\'2\"",5.9,2.9,1.6,1.2),
]
BENCH_POR = [
    Player("Karlie Samuelson","G","6\'0\"",5.3,2.0,1.4,1.1),
    Player("Emily Engstler","F","6\'1\"",4.7,3.9,1.4,0.5),
    Player("Haley Jones","G","6\'1\"",4.7,2.6,2.2,0.2),
    Player("Megan Gustafson","C","6\'4\"",4.4,2.4,0.4,0.4),
    Player("Sarah Ashlee Barker","G","6\'0\"",3.9,2.1,1.0,0.6),
    Player("Kamiah Smalls","F","5\'10\"",3.1,0.9,1.7,0.7),
    Player("Frieda Buhner","F","6\'1\"",2.0,1.7,0.0,0.0),
    Player("Holly Winterburn","G","5\'11\"",2.0,1.0,4.0,0.0),
    Player("Serah Williams","C","6\'4\"",1.3,3.0,0.7,0.0),
    Player("Teja Oblak","G","5\'8\"",0.0,0.0,0.0,0.0),
]

# SEA — Seattle Storm
STARTERS_SEA = [
    Player("Flau'jae Johnson","G","5\'10\"",12.3,5.0,1.3,1.0),
    Player("Ezi Magbegor","F","6\'4\"",9.7,6.0,1.7,0.4),
    Player("Stefanie Dolson","C","6\'5\"",8.3,4.4,1.8,0.7),
    Player("Dominique Malonga","C","6\'6\"",8.2,4.8,0.8,0.1),
    Player("Natisha Hiedeman","G","5\'8\"",7.4,1.8,2.5,1.2),
]
BENCH_SEA = [
    Player("Jordan Horston","F","6\'2\"",6.6,4.6,1.7,0.3),
    Player("Katie Lou Samuelson","F","6\'3\"",5.9,2.5,1.4,1.0),
    Player("Lexie Brown","G","5\'9\"",5.7,1.5,1.7,1.1),
    Player("Jade Melbourne","G","5\'10\"",5.2,1.5,2.1,0.5),
    Player("Grace VanSlooten","F","6\'3\"",4.3,1.5,0.8,0.5),
    Player("Zia Cooke","G","5\'9\"",4.3,0.8,0.7,0.5),
    Player("Mackenzie Holmes","F","6\'3\"",1.5,1.6,0.3,0.1),
    Player("Taylor Thierry","F","6\'1\"",0.4,0.4,0.1,0.1),
    Player("Awa Fam","C","6\'4\"",0.0,0.0,0.0,0.0),
    Player("Taina Mair","G","5\'9\"",0.0,0.0,0.0,0.0),
]

# TOR — Toronto Tempo
STARTERS_TOR = [
    Player("Sylvia F + 9","G","5-8",27.0,4.5,3.0,3.0),
    Player("Katherine Plouffe","F","6-2",18.5,7.5,4.0,2.0),
    Player("Megan Laizer","C","6-5",14.0,8.5,2.5,0.5),
    Player("Cassidy MihARA","G","5-10",13.5,4.0,5.5,1.8),
    Player("Natalia Mike","F","6-2",12.0,5.5,2.0,0.8),
]
BENCH_TOR = [
    Player("Jaylyne Widener","G","5-9",11.0,3.5,4.0,1.5),
    Player("Olga Osimani","F","6-3",10.5,6.0,2.0,0.8),
    Player("Christina Brown","G","5-10",9.5,3.5,4.5,1.2),
    Player("Paige Gait","C","6-4",8.5,5.0,1.5,0.0),
    Player("Aaliyah Garner","F","6-1",7.5,4.0,1.5,0.6),
    Player("Teanna Lewis","G","5-8",6.0,2.5,3.0,0.8),
    Player("Brittney Sykes","G","6\'0\"",5.1,0.9,1.0,0.0),
    Player("Marina Mabrey","G","6\'0\"",4.2,0.8,0.5,0.0),
    Player("Kiki Rice","G","6\'0\"",2.3,0.7,0.4,0.0),
    Player("Nyara Sabally","F","6\'0\"",2.3,1.5,0.6,0.0),
    Player("Temi Fagbenle","C","6\'0\"",2.0,1.0,1.0,0.0),
    Player("Laura Juskaite","F","6\'0\"",1.6,0.8,0.2,0.0),
    Player("Maria Conde","F","6\'0\"",1.2,0.8,0.2,0.0),
    Player("Julie Allemand","G","6\'0\"",1.1,0.8,1.3,0.0),
    Player("Nikolina Milic","F","6\'0\"",0.7,0.3,0.1,0.0),
    Player("Kia Nurse","G","6\'0\"",0.6,0.2,0.1,0.0),
    Player("Teonni Key","F","6\'0\"",0.6,0.6,0.1,0.0),
    Player("Lexi Held","G","6\'0\"",0.1,0.0,0.0,0.0),
    Player("Mariella Fasoula","C","6\'0\"",0.0,1.0,0.0,0.0),
]

# WAS — Washington Mystics
STARTERS_WAS = [
    Player("Kelsey Mitchell","G","5-8",24.0,3.5,2.5,2.5),
    Player("Brittany Sykes","G","5-9",15.0,4.0,5.5,1.0),
    Player("Ariel Atkins","G","5-11",12.0,3.5,3.0,1.5),
    Player("Keishna Murray","F","6-2",10.5,5.5,2.0,0.8),
    Player("Aliyah Boston","C","6-4",9.0,4.0,2.0,0.5),
]
BENCH_WAS = [
    Player("Mathilde Reding","F","6-3",8.5,4.5,1.5,0.8),
    Player("Jacie Lamm","C","6-4",7.0,5.0,1.0,0.0),
    Player("Emma Roderique","G","5-10",6.5,2.5,3.5,0.7),
    Player("Miya Davidson","F","6-2",5.5,3.5,1.0,0.5),
    Player("Sonia Citron","G","6\'0\"",5.0,0.9,0.5,0.0),
    Player("Cotie McMahon","G","6\'0\"",5.0,1.5,0.8,0.0),
    Player("Kiki Iriafen","F","6\'0\"",4.1,3.2,0.6,0.0),
    Player("Shakira Austin","C","6\'0\"",4.1,2.1,0.8,0.0),
    Player("Georgia Amoore","G","6\'0\"",1.4,0.3,1.1,0.0),
    Player("Lauren Betts","C","6\'0\"",1.4,0.8,0.1,0.0),
    Player("Lucy Olsen","G","6\'0\"",1.4,0.0,0.4,0.0),
    Player("Cassandre Prosper","G","6\'0\"",1.1,0.5,0.3,0.0),
    Player("Alex Wilson","G","6\'0\"",0.8,0.5,0.2,0.0),
    Player("Angela Dugalic","F","6\'0\"",0.6,0.6,0.1,0.0),
    Player("Rori Harmon","G","6\'0\"",0.4,0.5,0.6,0.0),
]
