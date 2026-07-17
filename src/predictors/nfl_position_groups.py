import random
from typing import Dict, List, Optional

class NFLPositionGroups:
    POSITIONS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K", "P", "ST"]

    def project_position_group(self, position: str, opponent: str = None) -> List[Dict]:
        if position not in self.POSITIONS:
            return []
        base_proj = {
            "QB": 20.0, "RB": 15.0, "WR": 12.0, "TE": 8.0,
            "OL": 5.0, "DL": 4.0, "LB": 6.0, "DB": 3.0,
            "K": 2.0, "P": 1.5, "ST": 1.0
        }
        return [{"position": position, "projection": base_proj.get(position, 5.0) + random.uniform(-2, 2)}]

    def project_all_groups(self, opponent: str = None) -> Dict:
        return {pos: self.project_position_group(pos, opponent) for pos in self.POSITIONS}

def project_nfl_position_groups(opponent: str = None) -> Dict:
    return NFLPositionGroups().project_all_groups(opponent)
