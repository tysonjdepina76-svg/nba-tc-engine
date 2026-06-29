import sys
sys.path.insert(0, '/home/workspace/tc-sports-app')
from src.domain.entities import Player, Projection
from src.domain.fantasy_images import FantasyImageGenerator

gen = FantasyImageGenerator('SOCCER')
p = Player(name='Bebe', team='Cape Verde', position='FWD', role='STARTER')
proj = Projection(player='Bebe', team='Cape Verde', role='FWD', stat='points', status='ACTIVE', tc_projection=12.5, line=10.0, edge=3.2, direction='OVER', valid=True)
path1 = gen.generate_player_card(p, proj)
print(f'CARD: {path1}')

projs = [
    Projection(player='Bebe', team='Cape Verde', role='FWD', stat='points', status='ACTIVE', tc_projection=12.5, line=10.0, edge=3.2, direction='OVER', valid=True),
    Projection(player='Ronaldo', team='Portugal', role='FWD', stat='points', status='ACTIVE', tc_projection=15.2, line=12.0, edge=4.1, direction='OVER', valid=True),
]
path2 = gen.generate_weekly_roundup(projs)
print(f'ROUNDUP: {path2}')