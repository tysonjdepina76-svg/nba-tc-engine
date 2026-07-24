"""Live test: train hybrid predictor + produce real prediction."""
import sys
from src.domain.entities import REGISTRY
from src.predictors import HybridWNBAPropPredictor, PlayerFeatures

predictor = REGISTRY.get_predictor()
print(f"trained: {predictor.trained} targets: {list(predictor.xgb_models.keys())}")

class MockPlayer:
    def __init__(self, n): self.name = n

features = PlayerFeatures(
    minutes=33.0, usage_rate=29.5, is_home=1, rest_days=2,
    season_avg_pts=22.5, season_avg_ast=3.1, season_avg_fg3m=1.8,
    recent_5_pts=24.0, recent_5_ast=3.4, recent_5_fg3m=2.0,
    opp_drtg=108.0, opp_3pa_allowed=20.0,
    creation_rate=0.20, spotup_rate=0.18, vs_switching_def=0,
)
player = MockPlayer("A'ja Wilson")

for tgt in ("pts", "ast", "fg3m"):
    r = predictor.predict(player, features, target=tgt)
    print(f"{tgt.upper():4s} median={r.median:5.1f}  p10={r.p10:5.1f}  p90={r.p90:5.1f}  conf={r.confidence:.2f}  tc={r.tc_math_component:5.1f}  ml={r.ml_component:5.1f}")
