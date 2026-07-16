def generate_explanation(player, sport, stat, projection, line, edge):
    if edge is None:
        edge = projection - line if line else 0.0
    if edge > 1.0:
        strength = "strong"
    elif edge > 0.5:
        strength = "moderate"
    else:
        strength = "marginal"
    sport_name = sport.upper() if sport else "Sport"
    stat_name = stat.upper() if stat else "projection"
    return (f"{strength.capitalize()} +EV opportunity: {player} projected for {projection:.1f} "
            f"{stat_name} vs {line:.1f}, edge {edge:.2f}. Based on recent form, opponent defense, and game context.")


def classify_signal(edge):
    if edge is None:
        return "WEAK"
    ae = abs(edge)
    if ae >= 2.0:
        return "STRONG"
    if ae >= 1.0:
        return "MODERATE"
    return "WEAK"
