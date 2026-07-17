from datetime import datetime
from typing import Dict, List, Callable, Any
from src.utils.logging import get_logger

logger = get_logger(__name__)

class PipelineStage:
    def __init__(self, name: str, func: Callable, dependencies: List[str] = None):
        self.name = name
        self.func = func
        self.dependencies = dependencies or []
        self.completed = False
        self.result = None
        self.error = None

class PipelineOrchestrator:
    def __init__(self):
        self.stages: Dict[str, PipelineStage] = {}
        self.results: Dict[str, Any] = {}

    def add_stage(self, name: str, func: Callable, dependencies: List[str] = None) -> None:
        self.stages[name] = PipelineStage(name, func, dependencies)

    def run(self) -> Dict[str, Any]:
        for name, stage in self.stages.items():
            logger.info(f"Running stage: {name}")
            try:
                stage.result = stage.func()
                stage.completed = True
                self.results[name] = stage.result
            except Exception as e:
                stage.error = str(e)
                return {"status": "failed", "stage": name, "error": str(e)}
        return {"status": "complete", "stages": len(self.stages), "results": self.results}

def build_daily_pipeline(sport: str):
    from src.adapters.line_fetcher import fetch_lines
    from src.adapters.live_scraper import fetch_live_games
    from daily_picks import generate_picks

    orchestrator = PipelineOrchestrator()
    orchestrator.add_stage("fetch_lines", lambda: fetch_lines(sport))
    orchestrator.add_stage("fetch_live", lambda: fetch_live_games(sport))
    orchestrator.add_stage("generate_picks", lambda: generate_picks(sport), dependencies=["fetch_lines", "fetch_live"])
    return orchestrator
