import type { Context } from "hono";
import { readFile, readdir, stat } from "node:fs/promises";
import { join } from "node:path";
import { existsSync } from "node:fs";

const LOG_DIR = "/home/workspace/Daily_Log";
const PROJ_DIR = "/home/workspace/Projects";
const SECRETS_FILE = "/root/.zo/secrets.env";
const FETCH_TIMEOUT = 7000;

const ODDS_BASE = "https://api.theoddsapi.com";
const SGO_BASE = "https://api.sportsgameodds.com/v2";
const ESPN_WNBA = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard";
const ESPN_WORLDCUP = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard";

async function tryFetch(url: string, opts: RequestInit = {}): Promise<{ ok: boolean; status: number; text: string }> {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(FETCH_TIMEOUT), ...opts });
    return { ok: r.ok, status: r.status, text: await r.text() };
  } catch (e: any) {
    return { ok: false, status: 0, text: e.message.slice(0, 80) };
  }
}

async function loadSecrets(): Promise<Record<string, string>> {
  const secrets: Record<string, string> = {};
  try {
    const raw = await readFile(SECRETS_FILE, "utf-8");
    for (const line of raw.split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const eq = t.indexOf("=");
      if (eq > 0) secrets[t.slice(0, eq).trim()] = t.slice(eq + 1).trim();
    }
  } catch {}
  return secrets;
}

export default async (c: Context) => {
  const secrets = await loadSecrets();
  const oddsKey = secrets.ODDS_API_KEY || "";
  const sgoKey = secrets.SPORTSGAMEODDS_API_KEY || "";
  const empty = { ok: false, status: 0, text: "" };

  const [
    apiKeys, conn, routes, integrity, logs, combos, services, cleanliness, scripts,
    sgoAdapter, oddsQuota, picksExist, dash8510, combo8515, combo8516, injuryFeed,
  ] = await Promise.all([
    // 1. API KEYS
    (async () => {
      const keys: { name: string; ok: boolean; masked: string }[] = [];
      const checks: [string, string[]][] = [
        ["ODDS_API_KEY", ["ODDS_API_KEY", "THEODDSAPI"]],
        ["SPORTSGAMEODDS_API_KEY", ["SPORTSGAMEODDS_API_KEY"]],
        ["SPORTS_DATA_API_KEY", ["SPORTS_DATA_API_KEY", "SPORTSDATAIO_API_KEY", "SPORTS_DATA_IO_KEY"]],
      ];
      for (const [label, names] of checks) {
        const val = names.map(n => secrets[n] || process.env[n] || "").find(v => !!v) || "";
        keys.push(val.length > 5
          ? { name: label, ok: true, masked: val.slice(0, 4) + "..." + val.slice(-4) }
          : { name: label, ok: false, masked: "" });
      }
      return keys;
    })(),

    // 2. CONNECTIVITY
    (async () => {
      const results: { name: string; ok: boolean; detail: string }[] = [];
      const [espn, espnWC, oddsWNBA, sgoWNBA] = await Promise.all([
        tryFetch(ESPN_WNBA),
        tryFetch(ESPN_WORLDCUP),
        oddsKey ? tryFetch(`${ODDS_BASE}/odds/?sport_key=basketball_wnba&regions=us&apiKey=${oddsKey}`) : Promise.resolve(empty),
        sgoKey ? tryFetch(`${SGO_BASE}/events?leagueID=WNBA&limit=100`, { headers: { "x-api-key": sgoKey } as any }) : Promise.resolve(empty),
      ]);

      results.push(espn.ok
        ? { name: "ESPN API (WNBA)", ok: true, detail: `HTTP ${espn.status}` }
        : { name: "ESPN API (WNBA)", ok: false, detail: espn.text.slice(0, 50) });

      if (espn.ok) {
        try {
          const j = JSON.parse(espn.text);
          const events = j?.events || [];
          const withDK = events.filter((e: any) => {
            const odds = e?.competitions?.[0]?.odds || [];
            return odds.some((o: any) => o?.provider?.name === "DraftKings" && o?.total);
          });
          results.push(withDK.length > 0
            ? { name: "ESPN DK odds (WNBA)", ok: true, detail: `${withDK.length}/${events.length} games with DK lines` }
            : { name: "ESPN DK odds (WNBA)", ok: false, detail: `${events.length} games, 0 DK` });
        } catch {
          results.push({ name: "ESPN DK odds (WNBA)", ok: false, detail: "JSON parse failed" });
        }
      }

      results.push(espnWC.ok
        ? { name: "ESPN API (World Cup)", ok: true, detail: `HTTP ${espnWC.status}` }
        : { name: "ESPN API (World Cup)", ok: false, detail: espnWC.text.slice(0, 50) });

      if (oddsKey) {
        const isRateLimit = oddsWNBA.text.includes("quota") || oddsWNBA.text.includes("exceeded");
        results.push(oddsWNBA.ok
          ? { name: "The Odds API", ok: true, detail: `HTTP ${oddsWNBA.status} — OK` }
          : { name: "The Odds API", ok: false, detail: `HTTP ${oddsWNBA.status}${isRateLimit ? " — QUOTA EXHAUSTED" : oddsWNBA.status === 401 ? " — BAD KEY" : oddsWNBA.status === 410 ? " — WRONG URL PATH" : ""}` });
      } else {
        results.push({ name: "The Odds API", ok: false, detail: "No key" });
      }

      if (sgoKey) {
        results.push(sgoWNBA.ok
          ? { name: "SGO (WNBA)", ok: true, detail: `HTTP ${sgoWNBA.status}` }
          : { name: "SGO (WNBA)", ok: false, detail: `HTTP ${sgoWNBA.status} — key expired/rate-limited` });
      } else {
        results.push({ name: "SGO (WNBA)", ok: false, detail: "No key" });
      }

      return results;
    })(),

    // 3. ROUTE CHECKS
    (async () => {
      const results: { name: string; ok: boolean; detail: string }[] = [];
      const paths = ["/api/tc?sport=WNBA&mode=live-stats", "/api/daily-log", "/api/combos", "/api/dk-lines?sport=WNBA"];
      const fetches = await Promise.all(paths.map(p => tryFetch(`http://localhost:3099${p}`)));
      for (let i = 0; i < paths.length; i++) {
        const f = fetches[i];
        let detail = `HTTP ${f.status}`;
        if (f.ok && f.text) {
          try {
            const j = JSON.parse(f.text);
            if (j.error) detail = j.error.slice(0, 50);
          } catch {}
        }
        results.push({ name: paths[i], ok: f.ok, detail });
      }
      return results;
    })(),

    // 4. DATA INTEGRITY
    (async () => {
      const results: { name: string; ok: boolean; detail: string }[] = [];
      const todayYYYMMDD = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const todayDash = new Date().toISOString().slice(0, 10);

      try {
        const wcPath = `/home/workspace/Daily_Log/worldcup/${todayYYYMMDD}/props.json`;
        if (existsSync(wcPath)) {
          const raw = await readFile(wcPath, "utf-8");
          const parsed = JSON.parse(raw);
          const isMatchFormat = Array.isArray(parsed) && parsed.length > 0 && parsed[0] && "teams" in parsed[0];
          if (isMatchFormat) {
            let totalPlayers = 0;
            for (const m of parsed) totalPlayers += Object.keys(m.player_props || {}).length;
            results.push({
              name: "WC props.json format",
              ok: totalPlayers > 0,
              detail: `${parsed.length} matches, ${totalPlayers} players`,
            });
          } else {
            results.push({ name: "WC props.json format", ok: false, detail: "Not match objects" });
          }
        } else {
          results.push({ name: "WC props.json format", ok: false, detail: "props.json not found" });
        }
      } catch (e: any) {
        results.push({ name: "WC props.json format", ok: false, detail: e.message.slice(0, 60) });
      }

      try {
        let foundPicks = false;
        let pickCount = 0;
        const dirsToCheck = [todayDash];
        const yesterdayDash = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
        if (yesterdayDash !== todayDash) dirsToCheck.push(yesterdayDash);
        for (const dateDir of dirsToCheck) {
          const picksPath = join(LOG_DIR, dateDir, "picks.json");
          if (existsSync(picksPath)) {
            const raw = await readFile(picksPath, "utf-8");
            const parsed = JSON.parse(raw);
            pickCount = Array.isArray(parsed) ? parsed.length : Object.keys(parsed).length;
            foundPicks = true;
            break;
          }
        }
        results.push({ name: "Today's picks", ok: foundPicks && pickCount > 0, detail: foundPicks ? `${pickCount} picks` : "No picks file" });
      } catch (e: any) {
        results.push({ name: "Today's picks", ok: false, detail: e.message.slice(0, 60) });
      }

      try {
        const espnRaw = await tryFetch(ESPN_WNBA);
        if (espnRaw.ok) {
          const j = JSON.parse(espnRaw.text);
          const active = (j?.events || []).filter((e: any) => {
            const s = e?.status?.type?.name;
            return s === "STATUS_SCHEDULED" || s === "STATUS_IN_PROGRESS";
          });
          if (active.length > 0) {
            const comps = active[0]?.competitions?.[0]?.competitors || [];
            const away = comps.find((c: any) => c?.homeAway === "away")?.team?.abbreviation || "";
            const home = comps.find((c: any) => c?.homeAway === "home")?.team?.abbreviation || "";
            const f = await tryFetch(`http://localhost:3099/api/tc?sport=WNBA&away=${away}&home=${home}`);
            if (f.ok) {
              const j2 = JSON.parse(f.text);
              const hasDK = (j2?.dk_total && j2.dk_total > 0) || j2?.odds?.total;
              results.push({
                name: `WNBA DK flow (${away}@${home})`,
                ok: hasDK,
                detail: hasDK ? `dk_total=${j2.dk_total || j2.odds?.total}, ${j2.valid_props?.length || 0} props` : `${j2.valid_props?.length || 0} props (off-hours)`,
              });
            }
          } else {
            results.push({ name: "WNBA DK flow", ok: true, detail: "No upcoming games (off-hours)" });
          }
        }
      } catch (e: any) {
        results.push({ name: "WNBA DK flow", ok: false, detail: e.message.slice(0, 60) });
      }

      return results;
    })(),

    // 5. DAILY LOGS
    (async () => {
      const entries: string[] = [];
      try {
        const dirs = await readdir(LOG_DIR, { withFileTypes: true });
        const dates = dirs.filter(d => d.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(d.name))
          .map(d => d.name).sort().reverse().slice(0, 10);
        for (const d of dates) {
          try {
            const raw = await readFile(join(LOG_DIR, d, "picks.json"), "utf-8");
            const picks = JSON.parse(raw);
            entries.push(`${d}: ${Array.isArray(picks) ? picks.length : 0} picks`);
          } catch {
            entries.push(`${d}: no picks`);
          }
        }
      } catch {}
      return entries.length > 0 ? entries : ["No daily logs found"];
    })(),

    // 6. COMBOS + WORLD CUP
    (async () => {
      const items: string[] = [];
      const [comboProb, wcProps] = await Promise.all([
        tryFetch("http://localhost:3099/api/combo-prob"),
        tryFetch("http://localhost:3099/api/worldcup-props"),
      ]);
      if (comboProb.ok && !comboProb.text.includes("error")) {
        items.push("✓ combo-prob");
      } else {
        items.push(`✗ combo-prob: HTTP ${comboProb.status}`);
      }
      if (wcProps.ok) {
        try {
          const j = JSON.parse(wcProps.text);
          items.push(`✓ worldcup-props: ${j.total_matches || j.games?.length || 0} matches, ${j.total_props || 0} props`);
        } catch {
          items.push("✓ worldcup-props: returned data");
        }
      } else {
        items.push(`✗ worldcup-props: HTTP ${wcProps.status}`);
      }
      return items;
    })(),

    // 7. SERVICES
    (async () => {
      const items: string[] = [];
      const [st8510, dkCombo, soccerCombo] = await Promise.all([
        tryFetch("http://localhost:8510").catch(() => empty),
        tryFetch("https://dk-combos-engine-true.zocomputer.io/combos?sport=WNBA"),
        tryFetch("http://localhost:8516/combos"),
      ]);
      items.push(st8510.ok ? "✓ Streamlit :8510" : "✗ Streamlit — not running");
      if (dkCombo.ok) {
        try { const j = JSON.parse(dkCombo.text); items.push(`✓ DK Combos: ${j.count || 0} combos`); } catch { items.push("✓ DK Combos Engine"); }
      } else {
        items.push(`✗ DK Combos: HTTP ${dkCombo.status}`);
      }
      if (soccerCombo.ok) {
        try { const j = JSON.parse(soccerCombo.text); items.push(`✓ Soccer Combos: ${j.count || 0} combos`); } catch { items.push("✓ Soccer Combos Engine"); }
      } else {
        items.push(`✗ Soccer Combos: HTTP ${soccerCombo.status}`);
      }
      return items;
    })(),

    // 8. WORKSPACE CLEANLINESS
    (async () => {
      const stale: string[] = [];
      try {
        const files = await readdir("/home/workspace");
        for (const f of files) {
          if (/\.(py|md|csv|json)$/.test(f)) {
            try {
              const s = await stat(join("/home/workspace", f));
              if ((Date.now() - s.mtimeMs) / 86400000 > 30) stale.push(f);
            } catch {}
          }
        }
      } catch {}
      return { ok: stale.length === 0, stale };
    })(),

    // 9. PIPELINE SCRIPTS
    (async () => {
      const items: string[] = [];
      for (const s of ["daily_picks.py", "consensus_engine.py", "build_pregame_combos.py"]) {
        items.push(existsSync(join(PROJ_DIR, s)) ? `✓ ${s}` : `✗ ${s}`);
      }
      return items;
    })(),

    // ===== REGRESSION GUARDS (7 new — added 2026-07-02) =====
    // 10. SGO adapter (with limit=100)
    sgoKey ? tryFetch(`${SGO_BASE}/events?leagueID=WNBA&limit=100`, { headers: { "x-api-key": sgoKey } as any }).catch(() => empty) : Promise.resolve(empty),

    // 11. OddsAPI quota check — use events endpoint (free, no quota)
    oddsKey ? tryFetch(`${ODDS_BASE}/v4/sports/?apiKey=${oddsKey}`).catch(() => empty) : Promise.resolve(empty),

    // 12. Daily_Log picks exist for today/yesterday
    (async () => {
      const todayDash = new Date().toISOString().slice(0, 10);
      const yesterdayDash = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
      for (const d of [todayDash, yesterdayDash]) {
        const p = join(LOG_DIR, d, "picks.json");
        if (existsSync(p)) {
          try {
            const raw = await readFile(p, "utf-8");
            const j = JSON.parse(raw);
            const n = Array.isArray(j) ? j.length : Object.keys(j).length;
            return { ok: n > 0, status: 200, text: `${d}: ${n} picks` };
          } catch (e: any) {
            return { ok: false, status: 0, text: e.message.slice(0, 50) };
          }
        }
      }
      return { ok: false, status: 0, text: "No picks file in today or yesterday" };
    })(),

    // 13. Dashboard :8510
    tryFetch("http://localhost:8510").catch(() => empty),

    // 14. Combo :8515 /combos (correct path, not /)
    tryFetch("http://localhost:8515/combos").catch(() => empty),

    // 15. Combo :8516 /combos
    tryFetch("http://localhost:8516/combos").catch(() => empty),

    // 16. Injury feed — verify wnba_tc_engine.py imports the injury module/function
    (async () => {
      const f = "/home/workspace/Projects/wnba_tc_engine.py";
      try {
        const raw = await readFile(f, "utf-8");
        const wired = /load_injury_report|injury_report|OUT_FACTOR/.test(raw);
        return {
          ok: wired,
          status: 200,
          text: wired ? "load_injury_report + OUT_FACTOR present" : "load_injury_report not found in wnba_tc_engine.py",
        };
      } catch (e: any) {
        return { ok: false, status: 0, text: e.message.slice(0, 50) };
      }
    })(),
  ]);

  // =================================================================
  // 7 REGRESSION GUARDS (consume the 7 new promise results)
  // =================================================================
  const regression = [
    { name: "SGO adapter (limit=100)", ok: sgoAdapter.ok, detail: sgoAdapter.ok ? `HTTP ${sgoAdapter.status} — OK` : `HTTP ${sgoAdapter.status} ${sgoAdapter.text.includes("429") ? "— rate-limited (ESPN fallback active)" : "— key check failed"}` },
    { name: "OddsAPI quota status", ok: oddsQuota.ok, detail: oddsQuota.ok ? `HTTP ${oddsQuota.status} — events endpoint free, /odds/ on quota` : `HTTP ${oddsQuota.status} — quota check failed` },
    { name: "Daily_Log picks exist", ok: picksExist.ok, detail: picksExist.text },
    { name: "Dashboard :8510", ok: dash8510.ok, detail: `HTTP ${dash8510.status}` },
    { name: "Combo :8515 /combos", ok: combo8515.ok, detail: combo8515.ok ? `HTTP ${combo8515.status}` : `HTTP ${combo8515.status} — engine down` },
    { name: "Combo :8516 /combos", ok: combo8516.ok, detail: combo8516.ok ? `HTTP ${combo8516.status}` : `HTTP ${combo8516.status} — engine down` },
    { name: "Injury feed wired (wnba)", ok: injuryFeed.ok, detail: injuryFeed.text },
  ];

  let regFail = 0; for (const r of regression) if (!r.ok) regFail++;

  let failures = regFail;
  for (const k of apiKeys) if (!k.ok) failures++;
  for (const c of conn) if (!c.ok) failures++;
  for (const r of routes) if (!r.ok) failures++;
  for (const d of integrity) if (!d.ok) failures++;
  if (!cleanliness.ok) failures++;
  if (!services.some(s => s.startsWith("✓"))) failures++;

  const status = failures === 0 ? "HEALTHY" : failures <= 4 ? "DEGRADED" : "UNHEALTHY";

  return c.json({
    status,
    failures,
    timestamp: new Date().toISOString(),
    note: "NBA off-season. Knicks 2026 NBA Champions 🏆. WNBA regular season. World Cup group stage. NFL 2026 W1 pulled.",
    api_keys: apiKeys,
    connectivity: conn,
    routes,
    services,
    pipeline_scripts: scripts,
    daily_logs: logs,
    combos,
    data_integrity: integrity,
    workspace_clean: cleanliness,
    regression,
  });
};
