import json, urllib.request
r = urllib.request.urlopen("https://true.zo.space/api/tc?sport=WNBA&away=CHI&home=TOR", timeout=20)
d = json.loads(r.read())
print("formula:", d.get('formula'))
for p in d.get('away',{}).get('starters',{}).get('players',[])[:3]:
    print(p.get('name'), 'pts=', p.get('pts'), 'tc_pts=', p.get('tc_pts'),
          'stl=', p.get('stl'), 'tc_stl=', p.get('tc_stl'))
