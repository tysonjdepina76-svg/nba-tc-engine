#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""Fantasy image generator — CLI wrapper around tc-sports-app fantasy_images.

Reads the latest Daily_Log picks and writes PNG cards/roundups to
/home/workspace/reports/images/.

    python3 Projects/fantasy_images.py [--sport WNBA] [--roundup] [--player "A'ja Wilson"]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

WORKSPACE = Path("/home/workspace")
GEN_PATH = WORKSPACE / "tc-sports-app" / "src" / "domain" / "fantasy_images.py"
ENT_PATH = WORKSPACE / "tc-sports-app" / "src" / "domain" / "entities.py"
OUT_DIR = WORKSPACE / "reports" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = WORKSPACE / "Daily_Log"
ET = timezone(timedelta(hours=-4))


def _load_entities():
    spec = importlib.util.spec_from_file_location("entities_mod", str(ENT_PATH))
    if not spec or not spec.loader:
        raise ImportError(f"Could not load entities from {ENT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Player, mod.Projection


def _load_generator_module():
    """Load FantasyImageGenerator from tc-sports-app and patch src imports."""
    src_root = WORKSPACE / "tc-sports-app"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    spec = importlib.util.spec_from_file_location("fantasy_mod", str(GEN_PATH))
    if not spec or not spec.loader:
        raise ImportError(f"Could not load generator from {GEN_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "FantasyImageGenerator"):
        class _StubGen:
            def __init__(self, *a, **kw): pass
            def generate_player_card(self, *a, **kw): return None
            def generate_roundup(self, *a, **kw): return None
            def generate_weekly_roundup(self, *a, **kw): return None
            def generate(self, *a, **kw): return None
        mod.FantasyImageGenerator = _StubGen
    return mod


def _latest_picks_df() -> pd.DataFrame | None:
    """Combine today's picks.csv + World Cup picks.csv into one DataFrame."""
    today = datetime.now(ET).strftime("%Y-%m-%d")
    frames: list[pd.DataFrame] = []

    # Primary: today's picks.csv
    daily_csv = LOG_DIR / today / "picks.csv"
    used_today = False
    if daily_csv.exists():
        try:
            df = pd.read_csv(daily_csv)
            if len(df):
                if "league" not in df.columns:
                    df["league"] = ""
                frames.append(df)
                used_today = True
        except Exception:
            pass

    # Fallback: if today's dir is empty, walk backward up to 7 days.
    # This matters during off-hours (WNBA off-day, MLB day game already
    # finished, etc.) so the image generator still produces cards.
    if not used_today:
        from datetime import timedelta
        for delta in range(1, 8):
            past = (datetime.now(ET) - timedelta(days=delta)).strftime("%Y-%m-%d")
            past_csv = LOG_DIR / past / "picks.csv"
            if past_csv.exists():
                try:
                    df = pd.read_csv(past_csv)
                    if len(df):
                        if "league" not in df.columns:
                            df["league"] = ""
                        df["_fallback_date"] = past
                        frames.append(df)
                        break
                except Exception:
                    continue

    wc_dir = LOG_DIR / "worldcup" / datetime.now(ET).strftime("%Y%m%d")
    wc_csv = wc_dir / "picks.csv"
    if wc_csv.exists():
        try:
            df = pd.read_csv(wc_csv)
            if len(df):
                df["league"] = "WORLD CUP"
                # WC rows: no team col
                frames.append(df)
        except Exception:
            pass

    if not frames:
        return None
    return pd.concat(frames, ignore_index=True, sort=False)


def _row_to_player_proj(row, Player, Projection):
    name = str(row.get("player", "Unknown"))
    # Prefer explicit team column; fall back gracefully instead of copying
    # the home team (Brazilian players were being tagged "Japan").
    team = (str(row.get("team") or "").strip()) or "FWC"
    # If team is still empty after str
    role = str(row.get("role") or "UTIL")
    stat = str(row.get("stat") or "points")
    line_val = row.get("market_line", row.get("line"))
    try:
        line_f = float(line_val) if pd.notna(line_val) else 0.0
    except Exception:
        line_f = 0.0

    tc_proj = row.get("tc_projection")
    if pd.isna(tc_proj) or tc_proj in (None, ""):
        tc_proj = round(line_f * 1.12, 1) if line_f else 0.0
    else:
        tc_proj = float(tc_proj)

    edge = row.get("edge")
    if pd.isna(edge) or edge in (None, ""):
        edge = round(tc_proj - line_f, 1)
    else:
        edge = float(edge)

    direction = str(row.get("direction") or ("OVER" if edge > 0 else "UNDER"))

    return Player(name=name, team=team, position=role, role=role), Projection(
        player=name, team=team, role=role, stat=stat,
        status=str(row.get("status") or "ACTIVE"),
        tc_projection=tc_proj, line=line_f, edge=edge,
        direction=direction, valid=True,
    )


def make_cards(sport: str | None, player_filter: str | None, max_n: int = 10, matchup: str | None = None, outdir: str | None = None):
    Player, Projection = _load_entities()
    gen_mod = _load_generator_module()

    df = _latest_picks_df()
    if df is None or df.empty:
        return [], "No picks available — run daily_picks.py first"

    if matchup and "matchup" in df.columns:
        _mn = re.sub(r"\s+", "", matchup.upper())
        df = df[df["matchup"].astype(str).str.upper().str.replace(r"\s+", "", regex=True) == _mn]
    if sport:
        if "league" in df.columns:
            target = sport.upper().replace("_", " ")
            df = df[df["league"].astype(str).str.upper().str.replace("_", " ", regex=False) == target]
        elif "matchup" in df.columns:
            target = "WORLD CUP" if sport.upper() in ("WORLD_CUP", "SOCCER", "WC") else sport
            df = df[df["matchup"].astype(str).str.contains(target, case=False, na=False)]
    if player_filter and "player" in df.columns:
        df = df[df["player"].astype(str).str.contains(player_filter, case=False, na=False)]

    df = df.head(max_n)
    if df.empty:
        return [], "No rows matched filter"

    _gen_save_dir = Path(outdir) if outdir else OUT_DIR
    _gen_save_dir.mkdir(parents=True, exist_ok=True)
    class _SubGen(gen_mod.FantasyImageGenerator):
        pass
    gen = _SubGen(sport=(sport or "ALL"), cache_dir="/tmp/tc_image_cache")
    # Override output dir by monkey-patching pathlib mkdir: simpler — patch the module's OUT_DIR isn't possible,
    # so we wrap generate_* to move files into outdir after save.
    _orig_card = gen.generate_player_card
    _orig_round = gen.generate_weekly_roundup
    def _card_re(player, projection, width=400, height=650):
        p = _orig_card(player, projection, width, height)
        import shutil
        new_p = _gen_save_dir / Path(p).name
        shutil.move(str(p), str(new_p))
        return str(new_p)
    def _round_re(projections, top_n=10):
        p = _orig_round(projections, top_n)
        import shutil
        new_p = _gen_save_dir / Path(p).name
        shutil.move(str(p), str(new_p))
        return str(new_p)
    gen.generate_player_card = _card_re
    gen.generate_weekly_roundup = _round_re
    results = []
    for _, row in df.iterrows():
        try:
            player, proj = _row_to_player_proj(row, Player, Projection)
            path = gen.generate_player_card(player, proj)
            results.append({
                "player": player.name, "team": player.team,
                "path": path, "tc_projection": proj.tc_projection,
                "edge": proj.edge, "direction": proj.direction,
            })
        except Exception as e:
            results.append({"player": str(row.get("player", "?")), "error": str(e)})
    return results, None


def make_roundup(sport: str | None, max_n: int = 10, matchup: str | None = None, outdir: str | None = None):
    Player, Projection = _load_entities()
    gen_mod = _load_generator_module()

    df = _latest_picks_df()
    if df is None or df.empty:
        return None, "No picks available — run daily_picks.py first"

    if matchup and "matchup" in df.columns:
        _mn = re.sub(r"\s+", "", matchup.upper())
        df = df[df["matchup"].astype(str).str.upper().str.replace(r"\s+", "", regex=True) == _mn]
    if sport:
        if "league" in df.columns:
            target = sport.upper().replace("_", " ")
            df = df[df["league"].astype(str).str.upper().str.replace("_", " ", regex=False) == target]
        elif "matchup" in df.columns:
            target = "WORLD CUP" if sport.upper() in ("WORLD_CUP", "SOCCER", "WC") else sport
            df = df[df["matchup"].astype(str).str.contains(target, case=False, na=False)]
    df = df.head(max_n)
    if df.empty:
        return None, "No rows matched filter"

    projections = []
    for _, row in df.iterrows():
        _, proj = _row_to_player_proj(row, Player, Projection)
        projections.append(proj)
    gen = gen_mod.FantasyImageGenerator(
        sport=(sport or "ALL"), cache_dir="/tmp/tc_image_cache"
    )
    path = gen.generate_weekly_roundup(projections, top_n=max_n)
    return path, None


def main():
    p = argparse.ArgumentParser(description="Generate fantasy PNG cards from TC picks")
    p.add_argument("--sport", help="Filter by sport: NBA, WNBA, NFL, MLB, NHL, WORLD_CUP (or SOCCER). Future: TENNIS, GOLF, CFB, CBB")
    p.add_argument("--player", help="Filter by player name substring")
    p.add_argument("--max", type=int, default=5, help="Max cards to generate")
    p.add_argument("--roundup", action="store_true", help="Generate a weekly roundup card")
    p.add_argument("--outdir", default=None, help="Override output directory")
    p.add_argument("--matchup", help="Filter by matchup (e.g. JPN@BRA)")
    p.add_argument("--out-json", default=None, help="Write results to JSON file")
    args = p.parse_args()

    if args.roundup:
        path, err = make_roundup(args.sport, args.max, matchup=args.matchup, outdir=args.outdir)
        if err:
            print(json.dumps({"error": err}))
            return
        print(json.dumps({"roundup": path, "sport": args.sport}))
        return

    results, err = make_cards(args.sport, args.player, args.max, matchup=args.matchup, outdir=args.outdir)
    if err:
        print(json.dumps({"error": err}))
        return
    payload = {"generated": len(results), "sport": args.sport, "cards": results}
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
