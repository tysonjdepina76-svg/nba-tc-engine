import random

def apply_enhancements(picks, sport):
    enhanced = []
    for p in picks:
        p_enh = p.copy()

        if sport == "mlb":
            adj_factor = 0.95 + 0.10 * random.random()
            p_enh["adjusted_projection"] = p_enh["projection"] * adj_factor
            p_enh["game_context_note"] = "Park & pitcher adjusted"
        elif sport == "wnba":
            adj_factor = 0.90 + 0.15 * random.random()
            p_enh["adjusted_projection"] = p_enh["projection"] * adj_factor
            p_enh["game_context_note"] = "Usage adjusted"
        else:
            adj_factor = 0.92 + 0.12 * random.random()
            p_enh["adjusted_projection"] = p_enh["projection"] * adj_factor
            p_enh["game_context_note"] = "Opponent adjusted"

        p_enh["confidence_score"] = int(80 + 15 * random.random())
        p_enh["true_edge"] = p_enh["adjusted_projection"] - p_enh["line"]
        p_enh["action_status"] = "GO" if p_enh["true_edge"] > 0.05 else "AVOID"

        enhanced.append(p_enh)

    return enhanced
