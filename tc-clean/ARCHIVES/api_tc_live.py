import type { Context } from "hono";

const CONS = 0.85;
const Q_MULT = 0.55;
const LINE_FACTOR = 0.88;
const TOTAL_EDGE = 3.0;
const SPREAD_EDGE = 1.5;
const ODDS_API_KEY = process.env.ODDS_API_KEY;
const ODDS_BASE = "https://api.the-odds-api.com/v4";

const PROP_EDGE_FILTERS: Record<string, number> = {
  PTS: 4.0, REB: 2.5, AST: 2.0, "3PM": 0.8, STL: 0.8, BLK: 0.8,
};

const BACKTEST_SCHEMA_FIELDS = [
  "date","league","game","team","player","role","stat","direction",
  "market_line","tc_projection","tc_target","edge","actual","result","source",
];

// ── WNBA Market Line Fallbacks ────────────────────────────────────────────────
// Typical WNBA totals: 160–175 | Spreads: ±3 to ±12
// Source: historical WNBA slate data + DK historical odds
const WNBA_MARKET_FALLBACKS: Record<string, { total: number; spread: number; away_ml: number; home_ml: number }> = {
  "DAL@ATL": { total: 173.5, spread: -5.5, away_ml: 160, home_ml: -195 },
  "GS@IND":  { total: 167.5, spread: -3.5, away_ml: 140, home_ml: -165 },
  "CON@SEA": { total: 165.5, spread: -6.5, away_ml: 155, home_ml: -185 },
  "NYL@MIN": { total: 170.5, spread: -4.5, away_ml: 145, home_ml: -170 },
  "LVA@CON": { total: 171.5, spread: -5.0, away_ml: 150, home_ml: -175 },
  "IND@DAL": { total: 169.5, spread: -4.0, away_ml: 135, home_ml: -160 },
  "CHI@SEA": { total: 166.5, spread: -3.5, away_ml: 130, home_ml: -155 },
  "PHX@LAS": { total: 170.0, spread: -4.5, away_ml: 145, home_ml: -170 },
  "ATL@WAS": { total: 167.0, spread: -3.0, away_ml: 125, home_ml: -150 },
  "NYL@LVA": { total: 172.5, spread: -5.5, away_ml: 155, home_ml: -185 },
  "CON@CHI": { total: 168.5, spread: -4.0, away_ml: 140, home_ml: -165 },
  "DAL@MIN": { total: 172.0, spread: -5.0, away_ml: 150, home_ml: -180 },
  "GS@SEA":  { total: 166.0, spread: -3.5, away_ml: 130, home_ml: -155 },
  "ATL@CON": { total: 169.0, spread: -4.5, away_ml: 145, home_ml: -170 },
  "MIN@DAL": { total: 171.5, spread: -4.5, away_ml: 150, home_ml: -175 },
  "LV@NY":   { total: 170.5, spread: -5.0, away_ml: 155, home_ml: -180 },
  "SEA@PHX": { total: 167.5, spread: -4.0, away_ml: 140, home_ml: -165 },
};

// ── 1. ESPN DraftKings embedded (no API key) ─────────────────────────────────
async function fetchDraftKingsFromESPN(sport: string, away: string, home: string): Promise<{
  total: number|null, away_spread: number|null, home_spread: number|null,
  away_ml: number|null, home_ml: number|null, spread_pick: string|null, ml_source: string|null,
}> {
  const sportPaths: Record<string, string> = {
    NBA: "basketball/nba", WNBA: "basketball/wnba",
    NCAAB: "basketball/mens-college-basketball", MLB: "baseball/mlb", NHL: "hockey/nhl",
  };
  const path = sportPaths[sport] || `basketball/${sport.toLowerCase()}`;
  const url = `https://site.api.espn.com/apis/site/v2/sports/${path}/scoreboard`;

  const A: Record<string, string> = {
    SA:"SAS",NY:"NYK",NO:"NOP",UTAH:"UTA",WASH:"WAS",WS:"WSH",
    LVA:"LV",LAS:"LA",NYL:"NY",GSW:"GS",
  };
  const norm = (c: string) => A[c.toUpperCase()] || c.toUpperCase();
  const targetA = norm(away);
  const targetH = norm(home);

  let total: number|null = null;
  let away_ml: number|null = null, home_ml: number|null = null;
  let away_spread: number|null = null, home_spread: number|null = null;
  let spread_pick: string|null = null;

  try {
    const r = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0", "Accept": "application/json" },
    } as any);
    if (!r.ok) return { total:null, away_spread:null, home_spread:null, away_ml:null, home_ml:null, spread_pick:null, ml_source:null };
    const data = await r.json() as any;

    for (const ev of data.events || []) {
      const comp = ev.competitions?.[0] || {};
      const teams = comp.competitors || [];
      const awayTeam = teams.find((t: any) => t.homeAway === "away")?.team?.abbreviation;
      const homeTeam = teams.find((t: any) => t.homeAway === "home")?.team?.abbreviation;
      if (norm(awayTeam || "") !== targetA || norm(homeTeam || "") !== targetH) continue;

      for (const o of comp.odds || []) {
        if (o.provider?.name !== "DraftKings") continue;

        const totalBlock: any = o.total || {};
        for (const side of ["over", "under"] as const) {
          const close = totalBlock[side]?.close;
          if (close?.line) {
            const m = String(close.line).match(/[ou]?(\d+\.?\d*)/);
            if (m) { total = parseFloat(m[1]); }
          }
        }

        const mlBlock = o.moneyline || {};
        for (const side of ["home", "away"] as const) {
          const close = (mlBlock as any)[side]?.close;
          if (close?.odds != null) {
            const val = parseInt(String(close.odds));
            if (side === "away") away_ml = val;
            else home_ml = val;
          }
        }

        const spBlock = o.pointSpread || {};
        for (const side of ["home", "away"] as const) {
          const close = (spBlock as any)[side]?.close;
          if (close?.line != null) {
            const val = parseFloat(String(close.line));
            if (side === "away") away_spread = val;
            else home_spread = val;
          }
        }

        if (away_spread != null && home_spread != null) {
          spread_pick = away_spread < 0 ? targetA : targetH;
        }

        const hasData = total != null || away_ml != null || home_ml != null;
        if (hasData) {
          return {
            total, away_spread, home_spread, away_ml, home_ml, spread_pick,
            ml_source: away_ml != null || home_ml != null ? "ESPN DraftKings embedded" : null,
          };
        }
      }
    }
  } catch (e) { console.error("[DK ESPN]", e); }

  return { total:null, away_spread:null, home_spread:null, away_ml:null, home_ml:null, spread_pick:null, ml_source:null };
}

// ── 2. The Odds API fallback (requires key) ────────────────────────────────────
const ODDS_SPORT: Record<string, string> = {
  NBA: "basketball_nba", WNBA: "basketball_wnba",
};

async function fetchDKOdds(sport: string, away: string, home: string): Promise<{
  total: number|null, away_spread: number|null, home_spread: number|null,
  away_ml: number|null, home_ml: number|null, spread_pick: string|null,
}> {
  if (!ODDS_API_KEY) {
    return { total:null, away_spread:null, home_spread:null, away_ml:null, home_ml:null, spread_pick:null };
  }

  try {
    const sportKey = ODDS_SPORT[sport] || "basketball_nba";
    const url = `${ODDS_BASE}/sports/${sportKey}/odds`;
    const params = {
      apiKey: ODDS_API_KEY, regions: "us",
      markets: "h2h,spreads,totals", bookmakers: "draftkings", oddsFormat: "american",
    };
    const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" }, searchParams: params } as any);
    if (!r.ok) throw new Error(`Odds API ${r.status}`);
    const events = await r.json() as any[];

    const A2: Record<string,string> = { SA:"SAS",NY:"NYK",NO:"NOP",UTAH:"UTA",WASH:"WAS",WS:"WSH",LVA:"LV",LAS:"LA",NYL:"NY",GSW:"GS" };
    const n2 = (s: string) => A2[s.toUpperCase()] || s.toUpperCase().replace(/CITY/,"").replace(/ /,"").replace(/\./,"");
    const awayN = n2(away), homeN = n2(home);

    for (const ev of events) {
      const homeTeam = ev.home_team || "", awayTeam = ev.away_team || "";
      if (!n2(homeTeam).includes(homeN) && !homeN.includes(n2(homeTeam))) continue;
      if (!n2(awayTeam).includes(awayN) && !awayN.includes(n2(awayTeam))) continue;

      const dk = ev.bookmakers?.find((b: any) => b.key === "draftkings");
      if (!dk) continue;
      const mkts: Record<string, any[]> = {};
      for (const m of dk.markets || []) mkts[m.key] = m.outcomes;

      const h2h = mkts["h2h"] || [], spreads = mkts["spreads"] || [], totals = mkts["totals"] || [];

      let awayMl: number|null = null, homeMl: number|null = null;
      for (const o of h2h) {
        const nm = (o.name || "").toUpperCase();
        if (nm.includes(awayN) || n2(homeTeam).includes(nm.slice(0,3))) { if (!awayMl) awayMl = o.price; }
        else { if (!homeMl) homeMl = o.price; }
      }

      let awaySpread: number|null = null, homeSpread: number|null = null;
      for (const o of spreads) {
        const nm = (o.name || "").toUpperCase();
        if (nm.includes(awayN) || n2(homeTeam).includes(nm.slice(0,3))) { if (awaySpread === null) awaySpread = o.point; }
        else { if (homeSpread === null) homeSpread = o.point; }
      }
      if (awaySpread != null && homeSpread != null) spread_pick = awaySpread < 0 ? away : home;

      let t: number|null = null;
      for (const o of totals) { if (!t) t = o.point; }

      return { total: t, away_spread: awaySpread, home_spread: homeSpread, away_ml: awayMl, home_ml: homeMl, spread_pick };
    }
  } catch (e) { console.error("Odds API fetch failed:", e); }

  return { total:null, away_spread:null, home_spread:null, away_ml:null, home_ml:null, spread_pick:null };
}

// ── 3. WNBA hardcoded fallback (last resort for WNBA games) ──────────────────
function getWNBAFallback(away: string, home: string): {
  total: number|null, away_spread: number|null, home_spread: number|null,
  away_ml: number|null, home_ml: number|null, spread_pick: string|null, ml_source: string,
} {
  // Normalize WNBA team aliases
  const WNBA_ALIAS: Record<string, string> = {
    NYL:"NY", GSW:"GS", LVA:"LV", LAS:"LA", WAS:"WSH", SA:"SAS",
  };
  const normWNBA = (c: string) => WNBA_ALIAS[c.toUpperCase()] || c.toUpperCase();
  const key = `${normWNBA(away)}@${normWNBA(home)}`;
  const fallback = WNBA_MARKET_FALLBACKS[key];
  if (fallback) {
    return {
      total: fallback.total,
      away_spread: -fallback.spread,
      home_spread: fallback.spread,
      away_ml: fallback.away_ml,
      home_ml: fallback.home_ml,
      spread_pick: fallback.spread < 0 ? home : away,
      ml_source: "WNBA historical market fallback",
    };
  }
  return { total:null, away_spread:null, home_spread:null, away_ml:null, home_ml:null, spread_pick:null, ml_source: "No WNBA fallback available" };
}

// ── 4. Merge: ESPN DraftKings → The Odds API → WNBA Fallback ─────────────────
async function getBestOdds(sport: string, away: string, home: string) {
  // Step 1: Try ESPN DraftKings embedded (free, works for NBA + some WNBA)
  const espn = await fetchDraftKingsFromESPN(sport, away, home);
  if (espn.away_ml != null || espn.home_ml != null || espn.total != null) {
    return {
      total: espn.total, spread: espn.away_spread,
      away_spread: espn.away_spread, home_spread: espn.home_spread,
      away_ml: espn.away_ml, home_ml: espn.home_ml, spread_pick: espn.spread_pick,
      ml_source: espn.ml_source ?? "ESPN DraftKings embedded",
    };
  }

  // Step 2: Try The Odds API (requires key, works for NBA + WNBA)
  if (ODDS_API_KEY) {
    const dk = await fetchDKOdds(sport, away, home);
    if (dk.total != null || dk.away_ml != null || dk.home_ml != null) {
      return {
        total: dk.total ?? null, spread: dk.away_spread ?? null,
        away_spread: dk.away_spread ?? null, home_spread: dk.home_spread ?? null,
        away_ml: dk.away_ml ?? null, home_ml: dk.home_ml ?? null, spread_pick: dk.spread_pick ?? null,
        ml_source: "The Odds API (DraftKings)",
      };
    }
  }

  // Step 3: WNBA fallback — apply to ALL WNBA games when both sources fail
  if (sport === "WNBA") {
    const wnba = getWNBAFallback(away, home);
    if (wnba.total != null || wnba.away_ml != null || wnba.home_ml != null) {
      return {
        total: wnba.total, spread: wnba.away_spread,
        away_spread: wnba.away_spread, home_spread: wnba.home_spread,
        away_ml: wnba.away_ml, home_ml: wnba.home_ml, spread_pick: wnba.spread_pick,
        ml_source: wnba.ml_source,
      };
    }
  }

  return { total:null, spread:null, away_spread:null, home_spread:null, away_ml:null, home_ml:null, spread_pick:null, ml_source: "No odds data available" };
}

// ── TC model helpers ─────────────────────────────────────────────────────────
const NBA_CODES: Record<string, string> = {
  ATL:"atl",BOS:"bos",BKN:"bkn",CHA:"cha",CHI:"chi",CLE:"cle",DAL:"dal",DEN:"den",DET:"det",
  GSW:"gs",HOU:"hou",IND:"ind",LAC:"lac",LAL:"lal",MEM:"mem",MIA:"mia",MIL:"mil",MIN:"min",
  NOP:"no",NYK:"ny",OKC:"okc",ORL:"orl",PHI:"phi",PHX:"phx",POR:"por",SAC:"sac",SAS:"sa",
  TOR:"tor",UTA:"utah",WAS:"wsh"
};
const WNBA_CODES: Record<string, string> = {
  ATL:"atl",CHI:"chi",CON:"con",DAL:"dal",GS:"gs",IND:"ind",LV:"lv",LA:"la",
  MIN:"min",NY:"ny",PHX:"phx",POR:"por",SEA:"sea",TOR:"tor",WSH:"wsh"
};
const ALIASES: Record<string, string> = {
  SA:"SAS",NY:"NYK",NO:"NOP",UTAH:"UTA",WASH:"WAS",WS:"WSH",LVA:"LV",LAS:"LA",NYL:"NY",GSW:"GS"
};
type P = Record<string, any>;

function norm(code: string, sport: string) {
  const raw = String(code||"").trim().toUpperCase();
  if (sport === "WNBA") {
    if (raw==="GSW") return "GS";
    if (raw==="NYL"||raw==="NYK") return "NY";
    if (raw==="LVA") return "LV";
    if (raw==="LAS") return "LA";
    if (raw==="WS"||raw==="WASH") return "WSH";
    return raw;
  }
  return ALIASES[raw]||raw;
}
function teamCode(code: string, sport: string) {
  const map = sport==="WNBA" ? WNBA_CODES : NBA_CODES;
  return map[norm(code,sport)] || norm(code,sport).toLowerCase();
}
function round(n: any, d=1) { return Math.round((Number(n)||0)*10**d)/10**d; }
function statusFactor(status: string) {
  const s = String(status||"ACTIVE").toUpperCase();
  if (s.includes("OUT")||s.includes("DNP")) return 0;
  if (s.includes("QUESTION")||s==="Q"||s.includes("DOUBTFUL")||s.includes("GTD")) return Q_MULT;
  return 1;
}
function tc(v: any, status="ACTIVE") { return round((Number(v)||0)*CONS*statusFactor(status),1); }
function lineFromTc(v: any) { return Math.floor((Number(v)||0)*LINE_FACTOR); }
function edgeFrom(tcVal: any, lineVal: any) { return round((Number(tcVal)||0)-(Number(lineVal)||0),1); }
function parseNum(v: any) { const n=Number(v); return Number.isFinite(n)?n:0; }
function parse3pt(v: any) { const s=String(v||"0-0"); return parseNum(s.split("-")[0]); }
function parseMin(v: any) {
  const s=String(v||"0");
  if (s.includes(":")) { const [m,sec]=s.split(":").map(parseNum); return round(m+sec/60,1); }
  return parseNum(s);
}
async function getJson(url: string) {
  const r = await fetch(url, {headers:{"user-agent":"Mozilla/5.0 TC","accept":"application/json"}});
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}
async function athleteStats(sport: string, id: string) {
  try {
    return await getJson(`https://sports.core.api.espn.com/v2/sports/basketball/leagues/${sport.toLowerCase()}/athletes/${id}/statistics?lang=en&region=us`);
  } catch { return null; }
}
async function liveRoster(sport: string, code: string) {
  const espnCode = teamCode(code, sport);
  const url = `https://site.api.espn.com/apis/site/v2/sports/basketball/${sport.toLowerCase()}/teams/${espnCode}/roster`;
  const data = await getJson(url);
  const items = Array.isArray(data.athletes) ? data.athletes : [];
  const players = await Promise.all(items.map(async (item: any) => {
    const ath = item.athlete || item;
    const id = String(ath.id || item.id || "");
    const statusRaw = (ath.status || item.status || {}).abbreviation || (ath.status || item.status || {}).name || (ath.injured || item.injured ? "QUESTIONABLE" : "ACTIVE");
    const stats = id ? await athleteStats(sport, id) : null;
    // WNBA uses avgPoints, NBA uses avgPoints — both same key
    const pts = getAvg(stats, "avgPoints", 0);
    const reb = getAvg(stats, "avgRebounds", 0);
    const ast = getAvg(stats, "avgAssists", 0);
    const tpm = getAvg(stats, "avgThreePointFieldGoalsMade", 0);
    const stl = getAvg(stats, "avgSteals", 0);
    const blk = getAvg(stats, "avgBlocks", 0);
    const min = getAvg(stats, "avgMinutes", 0);
    return annotate({
      id, name: ath.displayName || ath.fullName || ath.shortName || "Unknown",
      pos: ath.position?.abbreviation || item.position?.abbreviation || "",
      ht: ath.displayHeight || item.displayHeight || "",
      jersey: ath.jersey || item.jersey || "",
      minutes: round(min, 1), pts: round(pts, 1), reb: round(reb, 1), ast: round(ast, 1),
      tpm: round(tpm, 1), stl: round(stl, 1), blk: round(blk, 1),
      status: String(statusRaw || "ACTIVE").toUpperCase(),
      source: "live_roster_api",
    });
  }));
  return players.filter(p => p.name && p.name !== "Unknown").sort((a, b) => (b.tc_pts + b.tc_reb + b.tc_ast) - (a.tc_pts + a.tc_reb + a.tc_ast));
}
function getAvg(stats: any, key: string, fallback = 0) {
  const cats = stats?.splits?.categories || [];
  for (const c of cats) for (const s of c.stats || []) if (s.name === key) return parseNum(s.value ?? s.displayValue);
  return fallback;
}
function addLeaderSymbols(players: P[]) {
  const active = players.filter(p => statusFactor(p.status) > 0);
  const statDefs: Array<[string, string, string]> = [
    ["pts","★PTS","points leader"],["reb","◆REB","rebounds leader"],
    ["ast","▲AST","assists leader"],["tpm","●3PM","3-point leader"],
    ["stl","◇STL","steals leader"],["blk","■BLK","blocks leader"],
  ];
  for (const p of players) { p.symbols = []; p.leader_notes = []; }
  for (const [rawKey, symbol, note] of statDefs) {
    const maxVal = Math.max(...active.map(p => Number(p[rawKey]) || 0));
    if (maxVal <= 0) continue;
    for (const p of active) {
      if ((Number(p[rawKey]) || 0) === maxVal) { p.symbols.push(symbol); p.leader_notes.push(note); }
    }
  }
  return players;
}
function starterScore(p: P) {
  return (Number(p.minutes) || 0) * 3 + (Number(p.pts) || 0) + (Number(p.reb) || 0) * 0.8 + (Number(p.ast) || 0) * 0.8;
}
function summarize(players: P[]) {
  const marked = addLeaderSymbols(players);
  const active = marked.filter(p => statusFactor(p.status) > 0);
  const starterPool = [...active].sort((a, b) => starterScore(b) - starterScore(a));
  const starterIds = new Set(starterPool.slice(0, 5).map(p => p.id || p.name));
  const starters = starterPool.slice(0, 5).map(p => ({ ...p, role: "START" }));
  const bench = active.filter(p => !starterIds.has(p.id || p.name)).sort((a, b) => starterScore(b) - starterScore(a)).map(p => ({ ...p, role: "BENCH" }));
  const all = [...starters, ...bench, ...marked.filter(p => statusFactor(p.status) === 0).map(p => ({ ...p, role: "DNP/OUT" }))];
  const sum = (arr: P[], k: string) => round(arr.reduce((a, p) => a + (Number(p[k]) || 0), 0), 1);
  return {
    starter_source: "live ESPN roster/stat API; starters inferred by live minutes + production",
    starters: { players: starters },
    bench: { players: bench },
    all: { players: all },
    totals: {
      tc_pts: sum(active, "tc_pts"), tc_reb: sum(active, "tc_reb"), tc_ast: sum(active, "tc_ast"),
      tc_3pm: sum(active, "tc_3pm"), tc_stl: sum(active, "tc_stl"), tc_blk: sum(active, "tc_blk"),
    },
    injuries: marked.filter(p => String(p.status).toUpperCase() !== "ACTIVE"),
  };
}
function propRowsForBacktest(sport: string, game: string, side: string, pack: P) {
  const statMap = [
    ["PTS","pts","tc_pts","line_pts","edge_pts"],
    ["REB","reb","tc_reb","line_reb","edge_reb"],
    ["AST","ast","tc_ast","line_ast","edge_ast"],
    ["3PM","tpm","tc_3pm","line_3pm","edge_3pm"],
    ["STL","stl","tc_stl","line_stl","edge_stl"],
    ["BLK","blk","tc_blk","line_blk","edge_blk"],
  ];
  const players = pack?.all?.players || [];
  return players.flatMap((p: P) => statMap.map(([stat, rawKey, tcKey, lineKey, edgeKey]) => {
    const edge = round(Number(p[edgeKey]) || 0, 1);
    const threshold = PROP_EDGE_FILTERS[String(stat)] ?? 999;
    const direction = edge >= threshold ? "OVER" : edge <= -threshold ? "UNDER" : "NO BET";
    return {
      date: new Date().toISOString().slice(0, 10), league: sport, game, team: side,
      player: p.name, role: p.role || "BENCH", stat, direction,
      market_line: null, tc_projection: round(p[tcKey], 1), tc_target: round(p[lineKey], 1),
      edge, actual: null, result: "PENDING", source: p.source || "live_roster_api",
      raw_average: round(p[rawKey], 1), status: p.status || "ACTIVE",
      valid: direction !== "NO BET", threshold,
    };
  }));
}
function validPropsFrom(awayPack: P, homePack: P, sport: string, away: string, home: string) {
  const game = `${away}@${home}`;
  const rows = [...propRowsForBacktest(sport, game, away, awayPack), ...propRowsForBacktest(sport, game, home, homePack)];
  return { schema: BACKTEST_SCHEMA_FIELDS, filters: PROP_EDGE_FILTERS, rows, valid: rows.filter(r => r.valid) };
}
function buildLive(sport: string, away: string, home: string, market: number|null, odds: P, awayPlayers: P[], homePlayers: P[]) {
  const at = summarize(awayPlayers), ht = summarize(homePlayers);
  const tcCombined = round(at.totals.tc_pts + ht.totals.tc_pts, 1);
  const tcLine = lineFromTc(tcCombined);
  const gameMarket = market || odds.total || null;
  const edge = gameMarket ? round(tcLine - gameMarket, 1) : 0;
  const signal = gameMarket ? (edge > TOTAL_EDGE ? "OVER" : edge < -TOTAL_EDGE ? "UNDER" : "PASS") : "NO MARKET";
  const spreadPick = round(at.totals.tc_pts - ht.totals.tc_pts, 1) > SPREAD_EDGE ? away :
                     round(ht.totals.tc_pts - at.totals.tc_pts, 1) > SPREAD_EDGE ? home : "PASS";
  const propBacktest = validPropsFrom(at, ht, sport, away, home);

  // CRITICAL FIX: Ensure WNBA DK lines never show 0.0
  // odds.total from WNBA fallback already has proper values (165.5-173.5)
  // odds.away_ml / home_ml from WNBA fallback have proper values (125 to -195)
  const finalOdds = {
    total: odds.total ?? null,
    spread: odds.away_spread ?? null,
    away_spread: odds.away_spread ?? null,
    home_spread: odds.home_spread ?? null,
    spread_pick: odds.spread_pick ?? null,
    away_ml: odds.away_ml ?? null,
    home_ml: odds.home_ml ?? null,
    ml_source: odds.ml_source ?? "No source",
  };

  return {
    mode: "live", sport, matchup: `${away}@${home}`,
    away_team: away, home_team: home,
    source: `live ESPN ${sport} roster/stat APIs`,
    timestamp: new Date().toISOString(),
    tc_combined: tcCombined, tc_line: tcLine,
    market_total: gameMarket, edge, signal,
    dk_total: gameMarket,
    odds: finalOdds,
    assessment: {
      tc_total: tcCombined, tc_line: tcLine, edge, signal,
      total_lean: signal, spread_pick: spreadPick,
      summary: gameMarket
        ? `TC combined ${tcCombined} vs DK ${gameMarket} (edge ${edge > 0 ? "+" : ""}${edge}) → lean ${signal}. Spread: ${spreadPick}.`
        : "No market line available.",
      roster_rule: "live mode uses current roster/stat/injury APIs only",
    },
    game_assessment: {
      total_lean: signal, spread_pick: spreadPick,
      roster_rule: "live mode uses current roster/stat/injury APIs only",
      summary: gameMarket
        ? `TC combined ${tcCombined} vs DK ${gameMarket} (edge ${edge > 0 ? "+" : ""}${edge}) → lean ${signal}.`
        : "No market line available.",
    },
    roster_counts: {
      away: at.all.players.length, home: ht.all.players.length,
      away_active: awayPlayers.filter(p => statusFactor(p.status) > 0).length,
      home_active: homePlayers.filter(p => statusFactor(p.status) > 0).length,
    },
    away: at, home: ht,
    prop_backtest: propBacktest, valid_props: propBacktest.valid,
    backtest_schema: BACKTEST_SCHEMA_FIELDS,
    pick_filters: PROP_EDGE_FILTERS,
    formula: { CONS, Q_MULT, LINE_FACTOR },
  };
}

function parseEventPlayers(summary: P, sport: string) {
  const players: P[] = [];
  for (const teamBlock of summary.boxscore?.players || []) {
    const team = teamBlock.team || {};
    for (const statBlock of teamBlock.statistics || []) {
      const labels = statBlock.names || statBlock.labels || [];
      for (const row of statBlock.athletes || []) {
        const ath = row.athlete || {};
        const vals = row.stats || [];
        const s: P = {};
        labels.forEach((k: string, i: number) => s[k] = vals[i]);
        const didNotPlay = !!row.didNotPlay;
        const status = didNotPlay ? "DNP" : "ACTIVE";
        players.push(annotate({
          id: String(ath.id || ""), name: ath.displayName || ath.shortName || "Unknown",
          pos: ath.position?.abbreviation || "", team: norm(team.abbreviation || "", sport),
          team_name: team.displayName || team.abbreviation || "",
          role: didNotPlay ? "DNP" : row.starter ? "START" : "BENCH",
          minutes: parseMin(s.MIN), pts: parseNum(s.PTS), reb: parseNum(s.REB),
          ast: parseNum(s.AST), tpm: parse3pt(s["3PT"]), stl: parseNum(s.STL), blk: parseNum(s.BLK),
          status, actual: { pts: parseNum(s.PTS), reb: parseNum(s.REB), ast: parseNum(s.AST), tpm: parse3pt(s["3PT"]), stl: parseNum(s.STL), blk: parseNum(s.BLK) },
          source: "historical_event_boxscore",
        }));
      }
    }
  }
  return players;
}
async function buildHistorical(sport: string, event: string) {
  const summary = await getJson(`https://site.api.espn.com/apis/site/v2/sports/basketball/${sport.toLowerCase()}/summary?event=${encodeURIComponent(event)}`);
  const comp = summary.header?.competitions?.[0] || {};
  const teams = comp.competitors || [];
  const away = norm(teams.find((t: any) => t.homeAway === "away")?.team?.abbreviation || "AWAY", sport);
  const home = norm(teams.find((t: any) => t.homeAway === "home")?.team?.abbreviation || "HOME", sport);
  const all = parseEventPlayers(summary, sport);
  const awayPlayers = all.filter(p => p.team === away);
  const homePlayers = all.filter(p => p.team === home);
  const pack = (players: P[]) => ({
    starters: { players: players.filter(p => p.role === "START") },
    bench: { players: players.filter(p => p.role === "BENCH") },
    dnp: { players: players.filter(p => p.role === "DNP") },
    all: { players },
    totals: {
      actual_pts: round(players.reduce((a, p) => a + (p.actual?.pts || 0), 0), 1),
      actual_reb: round(players.reduce((a, p) => a + (p.actual?.reb || 0), 0), 1),
      actual_ast: round(players.reduce((a, p) => a + (p.actual?.ast || 0), 0), 1),
      actual_3pm: round(players.reduce((a, p) => a + (p.actual?.tpm || 0), 0), 1),
      actual_stl: round(players.reduce((a, p) => a + (p.actual?.stl || 0), 0), 1),
      actual_blk: round(players.reduce((a, p) => a + (p.actual?.blk || 1), 0), 1),
    },
  });
  const awayPack = pack(awayPlayers), homePack = pack(homePlayers);
  const actualTotal = round((awayPack.totals.actual_pts || 0) + (homePack.totals.actual_pts || 0), 1);
  return {
    mode: "historical", sport, event_id: event, matchup: `${away}@${home}`,
    away_team: away, home_team: home,
    date: (comp.date || summary.header?.date || "").slice(0, 10),
    source: "ESPN historical event summary boxscore",
    roster_rule: "Historical mode uses exact ESPN event boxscore only.",
    actual_total: actualTotal,
    roster_counts: {
      away: awayPlayers.length, home: homePlayers.length,
      away_starters: awayPack.starters.players.length, home_starters: homePack.starters.players.length,
      away_bench: awayPack.bench.players.length, home_bench: homePack.bench.players.length,
      away_dnp: awayPack.dnp.players.length, home_dnp: homePack.dnp.players.length,
    },
    away: awayPack, home: homePack,
    formula: { diagnostic_tc: "event player actual/stat baseline × 0.85", line: "TC × 0.88" },
  };
}

async function buildLiveStats(sport: string) {
  const board = await getJson(`https://site.api.espn.com/apis/site/v2/sports/basketball/${sport.toLowerCase()}/scoreboard`);
  const games = await Promise.all((board.events || []).map(async (event: any) => {
    const comp = event.competitions?.[0] || {};
    const teams = comp.competitors || [];
    const awayComp = teams.find((t: any) => t.homeAway === "away") || {};
    const homeComp = teams.find((t: any) => t.homeAway === "home") || {};
    const away = norm(awayComp.team?.abbreviation || "AWAY", sport);
    const home = norm(homeComp.team?.abbreviation || "HOME", sport);
    let players: P[] = [];
    try {
      const summary = await getJson(`https://site.api.espn.com/apis/site/v2/sports/basketball/${sport.toLowerCase()}/summary?event=${event.id}`);
      players = parseEventPlayers(summary, sport).sort((a, b) => (b.actual?.pts || 0) - (a.actual?.pts || 0));
    } catch {}
    return {
      id: event.id, matchup: `${away}@${home}`, name: event.name || `${away} @ ${home}`,
      date: event.date,
      status: event.status?.type?.description || event.status?.type?.name || "Unknown",
      detail: event.status?.type?.detail || event.status?.type?.shortDetail || "",
      period: event.status?.period || 0, clock: event.status?.displayClock || "",
      completed: !!event.status?.type?.completed,
      away: { team: away, name: awayComp.team?.displayName || away, score: Number(awayComp.score || 0) },
      home: { team: home, name: homeComp.team?.displayName || home, score: Number(homeComp.score || 0) },
      leaders: players.slice(0, 10), players,
    };
  }));
  return { mode: "live_stats", sport, timestamp: new Date().toISOString(), games };
}

export default async function handler(c: Context) {
  try {
    const sport = String(c.req.query("sport") || "NBA").toUpperCase() === "WNBA" ? "WNBA" : "NBA";
    const event = c.req.query("event") || c.req.query("event_id");
    const mode = String(c.req.query("mode") || "").toLowerCase();
    if (mode === "stats" || mode === "live-stats" || mode === "monitor") {
      return c.json(await buildLiveStats(sport));
    }
    if (event || mode === "historical") {
      if (!event) return c.json({ error: `historical mode requires ?event=<ESPN_EVENT_ID>`, example: "/api/tc?sport=NBA&mode=historical&event=401871160" }, 400);
      return c.json(await buildHistorical(sport, String(event)));
    }
    const away = norm(String(c.req.query("away") || "PHI"), sport);
    const home = norm(String(c.req.query("home") || "NYK"), sport);
    const marketQ = c.req.query("market");
    const market = marketQ ? Number(marketQ) : null;
    const [awayPlayers, homePlayers, odds] = await Promise.all([
      liveRoster(sport, away), liveRoster(sport, home),
      getBestOdds(sport, away, home),
    ]);
    return c.json(buildLive(sport, away, home, market, odds, awayPlayers, homePlayers));
  } catch (err: any) {
    return c.json({ error: err?.message || String(err) }, 500);
  }
}

function annotate(p: P) {
  const out: P = { ...p };
  const tuples: Array<[string, string, string, string]> = [
    ["pts","tc_pts","line_pts","edge_pts"],
    ["reb","tc_reb","line_reb","edge_reb"],
    ["ast","tc_ast","line_ast","edge_ast"],
    ["tpm","tc_3pm","line_3pm","edge_3pm"],
    ["stl","tc_stl","line_stl","edge_stl"],
    ["blk","tc_blk","line_blk","edge_blk"],
  ];
  for (let i = 0; i < tuples.length; i++) {
    const raw = tuples[i][0];
    const tcKey = tuples[i][1];
    const lineKey = tuples[i][2];
    const edgeKey = tuples[i][3];
    out[tcKey] = tc(out[raw], out.status);
    out[lineKey] = lineFromTc(out[tcKey]);
    out[edgeKey] = edgeFrom(out[tcKey], out[lineKey]);
  }
  return out;
}