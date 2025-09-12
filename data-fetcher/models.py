"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class StatsType(str, Enum):
    batting = "batting"
    pitching = "pitching"
    fielding = "fielding"


class FetchType(str, Enum):
    all = "all"
    teams = "teams"
    players = "players"
    games = "games"
    stats = "stats"


class PlayerStatsRequest(BaseModel):
    player_id: str = Field(..., min_length=1, max_length=50)
    season: int = Field(..., ge=1876, le=datetime.now().year + 1)
    stats_type: StatsType = StatsType.batting


class LeaderboardRequest(BaseModel):
    season: int = Field(..., ge=1876, le=datetime.now().year + 1)
    stats_type: StatsType = StatsType.batting
    stat_name: str = Field(default="AVG", max_length=20)
    limit: int = Field(default=50, ge=1, le=500)
    position: Optional[str] = Field(default=None, max_length=10)

    @validator('position')
    def validate_position(cls, v):
        if v is not None:
            valid_positions = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']
            if v not in valid_positions:
                raise ValueError(f'Invalid position. Must be one of: {valid_positions}')
        return v


class CatcherMetricsRequest(BaseModel):
    player_id: str = Field(..., min_length=1, max_length=50)
    season: int = Field(..., ge=1876, le=datetime.now().year + 1)


class OutfielderMetricsRequest(BaseModel):
    player_id: str = Field(..., min_length=1, max_length=50)
    season: int = Field(..., ge=1876, le=datetime.now().year + 1)
    position: str = Field(default="CF", max_length=10)

    @validator('position')
    def validate_position(cls, v):
        if v is not None:
            valid_positions = ['LF', 'CF', 'RF']
            if v not in valid_positions:
                raise ValueError(f'Invalid position. Must be one of: {valid_positions}')
        return v


class CatcherLeaderboardRequest(BaseModel):
    season: int = Field(..., ge=1876, le=datetime.now().year + 1)
    stat_name: str = Field(default="FRAMING_RUNS", max_length=30)
    limit: int = Field(default=25, ge=1, le=100)

    @validator('stat_name')
    def validate_catcher_stat(cls, v):
        valid_stats = [
            'FRAMING_RUNS', 'BLOCKING_RUNS', 'ARM_RUNS',
            'POP_TIME_SECONDS', 'EXCHANGE_TIME_SECONDS',
            'FRAMING_PCT_ABOVE_AVG', 'BLOCKING_PCT_ABOVE_AVG',
            'CS_ABOVE_AVG', 'TOTAL_CATCHER_RUNS'
        ]
        if v not in valid_stats:
            raise ValueError(f'Invalid catcher stat. Must be one of: {valid_stats}')
        return v


class OutfielderLeaderboardRequest(BaseModel):
    season: int = Field(..., ge=1876, le=datetime.now().year + 1)
    position: str = Field(default="CF", max_length=10)
    stat_name: str = Field(default="RANGE_RUNS", max_length=30)
    limit: int = Field(default=50, ge=1, le=100)

    @validator('position')
    def validate_position(cls, v):
        if v is not None:
            valid_positions = ['LF', 'CF', 'RF']
            if v not in valid_positions:
                raise ValueError(f'Invalid position. Must be one of: {valid_positions}')
        return v

    @validator('stat_name')
    def validate_outfielder_stat(cls, v):
        valid_stats = [
            'RANGE_RUNS', 'ARM_RUNS', 'JUMP_RATING',
            'ROUTE_EFFICIENCY', 'SPRINT_SPEED',
            'MAX_SPEED_MPH', 'FIRST_STEP_TIME',
            'TOTAL_OUTFIELDER_RUNS'
        ]
        if v not in valid_stats:
            raise ValueError(f'Invalid outfielder stat. Must be one of: {valid_stats}')
        return v


class FetchRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    fetch_type: FetchType = FetchType.all
    season: Optional[int] = Field(default=None, ge=1876, le=datetime.now().year + 1)


class DataFetchStatus(BaseModel):
    last_fetch: Optional[datetime]
    next_fetch: Optional[datetime]
    is_fetching: bool
    last_error: Optional[str]
    total_teams: int
    total_players: int
    total_games: int


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HistoricalStatsRequest(BaseModel):
    start_year: int = Field(default=2020, ge=1876, le=datetime.now().year)
    end_year: int = Field(default=2024, ge=1876, le=datetime.now().year)

    @validator('end_year')
    def validate_year_range(cls, v, values):
        if 'start_year' in values and v < values['start_year']:
            raise ValueError('end_year must be greater than or equal to start_year')
        return v
