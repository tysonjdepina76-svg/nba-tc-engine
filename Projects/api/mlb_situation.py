"""MLB Live Situation API — pitch count, bases, batter, pitcher"""
import requests, json, time

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
CACHE = {}
CACHE_TTL = 30

def get_mlb_situation(game_id: str = None):
    now = time.time()
    cache_key = "mlb_situation"
    if cache_key in CACHE and now - CACHE[cache_key]["ts"] < CACHE_TTL:
        data = CACHE[cache_key]["data"]
    else:
        r = requests.get(ESPN_SCOREBOARD, timeout=10)
        r.raise_for_status()
        data = r.json()
        CACHE[cache_key] = {"ts": now, "data": data}
    
    events = data.get("events", [])
    situations = {}
    
    for ev in events:
        eid = ev.get("id", "")
        short = ev.get("shortName", "?")
        status = ev.get("status", {})
        state = status.get("type", {}).get("state", "pre")
        
        competitions = ev.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]
        sit = comp.get("situation", {})
        
        home = comp.get("competitors", [{}])[0] if len(comp.get("competitors", [])) > 0 else {}
        away = comp.get("competitors", [{}])[1] if len(comp.get("competitors", [])) > 1 else {}
        
        batter_ref = sit.get("batter", {})
        pitcher_ref = sit.get("pitcher", {})
        
        batter_name = ""
        pitcher_name = ""
        
        if batter_ref.get("$ref"):
            # fetch batter details
            try:
                br = requests.get(batter_ref["$ref"], timeout=5)
                batter_name = br.json().get("fullName", "")
            except:
                batter_name = batter_ref.get("athlete", {}).get("fullName", "")
        else:
            batter_name = batter_ref.get("athlete", {}).get("fullName", "")
        
        if pitcher_ref.get("$ref"):
            try:
                pr = requests.get(pitcher_ref["$ref"], timeout=5)
                pitcher_name = pr.json().get("fullName", "")
            except:
                pitcher_name = pitcher_ref.get("athlete", {}).get("fullName", "")
        else:
            pitcher_name = pitcher_ref.get("athlete", {}).get("fullName", "")
        
        on_first = bool(sit.get("onFirst"))
        on_second = bool(sit.get("onSecond"))
        on_third = bool(sit.get("onThird"))
        
        # Extract pitch count from pitching statistics if available
        pitch_count = ""
        pc_st = ""
        for comp_team in comp.get("competitors", []):
            for stat_group in comp_team.get("statistics", []):
                if stat_group.get("name") == "pitching":
                    for s in stat_group.get("stats", []):
                        if s.get("name") == "pitches":
                            pitch_count = str(s.get("displayValue", "")) if s.get("displayValue") else pitch_count
                        if "strike" in s.get("name", "").lower():
                            pc_st = str(s.get("displayValue", "")) if s.get("displayValue") else pc_st
        
        # Extract due up batters from situation
        due_up = []
        due_up_refs = sit.get("dueUp", [])
        for d in due_up_refs:
            if isinstance(d, dict):
                due_up.append(d.get("athlete", {}).get("fullName", "") or d.get("fullName", ""))
            elif isinstance(d, str):
                due_up.append(d)
        
        situations[eid] = {
            "event_id": str(eid),
            "shortName": short,
            "state": state,
            "period": sit.get("batter", {}).get("inning") or status.get("period", 0),
            "isTopInning": sit.get("isTopInning", False),
            "outs": sit.get("outs", 0),
            "balls": sit.get("balls", 0),
            "strikes": sit.get("strikes", 0),
            "batter": batter_name,
            "pitcher": pitcher_name,
            "pitchCount": pitch_count,
            "pcSt": pc_st,
            "dueUp": due_up,
            "onFirst": on_first,
            "onSecond": on_second,
            "onThird": on_third,
            "bases_empty": not (on_first or on_second or on_third),
            "bases_loaded": on_first and on_second and on_third,
            "home_score": home.get("score", "0"),
            "away_score": away.get("score", "0"),
        }
    
    return situations
