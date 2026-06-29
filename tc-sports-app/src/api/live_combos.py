from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.domain.combo_qualifier import ComboQualifier, aggregate_lines
from src.domain.entities import Projection as _ProjectionEntity
from src.domain.daily_picks import DailyPicks

app = FastAPI(title="TC Sports Live Combos API")


def _attach_market_lines(projections, sport: str, date: str):
    """Re-compute edge against SGO DK lines when available.

    For each projection we look up (player, stat) in SGO's player_props feed
    (the canonical DK source) and, if found, replace self-edge with the
    market edge: tc_projection − market_line. Sets direction appropriately.

    Returns (projections_with_market, line_lookup_stats) so the caller can
    surface diagnostics in the response.
    """
    try:
        from src.domain.market_line_provider import MarketLinesProvider
    except Exception as e:
        return projections, {"provider_available": False, "error": str(e)}

    try:
        provider = MarketLinesProvider(sport=sport, date=date)
    except Exception as e:
        return projections, {"provider_available": True, "fetched_rows": 0, "error": str(e)}

    rows = provider.fetch_lines()
    if not rows:
        return projections, {"provider_available": True, "fetched_rows": 0, "attached": 0}

    lookup = {(r["player"], r["stat"]): r for r in rows}

    attached = 0
    for p in projections:
        row = lookup.get((p.player, p.stat))
        if row is None:
            continue
        p.market_line = row["line"]
        p.market_source = row.get("source", "SGO")
        p.market_agreement = row.get("agreement")
        # Re-compute edge against market line.
        market_edge = p.tc_projection - row["line"]
        # If market disagrees with self-direction, downgrade validity.
        same_dir = (market_edge > 0 and p.direction == "OVER") or \
                   (market_edge < 0 and p.direction == "UNDER")
        if abs(market_edge) > 0:
            # Only override when market edge meets threshold.
            if abs(market_edge) >= 1.0:
                p.edge = round(market_edge, 2)
                p.direction = "OVER" if market_edge > 0 else "UNDER"
        p.valid = bool(p.valid) and same_dir
        attached += 1

    return projections, {"provider_available": True, "fetched_rows": len(rows), "attached": attached}


@app.get("/live-combos")
def get_live_combos(
    sport: str = Query("NBA"),
    date: str = Query(datetime.now().strftime("%Y-%m-%d")),
    min_edge: float = Query(1.5),
    min_conf: float = Query(0.6),
    min_corr: float = Query(0.3),
    min_hit: float = Query(0.5),
    max_legs: int = Query(4),
    min_legs: int = Query(2),
):
    sport = sport.upper()
    projections = []
    proj_error = None

    try:
        dp = DailyPicks(sport, date)
        projections = dp.run()
        # dp.run() returns raw matchup dicts (not Projection entities). Rebuild as entities.
        projections = _matchup_dicts_to_projections(projections)
    except Exception as e:
        proj_error = str(e)

    seeded = False
    if not projections:
        seed_path = Path(__file__).resolve().parents[2] / "data" / "seeded_combos.json"
        try:
            raw = json.loads(seed_path.read_text())
            sport_proj = raw.get("projections", {}).get(sport, [])
            if sport_proj:
                projections = [_projection_from_seed(p) for p in sport_proj]
                seeded = bool(projections)
                if proj_error:
                    proj_error = f"{proj_error} | using seeded data"
                else:
                    proj_error = "no live projections — using seeded test data"
        except Exception as e:
            proj_error = f"{proj_error or 'no projections'} | seed load failed: {e}"

    # Always attempt to fetch market lines so the response shows provider status,
    # even when running on seeded projections (which can't be enriched).
    line_stats = None
    projections, line_stats = _attach_market_lines(projections, sport, date)
    line_stats = line_stats  # alias for readability

    qualifier = ComboQualifier(sport)
    combos, report = qualifier.qualify(projections)

    return {
        "sport": sport,
        "date": date,
        "thresholds": {
            "min_edge": min_edge,
            "min_conf": min_conf,
            "min_corr": min_corr,
            "min_hit": min_hit,
            "max_legs": max_legs,
            "min_legs": min_legs,
        },
        "combo_count": len(combos),
        "combos": [c.to_dict() for c in combos],
        "filter_report": report.to_dict(),
        "projection_error": proj_error,
        "seeded": seeded,
        "market_lines": line_stats,
        "timestamp": datetime.now().isoformat(),
    }


def _matchup_dicts_to_projections(matchup_results):
    """Convert daily_picks matchup dicts -> Projection entities for qualifier."""
    out = []
    for r in matchup_results:
        game_id = r.get("matchup", "unknown")
        for prop in r.get("valid_props", []):
            try:
                out.append(_ProjectionEntity(
                    player=prop.get("player", ""),
                    team=prop.get("team", ""),
                    role=prop.get("role", "BENCH"),
                    status=prop.get("status", "ACTIVE"),
                    stat=prop.get("stat", ""),
                    tc_projection=float(prop.get("tc_projection", 0)),
                    line=float(prop.get("line", 0)),
                    edge=float(prop.get("edge", 0)),
                    direction=prop.get("direction", "OVER"),
                    valid=bool(prop.get("valid", True)),
                ))
            except Exception:
                continue
    return out


def _projection_from_seed(d: dict):
    return _ProjectionEntity(
        player=d["player"], team=d["team"], role=d.get("role", "G"),
        status=d.get("status", "ACTIVE"), stat=d["stat"],
        tc_projection=d["tc_projection"], line=d["line"],
        edge=d["edge"], direction=d["direction"], valid=d.get("valid", True),
        market_line=d.get("market_line"),
        market_source=d.get("market_source"),
        market_agreement=d.get("market_agreement"),
    )


def _avg_corr(legs: list) -> float:
    if not legs:
        return 0.0
    return 0.4


def get_seeded_combos_for_dashboard(sport: str):
    pass


@app.get("/live-combos/image")
def get_live_combo_image(
    sport: str = Query("NBA"),
    date: str = Query(datetime.now().strftime("%Y-%m-%d")),
):
    from .screenshot import generate_combo_screenshot
    path = generate_combo_screenshot(sport, date)
    return FileResponse(path, media_type="image/png")


@app.get("/live-combos/health")
def health():
    return {"status": "ok", "service": "tc-live-combos", "timestamp": datetime.now().isoformat()}
