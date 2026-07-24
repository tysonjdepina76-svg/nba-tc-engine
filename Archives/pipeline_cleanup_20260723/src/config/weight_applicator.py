class WeightApplicator:
    def get_direction_multiplier(self, direction, sport, stat):
        return 1.0

    def apply_weights(self, picks):
        return picks

_APPLICATOR = None

def get_weight_applicator():
    global _APPLICATOR
    if _APPLICATOR is None:
        _APPLICATOR = WeightApplicator()
    return _APPLICATOR
