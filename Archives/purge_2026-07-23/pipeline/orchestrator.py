"""
Pipeline orchestrator — DAG-based execution (from legacy nba_tc_pipeline_v2).
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from sources.sports_registry import REGISTRY
from sources.utils.logging import get_logger

logger = get_logger(__name__)

class PipelineStage:
    """Single pipeline stage with dependencies."""

    def __init__(self, name: str, func: Callable, dependencies: List[str] = None):
        self.name = name
        self.func = func
        self.dependencies = dependencies or []
        self.completed = False
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None


class PipelineOrchestrator:
    """Orchestrate pipeline execution with DAG-based stages."""

    def __init__(self):
        self.stages: Dict[str, PipelineStage] = {}
        self.results: Dict[str, Any] = {}
        self.start_time = None
        self.end_time = None
        self.execution_order: List[str] = []

    def add_stage(self, name: str, func: Callable, dependencies: List[str] = None) -> None:
        """Add a pipeline stage."""
        self.stages[name] = PipelineStage(name, func, dependencies)
        logger.debug(f"Added stage: {name} (deps: {dependencies or 'none'})")

    def _resolve_order(self) -> List[str]:
        """Resolve execution order using topological sort."""
        visited = set()
        order = []
        temp = set()

        def dfs(stage_name: str) -> None:
            if stage_name in temp:
                raise ValueError(f"Circular dependency detected: {stage_name}")
            if stage_name in visited:
                return

            temp.add(stage_name)
            stage = self.stages.get(stage_name)
            if stage:
                for dep in stage.dependencies:
                    if dep not in self.stages:
                        raise ValueError(f"Unknown dependency: {dep} for {stage_name}")
                    dfs(dep)

            temp.remove(stage_name)
            visited.add(stage_name)
            order.append(stage_name)

        for name in self.stages:
            if name not in visited:
                dfs(name)

        return order

    def run(self) -> Dict[str, Any]:
        """Run the pipeline in DAG order."""
        self.start_time = datetime.now()
        logger.info("Starting pipeline execution")

        try:
            self.execution_order = self._resolve_order()
            logger.info(f"Execution order: {self.execution_order}")
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        for stage_name in self.execution_order:
            stage = self.stages[stage_name]
            logger.info(f"Running stage: {stage_name}")

            deps_met = all(
                self.stages.get(dep) and self.stages[dep].completed
                for dep in stage.dependencies
            )
            if not deps_met:
                missing = [d for d in stage.dependencies if not self.stages.get(d) or not self.stages[d].completed]
                logger.error(f"Stage {stage_name} missing dependencies: {missing}")
                stage.error = f"Missing dependencies: {missing}"
                stage.completed = True
                self.results[stage_name] = {"error": stage.error}
                continue

            try:
                stage.start_time = datetime.now()
                stage.result = stage.func()
                stage.completed = True
                stage.end_time = datetime.now()
                self.results[stage_name] = stage.result
                logger.info(f"Stage {stage_name} completed in {(stage.end_time - stage.start_time).total_seconds():.2f}s")
            except Exception as e:
                logger.error(f"Stage {stage_name} failed: {e}")
                stage.error = str(e)
                stage.completed = True
                self.results[stage_name] = {"error": str(e)}
                return {
                    "status": "failed",
                    "stage": stage_name,
                    "error": str(e),
                    "results": self.results,
                    "elapsed_seconds": (datetime.now() - self.start_time).total_seconds()
                }

        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Pipeline complete in {elapsed:.2f}s")

        return {
            "status": "complete",
            "stages": len(self.stages),
            "execution_order": self.execution_order,
            "elapsed_seconds": elapsed,
            "results": self.results,
            "timestamp": datetime.now().isoformat()
        }

    def get_stage_result(self, stage_name: str) -> Optional[Any]:
        return self.results.get(stage_name)

    def get_status(self) -> Dict[str, Any]:
        return {
            "stages": {name: {
                "completed": stage.completed,
                "error": stage.error,
                "result_type": type(stage.result).__name__ if stage.result else None
            } for name, stage in self.stages.items()},
            "execution_order": self.execution_order,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


def run_sport_pipeline(sport: str) -> Dict[str, Any]:
    """Run the full pipeline for a sport."""
    orchestrator = PipelineOrchestrator()

    def fetch_schedule():
        from sources.schedule_fetcher import fetch_schedule_cached
        return fetch_schedule_cached(sport)
    orchestrator.add_stage("fetch_schedule", fetch_schedule)

    def fetch_projections():
        config = REGISTRY.get(sport)
        if config and config.fetcher:
            result = config.fetcher()
            return result or {"players": []}
        return {"players": []}
    orchestrator.add_stage("fetch_projections", fetch_projections, dependencies=["fetch_schedule"])

    def fetch_lines():
        from sources.line_fetcher import fetch_lines
        return fetch_lines(sport)
    orchestrator.add_stage("fetch_lines", fetch_lines, dependencies=["fetch_schedule"])

    def compute_edges():
        projections = orchestrator.get_stage_result("fetch_projections") or {"players": []}
        lines = orchestrator.get_stage_result("fetch_lines") or {"games": []}
        return {
            "projections": projections,
            "lines": lines,
            "merged": True,
            "player_count": len(projections.get("players", []))
        }
    orchestrator.add_stage("compute_edges", compute_edges, dependencies=["fetch_projections", "fetch_lines"])

    def generate_picks():
        from pipeline.daily_picks import generate_daily_picks
        return generate_daily_picks(sport)
    orchestrator.add_stage("generate_picks", generate_picks, dependencies=["compute_edges"])

    return orchestrator.run()


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "mlb"
    result = run_sport_pipeline(sport)
    print(f"Pipeline status: {result.get('status')}")
    print(f"Stages: {len(result.get('results', {}))}")
    for name, res in result.get("results", {}).items():
        print(f"  {name}: {str(res)[:100]}...")
