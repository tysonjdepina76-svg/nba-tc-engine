#!/usr/bin/env python3
"""
NBA/WSBA Backtest Scraper
Scrapes ESPN summary boxscores and live rosters, saves TC projections + actuals.
"""
import json, os, urllib.request

CONS=0.85; LINE_FACTOR=0.88; Q_MULT=0.55

def fetch(url):
    req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req) as r: return json.loads(r.read())

def parse3pt(v):
    try: return float(str(v).split("-")[0])
    except: return 0.0

def status_factor(s):
    s=str(s).upper()
    if s in ("DNP","OUT","IR","SUSPENDED"): return 0
    if any(x in s for x in ("QUESTION","DOUBTFUL","GTD")): return Q_MULT
    return 1.0

def annotate(s):
    out=dict(s)
    for stat in ["pts","reb","ast","tpm","stl","blk"]:
        raw=float(out.get(stat,0) or 0)
        tc=round(raw*CONS*status_factor(out.get("status","ACTIVE")),1)
        out[f"tc_{stat}"]=tc
        out[f"line_{stat}"]=round(tc*LINE_FACTOR)
        out[f"edge_{stat}"]=round(tc-round(tc*LINE_FACTOR),1)
    return out

TEAM_MAP={"SA":"SAS","GS":"GSW","LV":"LVA","DAL":"DAL","WSH":"WSH","NYK":"NYK","UTA":"UTA","WAS":"WAS","IND":"IND"}

def liveRoster(sport, abbr):
    code=TEAM_MAP.get(abbr, abbr)
    url=f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport.lower()}/teams/{code}/roster"
    data=fetch(url)
    players=[]
    for item in data.get("athletes",[]):
        ath=item.get("athlete",item)
        sid=str(ath.get("id",""))
        stats_url=f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/{sport.lower()}/athletes/{sid}/statistics?lang=en&region=us"
        try: st=fetch(stats_url)
        except: st=None
        cats=st.get("splits",{}).get("categories",[]) if st else []
        def avg(key):
            for c in cats:
                for s in c.get("stats",[]):
                    if s.get("name")==key:
                        v=s.get("value",s.get("displayValue",0))
                        try: return float(v)
                        except: return 0.0
            return 0.0
        pos=ath.get("position",{}).get("abbreviation","")
        raw_status=ath.get("status",{}).get("abbreviation","ACTIVE")
        status=str(raw_status).upper()
        dnp=status in ("DNP","OUT","IR","SUSPENDED") or status=="COACH'S DECISION"
        s={"id":sid,"name":ath.get("displayName","Unknown"),"pos":pos,"status":status,
           "starter":bool(item.get("starter",False)),"dnp":dnp}
        s["minutes"]=round(avg("avgMinutes"),1)
        s["pts"]=round(avg("avgPoints"),1)
        s["reb"]=round(avg("avgRebounds"),1)
        s["ast"]=round(avg("avgAssists"),1)
        s["tpm"]=round(avg("avgThreePointFieldGoalsMade"),1)
        s["stl"]=round(avg("avgSteals"),1)
        s["blk"]=round(avg("avgBlocks"),1)
        if s["name"]!="Unknown": players.append(annotate(s))
    return players

GAMES=[
    {"sport":"WNBA","event":"401856943","away":"LV","home":"DAL","label":"WNBA_DAL_LV"},
    {"sport":"WNBA","event":"401856944","away":"GS","home":"IND","label":"WNBA_GS_IND"},
    {"sport":"NBA","event":"401873202","away":"SA","home":"OKC","label":"NBA_WCF_SA_OKC"},
]
os.makedirs("/home/workspace/backtest", exist_ok=True)

for cfg in GAMES:
    sport=cfg["sport"]; ev_id=cfg["event"]; away=cfg["away"]; home=cfg["home"]; label=cfg["label"]
    print(f"\n{'='*60}\n  BACKTEST: {label}  {away}@{home}\n{'='*60}")
    try:
        data=fetch(f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport.lower()}/summary?event={ev_id}")
        comp=data.get("header",{}).get("competitions",[{}])[0]
        date=comp.get("date","")[:10]
        status=data.get("header",{}).get("status",{}).get("type",{}).get("description","")
        away_score=home_score=0
        for c in comp.get("competitors",[]):
            if c.get("homeAway")=="away": away_score=int(c.get("score") or 0)
            else: home_score=int(c.get("score") or 0)
        actual_total=round(away_score+home_score,1)

        print(f"  Fetching TC roster projection...")
        try:
            away_players=liveRoster(sport,away)
            home_players=liveRoster(sport,home)
        except Exception as e:
            print(f"  Roster fetch error (will use historical only): {e}")
            away_players=home_players=[]

        away_active=[p for p in away_players if not p.get("dnp")]
        home_active=[p for p in home_players if not p.get("dnp")]
        tc_away=round(sum(p["tc_pts"] for p in away_active),1)
        tc_home=round(sum(p["tc_pts"] for p in home_active),1)
        tc_comb=round(tc_away+tc_home,1)
        tc_line=round(tc_comb*LINE_FACTOR)
        edge=round(tc_line-actual_total,1)
        signal="OVER" if edge>2 else "UNDER" if edge<-2 else "ON_LINE"
        print(f"  Date   : {date} | {status}")
        print(f"  Actual : {away} {away_score} - {home} {home_score}  (total={actual_total})")
        print(f"  TC proj: {tc_away}+{tc_home}={tc_comb} | TC Line={tc_line} | edge={edge} -> {signal}")
        print(f"  Roster : {away}({len(away_active)}) @ {home}({len(home_active)})")
        all_p=away_active+home_active
        for stat,lbl in [("pts","PTS"),("reb","REB"),("ast","AST"),("tpm","3PM")]:
            if not all_p: continue
            best=max(all_p, key=lambda x: x.get(stat,0))
            print(f"    {lbl}: {best['name']} | avg={best[stat]} TC={best['tc_'+stat]} line={best['line_'+stat]} edge={best['edge_'+stat]}")
        out={
            "game_label":label,"sport":sport,"event_id":ev_id,"date":date,"status":status,
            "matchup":f"{away}@{home}",
            "actual_score":{"away":away_score,"home":home_score,"total":actual_total},
            "tc_projection":{"tc_away":tc_away,"tc_home":tc_home,"tc_combined":tc_comb,"tc_line":tc_line},
            "edge_vs_actual":edge,"signal":signal,
            "formula":{"CONS":CONS,"LINE_FACTOR":LINE_FACTOR,"Q_MULT":Q_MULT},
            "teams":{"away":{"abbr":away,"players":away_players},"home":{"abbr":home,"players":home_players}}
        }
        fname=f"/home/workspace/backtest/{label.lower()}.json"
        with open(fname,"w") as f: json.dump(out,f,indent=2)
        print(f"  Saved -> backtest/{label.lower()}.json")
    except Exception as e:
        print(f"  ERROR: {e}"); import traceback; traceback.print_exc()
