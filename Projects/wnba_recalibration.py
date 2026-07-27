# WNBA Recalibration Module
# Applies backtest-driven adjustments to WNBA self-edge picks
# Calibrated from 7/19 backtest: 84 picks, 60.7% hit rate

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================
# BACKTEST CALIBRATION DATA (7/19/2026)
# ============================================================

# Stat hit rates from 84-pick backtest
STAT_HIT_RATES = {
    "PTS": 66.7,
    "P+R": 66.7,
    "P+A": 57.1,
    "P+R+A": 52.4,
    "AST": 64.3,
    "REB": 64.3,
    "BLK": 64.3,
    "STL": 57.1,
}

# Stat weight multipliers (higher = more confidence in signal)
STAT_WEIGHTS = {
    "PTS": 1.5,
    "P+R": 1.3,
    "P+A": 0.7,
    "P+R+A": 0.4,
    "AST": 1.0,
    "REB": 1.0,
    "BLK": 1.0,
    "STL": 0.8,
}

# Players with 0% hit rate across all their picks — BLACKLIST
PLAYER_BLACKLIST = {
    "Allisha Gray",
    "Brittney Griner",
    "DeWanna Bonner",
    "Kahleah Copper",
    "Arike Ogunbowale",
    "Azura Stevens",
    "Dearica Hamby",
}

# Players with 100% hit rate — preferred (boost)
PLAYER_BOOST = {
    "Cheyenne Parker",
    "Diamond DeShields",
    "Brionna Jones",
    "Diana Taurasi",
    "Marina Mabrey",
    "Kelsey Plum",
    "Lexie Brown",
    "Natasha Howard",
    "Satou Sabally",
    "Skylar Diggins-Smith",
    "Teaira McCowan",
}

# Minimum weighted edge to output a pick (filters noise)
CONVICTION_THRESHOLD = 0.35

# Stats to drop completely (below break-even 52.4%)
DROPPED_STATS = {"P+R+A"}

# Direction diversity: if all picks are same direction, flip weakest edges
DIRECTION_DIVERSITY_ENABLED = True


def calibrate_wnba_picks(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply recalibration to WNBA self-edge picks.
    
    Steps:
    1. Drop P+R+A (52.4% hit rate = coin flip)
    2. Blacklist 0% players
    3. Apply stat weights to edge
    4. Filter below conviction threshold
    5. Boost 100% players
    6. Enforce direction diversity (prevent all-UNDER)
    """
    if not picks:
        logger.info("[CALIBRATE] No WNBA picks to calibrate")
        return picks

    filtered = []
    stat_counts = {}
    direction_counts = {"OVER": 0, "UNDER": 0}
    
    for p in picks:
        stat = p.get("stat", "")
        name = p.get("name", p.get("player", ""))
        edge = p.get("edge", 0)
        
        # Step 1: Drop P+R+A
        if stat in DROPPED_STATS:
            logger.debug(f"[CALIBRATE] DROP {name} {stat}: stat below break-even")
            continue
        
        # Step 2: Blacklist 0% players
        if name in PLAYER_BLACKLIST:
            logger.debug(f"[CALIBRATE] DROP {name} {stat}: blacklisted (0% hit rate)")
            continue

        # Step 2b: PTS is broken — require 2x edge threshold (backtest: 36.8% hit rate)
        if stat == "PTS":
            if abs(edge) < 0.20:
                logger.debug(f"[CALIBRATE] DROP {name} PTS: edge {abs(edge):.3f} < 0.20 PTS threshold")
                continue

        # Step 2c: OVERs are toxic — require 1.7x edge threshold (backtest: 25.6% hit rate)
        if p.get("direction") == "OVER":
            if abs(edge) < 0.12:
                logger.debug(f"[CALIBRATE] DROP {name} {stat}: OVER edge {abs(edge):.3f} < 0.12 OVER threshold")
                continue
        
        # Step 3: Apply stat weight
        weight = STAT_WEIGHTS.get(stat, 1.0)
        weighted_edge = abs(edge) * weight
        
        # Step 4: Conviction filter
        if weighted_edge < CONVICTION_THRESHOLD:
            logger.debug(f"[CALIBRATE] DROP {name} {stat}: edge {weighted_edge:.1f} < threshold {CONVICTION_THRESHOLD}")
            continue
        
        # Step 5: Boost 100% players
        if name in PLAYER_BOOST:
            weighted_edge *= 1.1  # 10% boost
            p["reason"] = (p.get("reason", "") + " [BOOST: 100% player]").strip()
        
        # Apply calibrated edge
        p["edge"] = round(weighted_edge, 2)
        p["reason"] = (p.get("reason", "") + f" [WT:{weight}]").strip()
        
        filtered.append(p)
        stat_counts[stat] = stat_counts.get(stat, 0) + 1
        direction_counts[p.get("direction", "UNDER")] += 1
    
    # Step 6: Direction diversity — if all picks same direction, flip weakest
    if DIRECTION_DIVERSITY_ENABLED and filtered:
        over_count = direction_counts["OVER"]
        under_count = direction_counts["UNDER"]
        total = over_count + under_count
        
        if total > 0:
            pct_over = 100.0 * over_count / total if over_count > 0 else 0
            pct_under = 100.0 * under_count / total if under_count > 0 else 0
            
            # If >90% one direction, flip the weakest 20% of picks from the dominant direction
            if pct_under > 90 and under_count >= 5 and over_count == 0:
                # Sort UNDER picks by edge (weakest first)
                under_picks = [p for p in filtered if p.get("direction") == "UNDER"]
                under_picks.sort(key=lambda x: abs(x.get("edge", 0)))
                
                flip_count = max(1, int(len(under_picks) * 0.2))
                for i in range(flip_count):
                    under_picks[i]["direction"] = "OVER"
                    under_picks[i]["reason"] = under_picks[i].get("reason", "") + " [DIV: flipped to OVER]"
                    logger.info(f"[CALIBRATE] DIVR: flipped {under_picks[i].get('name')} {under_picks[i].get('stat')} to OVER")
            
            elif pct_over > 90 and over_count >= 5 and under_count == 0:
                over_picks = [p for p in filtered if p.get("direction") == "OVER"]
                over_picks.sort(key=lambda x: abs(x.get("edge", 0)))
                
                flip_count = max(1, int(len(over_picks) * 0.2))
                for i in range(flip_count):
                    over_picks[i]["direction"] = "UNDER"
                    over_picks[i]["reason"] = over_picks[i].get("reason", "") + " [DIV: flipped to UNDER]"
                    logger.info(f"[CALIBRATE] DIVR: flipped {over_picks[i].get('name')} {over_picks[i].get('stat')} to UNDER")
    
    logger.info(
        f"[CALIBRATE] WNBA: {len(picks)} -> {len(filtered)} picks "
        f"({', '.join('{}:{}'.format(k,v) for k,v in sorted(stat_counts.items()))}) "
        f"DIR: O{sum(1 for p in filtered if p.get('direction')=='OVER')}/U{sum(1 for p in filtered if p.get('direction')=='UNDER')}"
    )
    
    return filtered


def get_wnba_calibration_summary() -> Dict[str, Any]:
    """Return calibration metadata for reporting."""
    return {
        "source": "7/19 backtest (84 picks, 60.7% hit rate)",
        "stat_weights": STAT_WEIGHTS,
        "dropped_stats": list(DROPPED_STATS),
        "blacklisted_players": sorted(PLAYER_BLACKLIST),
        "boosted_players": sorted(PLAYER_BOOST),
        "conviction_threshold": CONVICTION_THRESHOLD,
        "direction_diversity": DIRECTION_DIVERSITY_ENABLED,
    }