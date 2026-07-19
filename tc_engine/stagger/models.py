"""Pydantic Models — request/response schemas for the Stagger API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PickLine(BaseModel):
    player: str
    sport: str
    stat: str
    projection: float
    line: float
    edge: float
    direction: str
    reason: Optional[str] = ""
    matchup: Optional[str] = ""


class PicksResponse(BaseModel):
    picks: list[dict]
    count: int


class SportAccuracy(BaseModel):
    sport: str
    count: int
    hits: int
    hit_rate: float


class AccuracyResponse(BaseModel):
    total_graded: int
    hits: int
    hit_rate: float
    profit: float
    by_sport: list[dict]


class SystemHealth(BaseModel):
    status: str
    sports_enabled: int
    timestamp: str


class PlayerSummary(BaseModel):
    name: str
    PTS: Optional[float] = None
    REB: Optional[float] = None
    AST: Optional[float] = None
    STL: Optional[float] = None
    BLK: Optional[float] = None
    H: Optional[float] = None
    RBI: Optional[float] = None
    HR: Optional[float] = None


class TeamSide(BaseModel):
    name: str
    side: str
    players: list[dict] = []


class Game(BaseModel):
    sport: str
    state: str
    teams: list[dict] = []
    away_score: int = 0
    home_score: int = 0
    period: int = 0
    clock: str = ""


class LiveDashboardResponse(BaseModel):
    games: list[dict]
    total: int
    sport: str
