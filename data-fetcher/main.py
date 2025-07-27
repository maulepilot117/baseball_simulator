import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional
import signal

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from mlb_stats_api import MLBStatsAPI
from performance_monitoring import get_performance_manager, initialize_monitoring
from data_consistency import run_daily_consistency_check
from input_validation import validate_api_input, PLAYER_STATS_SCHEMA, LEADERBOARD_SCHEMA, TEAM_ROSTER_SCHEMA

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
db_pool: Optional[asyncpg.Pool] = None
fetch_task: Optional[asyncio.Task] = None


class Config:
    """Application configuration"""
    def __init__(self):
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', 5432))
        self.db_user = os.getenv('DB_USER', 'baseball_user')
        self.db_password = os.getenv('DB_PASSWORD', 'baseball_pass')
        self.db_name = os.getenv('DB_NAME', 'baseball_sim')
        self.fetch_interval = int(os.getenv('FETCH_INTERVAL', 86400))  # 24 hours
        self.port = int(os.getenv('PORT', 8082))
        self.initial_years = int(os.getenv('INITIAL_YEARS', 5))  # Years of history to fetch


class DataFetchStatus(BaseModel):
    """Status of data fetching operations"""
    last_fetch: Optional[datetime]
    next_fetch: Optional[datetime]
    is_fetching: bool
    last_error: Optional[str]
    total_teams: int
    total_players: int
    total_games: int
    total_pitches: int


class FetchRequest(BaseModel):
    """Request model for manual data fetch"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    fetch_type: str = "all"  # all, teams, players, games, pitches, stats
    season: Optional[int] = None


async def create_db_pool(config: Config) -> asyncpg.Pool:
    """Create database connection pool"""
    return await asyncpg.create_pool(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        min_size=5,
        max_size=20,
        command_timeout=60
    )


async def ensure_db_tables(db_pool: asyncpg.Pool):
    """Ensure all required tables exist"""
    # Add player MLB mapping table if it doesn't exist
    await db_pool.execute("""
        CREATE TABLE IF NOT EXISTS player_mlb_mapping (
            player_id UUID PRIMARY KEY REFERENCES players(id),
            mlb_id INTEGER UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_player_mlb_mapping_mlb_id 
        ON player_mlb_mapping(mlb_id);
    """)
    
    # Add data fetch status table
    await db_pool.execute("""
        CREATE TABLE IF NOT EXISTS data_fetch_status (
            fetch_type VARCHAR(50) PRIMARY KEY,
            status VARCHAR(20),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            last_error TEXT,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


async def fetch_data_task(config: Config):
    """Background task to fetch data periodically"""
    global db_pool
    
    mlb_api = MLBStatsAPI(db_pool)
    
    while True:
        try:
            logger.info("Starting scheduled data fetch...")
            
            # Update fetch status
            await db_pool.execute("""
                INSERT INTO data_fetch_status (fetch_type, status, started_at)
                VALUES ('scheduled', 'running', $1)
                ON CONFLICT (fetch_type) DO UPDATE
                SET status = 'running', started_at = $1, updated_at = $1
            """, datetime.utcnow())
            
            # Determine date range
            # For daily updates, fetch last 7 days to ensure we catch any corrections
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Fetch all data
            await mlb_api.fetch_all_data(start_date, end_date)
            
            # Update fetch status
            await db_pool.execute("""
                UPDATE data_fetch_status
                SET status = 'completed',
                    completed_at = $1,
                    last_error = NULL,
                    updated_at = $1
                WHERE fetch_type = 'scheduled'
            """, datetime.utcnow())
            
            logger.info("Data fetch completed successfully")
            
        except Exception as e:
            logger.error(f"Error during data fetch: {str(e)}")
            
            # Update error status
            await db_pool.execute("""
                UPDATE data_fetch_status
                SET status = 'error',
                    completed_at = $1,
                    last_error = $2,
                    updated_at = $1
                WHERE fetch_type = 'scheduled'
            """, datetime.utcnow(), str(e))
        
        # Wait for next fetch interval
        await asyncio.sleep(config.fetch_interval)


async def daily_consistency_check_task():
    """Background task for daily data consistency checks"""
    global db_pool
    
    while True:
        try:
            # Run at 2 AM daily
            now = datetime.utcnow()
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"Next consistency check scheduled in {wait_seconds/3600:.1f} hours")
            await asyncio.sleep(wait_seconds)
            
            # Run consistency check
            logger.info("Starting daily data consistency check...")
            await run_daily_consistency_check(db_pool)
            
        except Exception as e:
            logger.error(f"Error in daily consistency check: {e}")
            # Wait 1 hour before retrying
            await asyncio.sleep(3600)


async def initial_data_load(config: Config):
    """Perform initial historical data load"""
    global db_pool
    
    logger.info(f"Starting initial data load for {config.initial_years} years...")
    
    mlb_api = MLBStatsAPI(db_pool)
    
    # Check if we already have data
    team_count = await db_pool.fetchval("SELECT COUNT(*) FROM teams")
    if team_count > 0:
        logger.info("Data already exists, skipping initial load")
        return
    
    try:
        # Fetch teams and venues first
        await mlb_api.fetch_teams_and_venues()
        
        # Fetch current rosters
        await mlb_api.fetch_all_players()
        
        # Fetch historical games
        end_date = datetime.now()
        start_date = datetime(end_date.year - config.initial_years, 1, 1)
        
        # Fetch by season to avoid overwhelming the API
        current_year = start_date.year
        while current_year <= end_date.year:
            season_start = datetime(current_year, 3, 1)  # Spring training
            season_end = datetime(current_year, 11, 1)   # After World Series
            
            if season_end > end_date:
                season_end = end_date
            
            logger.info(f"Fetching {current_year} season data...")
            await mlb_api.fetch_games_with_details(season_start, season_end)
            
            # Fetch season stats
            await mlb_api.fetch_player_stats(current_year)
            
            current_year += 1
        
        logger.info("Initial data load completed")
        
    except Exception as e:
        logger.error(f"Error during initial data load: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_pool, fetch_task
    
    config = Config()
    
    # Startup
    logger.info("Starting MLB Data Fetcher service with enhanced monitoring...")
    
    # Create database pool
    db_pool = await create_db_pool(config)
    
    # Initialize performance monitoring
    performance_manager = initialize_monitoring(db_pool)
    await performance_manager.start_monitoring()
    
    # Ensure required tables exist
    await ensure_db_tables(db_pool)
    
    # Perform initial data load if needed
    asyncio.create_task(initial_data_load(config))
    
    # Start background fetch task
    fetch_task = asyncio.create_task(fetch_data_task(config))
    
    # Start daily consistency checks
    consistency_task = asyncio.create_task(daily_consistency_check_task())
    
    yield
    
    # Shutdown
    logger.info("Shutting down MLB Data Fetcher service...")
    
    # Cancel tasks
    if fetch_task:
        fetch_task.cancel()
        try:
            await fetch_task
        except asyncio.CancelledError:
            pass
    
    if 'consistency_task' in locals():
        consistency_task.cancel()
        try:
            await consistency_task
        except asyncio.CancelledError:
            pass
    
    # Stop performance monitoring
    if performance_manager:
        await performance_manager.stop_monitoring()
    
    # Close database pool
    if db_pool:
        await db_pool.close()


# Create FastAPI app
app = FastAPI(
    title="MLB Data Fetcher",
    description="Service for fetching MLB statistics via official API",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global db_pool
    
    try:
        # Test database connection
        await db_pool.fetchval("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.utcnow(),
        "version": "2.0.0",
        "data_source": "MLB Stats API"
    }


@app.get("/status", response_model=DataFetchStatus)
async def get_fetch_status():
    """Get current data fetch status"""
    global db_pool
    
    try:
        # Get fetch status
        status = await db_pool.fetchrow("""
            SELECT status, started_at, completed_at, last_error
            FROM data_fetch_status
            WHERE fetch_type = 'scheduled'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        
        # Get data counts
        counts = await db_pool.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM teams) as teams,
                (SELECT COUNT(*) FROM players) as players,
                (SELECT COUNT(*) FROM games) as games,
                (SELECT COUNT(*) FROM pitches) as pitches
        """)
        
        is_fetching = status['status'] == 'running' if status else False
        last_fetch = status['completed_at'] if status else None
        next_fetch = last_fetch + timedelta(seconds=Config().fetch_interval) if last_fetch else None
        
        return DataFetchStatus(
            last_fetch=last_fetch,
            next_fetch=next_fetch,
            is_fetching=is_fetching,
            last_error=status['last_error'] if status else None,
            total_teams=counts['teams'],
            total_players=counts['players'],
            total_games=counts['games'],
            total_pitches=counts['pitches']
        )
        
    except Exception as e:
        logger.error(f"Error getting fetch status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/fetch")
async def trigger_manual_fetch(
    request: FetchRequest,
    background_tasks: BackgroundTasks
):
    """Trigger a manual data fetch"""
    global db_pool
    
    # Check if fetch is already running
    status = await db_pool.fetchval("""
        SELECT status FROM data_fetch_status
        WHERE fetch_type IN ('scheduled', 'manual')
        AND status = 'running'
        LIMIT 1
    """)
    
    if status:
        raise HTTPException(status_code=409, detail="Fetch already in progress")
    
    # Add fetch task to background
    background_tasks.add_task(
        manual_fetch,
        request.start_date,
        request.end_date,
        request.fetch_type,
        request.season
    )
    
    return {
        "message": "Fetch triggered successfully",
        "status": "started",
        "fetch_type": request.fetch_type
    }


async def manual_fetch(start_date: Optional[datetime], end_date: Optional[datetime], 
                      fetch_type: str, season: Optional[int]):
    """Perform manual data fetch"""
    global db_pool
    
    mlb_api = MLBStatsAPI(db_pool)
    
    try:
        # Update fetch status
        await db_pool.execute("""
            INSERT INTO data_fetch_status (fetch_type, status, started_at)
            VALUES ('manual', 'running', $1)
            ON CONFLICT (fetch_type) DO UPDATE
            SET status = 'running', started_at = $1, updated_at = $1
        """, datetime.utcnow())
        
        # Default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        if fetch_type == 'all':
            await mlb_api.fetch_all_data(start_date, end_date)
        elif fetch_type == 'teams':
            await mlb_api.fetch_teams_and_venues()
        elif fetch_type == 'players':
            await mlb_api.fetch_all_players()
        elif fetch_type == 'games':
            await mlb_api.fetch_games_with_details(start_date, end_date)
        elif fetch_type == 'stats' and season:
            await mlb_api.fetch_player_stats(season)
        else:
            raise ValueError(f"Invalid fetch type: {fetch_type}")
        
        # Update status
        await db_pool.execute("""
            UPDATE data_fetch_status
            SET status = 'completed',
                completed_at = $1,
                last_error = NULL,
                updated_at = $1
            WHERE fetch_type = 'manual'
        """, datetime.utcnow())
        
    except Exception as e:
        logger.error(f"Error during manual fetch: {str(e)}")
        await db_pool.execute("""
            UPDATE data_fetch_status
            SET status = 'error',
                completed_at = $1,
                last_error = $2,
                updated_at = $1
            WHERE fetch_type = 'manual'
        """, datetime.utcnow(), str(e))


@app.get("/teams")
async def get_teams():
    """Get all teams"""
    global db_pool
    
    teams = await db_pool.fetch("""
        SELECT t.*, s.name as stadium_name
        FROM teams t
        LEFT JOIN stadiums s ON t.stadium_id = s.id
        ORDER BY t.league, t.division, t.name
    """)
    
    return {"teams": [dict(team) for team in teams]}


@app.get("/players/{team_id}")
async def get_team_roster(team_id: str):
    """Get roster for a specific team"""
    global db_pool
    
    players = await db_pool.fetch("""
        SELECT p.*
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE t.team_id = $1
        ORDER BY p.position, p.last_name
    """, team_id)
    
    return {"players": [dict(player) for player in players]}


@app.get("/player/{player_id}/stats/{season}")
async def get_player_season_stats(player_id: str, season: int, stats_type: str = "batting"):
    """Get season statistics for a specific player"""
    global db_pool
    
    try:
        stats = await db_pool.fetchrow("""
            SELECT aggregated_stats, games_played, last_updated
            FROM player_season_aggregates
            WHERE player_id = $1 AND season = $2 AND stats_type = $3
        """, player_id, season, stats_type)
        
        if stats:
            return {
                "player_id": player_id,
                "season": season,
                "stats_type": stats_type,
                "stats": json.loads(stats['aggregated_stats']),
                "games_played": stats['games_played'],
                "last_updated": stats['last_updated']
            }
        else:
            raise HTTPException(status_code=404, detail="Player stats not found")
            
    except Exception as e:
        logger.error(f"Error getting player stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/player/{player_id}/advanced-stats/{season}")
async def get_player_advanced_stats(player_id: str, season: int, stats_type: str = "batting"):
    """Get advanced statistics for a specific player"""
    global db_pool
    
    try:
        stats = await db_pool.fetchrow("""
            SELECT aggregated_stats, games_played, last_updated
            FROM player_season_aggregates
            WHERE player_id = $1 AND season = $2 AND stats_type = $3
        """, player_id, season, stats_type)
        
        if stats:
            all_stats = json.loads(stats['aggregated_stats'])
            
            # Extract only advanced stats
            if stats_type == 'batting':
                advanced_stats = {k: v for k, v in all_stats.items() 
                                if k in ['wOBA', 'wRC+', 'ISO', 'BABIP', 'BB%', 'K%']}
            elif stats_type == 'pitching':
                advanced_stats = {k: v for k, v in all_stats.items() 
                                if k in ['FIP', 'xFIP', 'WHIP', 'ERA+', 'K/BB', 'BABIP', 'LOB%']}
            elif stats_type == 'fielding':
                advanced_stats = {k: v for k, v in all_stats.items() 
                                if k in ['UZR', 'DRS', 'FPCT+', 'ARM', 'POS_ADJ', 'RF']}
            else:
                advanced_stats = {}
            
            return {
                "player_id": player_id,
                "season": season,
                "stats_type": stats_type,
                "advanced_stats": advanced_stats,
                "last_updated": stats['last_updated']
            }
        else:
            raise HTTPException(status_code=404, detail="Player advanced stats not found")
            
    except Exception as e:
        logger.error(f"Error getting player advanced stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/calculate-advanced-stats/{season}")
async def trigger_advanced_stats_calculation(season: int, background_tasks: BackgroundTasks):
    """Trigger advanced statistics calculation for a season"""
    global db_pool
    
    from mlb_stats_api import MLBStatsAPI
    
    def calculate_advanced_stats_task():
        async def run_calculation():
            mlb_api = MLBStatsAPI(db_pool)
            await mlb_api.calculate_advanced_stats_for_season(season)
        
        import asyncio
        asyncio.run(run_calculation())
    
    background_tasks.add_task(calculate_advanced_stats_task)
    
    return {
        "message": f"Advanced statistics calculation started for {season} season",
        "season": season
    }


@app.get("/leaderboards/{season}")
async def get_season_leaderboards(season: int, stats_type: str = "batting", 
                                stat_name: str = "wRC+", limit: int = 50):
    """Get leaderboards for advanced statistics"""
    global db_pool
    
    try:
        # Validate stat name based on type
        if stats_type == 'batting':
            valid_stats = ['wOBA', 'wRC+', 'ISO', 'BABIP', 'BB%', 'K%', 'AVG', 'OBP', 'SLG', 'OPS', 'HR']
        elif stats_type == 'pitching':
            valid_stats = ['FIP', 'xFIP', 'WHIP', 'ERA+', 'K/BB', 'BABIP', 'LOB%', 'ERA', 'SO', 'W']
        elif stats_type == 'fielding':
            valid_stats = ['UZR', 'DRS', 'FPCT', 'RF', 'E', 'FPCT+', 'ARM', 'POS_ADJ']
        else:
            raise HTTPException(status_code=400, detail="Invalid stats_type")
        
        if stat_name not in valid_stats:
            raise HTTPException(status_code=400, detail=f"Invalid stat_name for {stats_type}")
        
        # Get leaderboard data
        results = await db_pool.fetch("""
            SELECT 
                p.player_id,
                p.first_name,
                p.last_name,
                t.name as team_name,
                t.abbreviation as team_abbrev,
                psa.aggregated_stats,
                psa.games_played
            FROM player_season_aggregates psa
            JOIN players p ON psa.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE psa.season = $1 
              AND psa.stats_type = $2
              AND (psa.aggregated_stats->>$3) IS NOT NULL
              AND psa.games_played >= 50
            ORDER BY 
                CASE 
                    WHEN $3 IN ('ERA', 'FIP', 'xFIP', 'WHIP', 'K%') 
                    THEN (psa.aggregated_stats->>$3)::float 
                    ELSE -(psa.aggregated_stats->>$3)::float 
                END
            LIMIT $4
        """, season, stats_type, stat_name, limit)
        
        leaderboard = []
        for i, row in enumerate(results):
            stats = json.loads(row['aggregated_stats'])
            leaderboard.append({
                "rank": i + 1,
                "player_id": row['player_id'],
                "name": f"{row['first_name']} {row['last_name']}",
                "team": row['team_abbrev'],
                "team_name": row['team_name'],
                "stat_value": stats.get(stat_name),
                "games_played": row['games_played']
            })
        
        return {
            "season": season,
            "stats_type": stats_type,
            "stat_name": stat_name,
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Error getting leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/fielding-leaderboards/{season}")
async def get_fielding_leaderboards_by_position(season: int, position: Optional[str] = None,
                                               stat_name: str = "UZR", limit: int = 50):
    """Get fielding leaderboards by position"""
    global db_pool
    
    try:
        from fielding_metrics import FieldingMetricsCalculator
        
        fielding_calc = FieldingMetricsCalculator(db_pool)
        leaderboard = await fielding_calc.get_fielding_leaderboards(
            season, stat_name, position, limit
        )
        
        return {
            "season": season,
            "position": position or "All",
            "stat_name": stat_name,
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Error getting fielding leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/calculate-fielding-stats/{season}")
async def trigger_fielding_stats_calculation(season: int, background_tasks: BackgroundTasks):
    """Trigger fielding statistics calculation for a season"""
    global db_pool
    
    from mlb_stats_api import MLBStatsAPI
    
    def calculate_fielding_stats_task():
        async def run_calculation():
            mlb_api = MLBStatsAPI(db_pool)
            await mlb_api.calculate_fielding_stats_for_season(season)
        
        import asyncio
        asyncio.run(run_calculation())
    
    background_tasks.add_task(calculate_fielding_stats_task)
    
    return {
        "message": f"Fielding statistics calculation started for {season} season",
        "season": season
    }


@app.get("/player/{player_id}/catcher-metrics/{season}")
async def get_player_catcher_metrics(player_id: str, season: int):
    """Get catcher-specific advanced metrics for a player"""
    global db_pool
    
    try:
        from position_specific_metrics import PositionSpecificMetrics
        
        position_calc = PositionSpecificMetrics(db_pool)
        metrics = await position_calc.calculate_all_catcher_metrics(player_id, season)
        
        if metrics:
            return {
                "player_id": player_id,
                "season": season,
                "position": "C",
                "catcher_metrics": metrics
            }
        else:
            raise HTTPException(status_code=404, detail="Catcher metrics not found")
            
    except Exception as e:
        logger.error(f"Error getting catcher metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/player/{player_id}/outfielder-metrics/{season}")
async def get_player_outfielder_metrics(player_id: str, season: int, position: str = "CF"):
    """Get outfielder-specific advanced metrics for a player"""
    global db_pool
    
    try:
        if position not in ['LF', 'CF', 'RF']:
            raise HTTPException(status_code=400, detail="Position must be LF, CF, or RF")
        
        from position_specific_metrics import PositionSpecificMetrics
        
        position_calc = PositionSpecificMetrics(db_pool)
        metrics = await position_calc.calculate_all_outfielder_metrics(player_id, season, position)
        
        if metrics:
            return {
                "player_id": player_id,
                "season": season,
                "position": position,
                "outfielder_metrics": metrics
            }
        else:
            raise HTTPException(status_code=404, detail="Outfielder metrics not found")
            
    except Exception as e:
        logger.error(f"Error getting outfielder metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/calculate-position-stats/{season}")
async def trigger_position_specific_stats_calculation(season: int, background_tasks: BackgroundTasks):
    """Trigger position-specific statistics calculation for a season"""
    global db_pool
    
    from position_specific_metrics import PositionSpecificMetrics
    
    def calculate_position_stats_task():
        async def run_calculation():
            position_calc = PositionSpecificMetrics(db_pool)
            await position_calc.calculate_all_position_specific_stats(season)
        
        import asyncio
        asyncio.run(run_calculation())
    
    background_tasks.add_task(calculate_position_stats_task)
    
    return {
        "message": f"Position-specific statistics calculation started for {season} season",
        "season": season
    }


@app.get("/catcher-leaderboards/{season}")
async def get_catcher_leaderboards(season: int, stat_name: str = "FRAMING_RUNS", limit: int = 25):
    """Get leaderboards for catcher-specific statistics"""
    global db_pool
    
    try:
        valid_catcher_stats = ['FRAMING_RUNS', 'BLOCKING_RUNS', 'ARM_RUNS', 'TOTAL_CATCHER_RUNS', 'CS_PCT', 'CATCHER_ERA']
        
        if stat_name not in valid_catcher_stats:
            raise HTTPException(status_code=400, detail=f"Invalid stat_name. Must be one of: {valid_catcher_stats}")
        
        # Get catcher leaderboard data
        results = await db_pool.fetch("""
            SELECT 
                p.player_id,
                p.first_name,
                p.last_name,
                t.name as team_name,
                t.abbreviation as team_abbrev,
                psa.aggregated_stats,
                psa.games_played
            FROM player_season_aggregates psa
            JOIN players p ON psa.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE psa.season = $1 
              AND psa.stats_type = 'fielding'
              AND p.position = 'C'
              AND (psa.aggregated_stats->>$2) IS NOT NULL
              AND psa.games_played >= 30
            ORDER BY (psa.aggregated_stats->>$2)::float DESC
            LIMIT $3
        """, season, stat_name, limit)
        
        leaderboard = []
        for i, row in enumerate(results):
            stats = json.loads(row['aggregated_stats'])
            leaderboard.append({
                "rank": i + 1,
                "player_id": row['player_id'],
                "name": f"{row['first_name']} {row['last_name']}",
                "team": row['team_abbrev'],
                "team_name": row['team_name'],
                "stat_value": stats.get(stat_name),
                "games_played": row['games_played']
            })
        
        return {
            "season": season,
            "position": "C",
            "stat_name": stat_name,
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Error getting catcher leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/outfielder-leaderboards/{season}")
async def get_outfielder_leaderboards(season: int, position: Optional[str] = None, 
                                     stat_name: str = "RANGE_RUNS", limit: int = 25):
    """Get leaderboards for outfielder-specific statistics"""
    global db_pool
    
    try:
        valid_of_stats = ['RANGE_RUNS', 'ARM_RUNS', 'TOTAL_OUTFIELD_RUNS', 'JUMP_RATING', 'ROUTE_EFFICIENCY', 'ARM_ACCURACY']
        valid_positions = ['LF', 'CF', 'RF']
        
        if stat_name not in valid_of_stats:
            raise HTTPException(status_code=400, detail=f"Invalid stat_name. Must be one of: {valid_of_stats}")
        
        if position and position not in valid_positions:
            raise HTTPException(status_code=400, detail=f"Invalid position. Must be one of: {valid_positions}")
        
        # Build query with optional position filter
        position_filter = ""
        params = [season, stat_name, limit]
        
        if position:
            position_filter = "AND p.position = $4"
            params.append(position)
        
        query = f"""
            SELECT 
                p.player_id,
                p.first_name,
                p.last_name,
                p.position,
                t.name as team_name,
                t.abbreviation as team_abbrev,
                psa.aggregated_stats,
                psa.games_played
            FROM player_season_aggregates psa
            JOIN players p ON psa.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE psa.season = $1 
              AND psa.stats_type = 'fielding'
              AND p.position IN ('LF', 'CF', 'RF')
              AND (psa.aggregated_stats->>$2) IS NOT NULL
              AND psa.games_played >= 30
              {position_filter}
            ORDER BY (psa.aggregated_stats->>$2)::float DESC
            LIMIT $3
        """
        
        results = await db_pool.fetch(query, *params)
        
        leaderboard = []
        for i, row in enumerate(results):
            stats = json.loads(row['aggregated_stats'])
            leaderboard.append({
                "rank": i + 1,
                "player_id": row['player_id'],
                "name": f"{row['first_name']} {row['last_name']}",
                "position": row['position'],
                "team": row['team_abbrev'],
                "team_name": row['team_name'],
                "stat_value": stats.get(stat_name),
                "games_played": row['games_played']
            })
        
        return {
            "season": season,
            "position": position or "All Outfielders",
            "stat_name": stat_name,
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Error getting outfielder leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/admin/performance-dashboard")
async def get_performance_dashboard():
    """Get performance monitoring dashboard data"""
    global db_pool
    
    try:
        performance_manager = get_performance_manager()
        if not performance_manager:
            raise HTTPException(status_code=503, detail="Performance monitoring not available")
        
        dashboard_data = performance_manager.get_dashboard_data()
        
        # Add additional statistics
        client_stats = {}
        try:
            # Get HTTP client stats if available
            mlb_api = MLBStatsAPI(db_pool)
            if hasattr(mlb_api.client, 'get_stats'):
                client_stats = mlb_api.client.get_stats()
        except Exception as e:
            logger.warning(f"Could not get client stats: {e}")
        
        dashboard_data['http_client'] = client_stats
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting performance dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/admin/validation-reports")
async def get_validation_reports(limit: int = 10):
    """Get recent data validation reports"""
    global db_pool
    
    try:
        from data_consistency import DataConsistencyValidator
        
        validator = DataConsistencyValidator(db_pool)
        reports = await validator.get_validation_history(limit)
        
        return {"validation_reports": reports}
        
    except Exception as e:
        logger.error(f"Error getting validation reports: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/validate-data/{season}")
async def trigger_data_validation(season: int, background_tasks: BackgroundTasks):
    """Trigger manual data validation for a season"""
    global db_pool
    
    # Input validation
    if not 1876 <= season <= datetime.utcnow().year + 1:
        raise HTTPException(status_code=400, detail="Invalid season year")
    
    def validation_task():
        async def run_validation():
            try:
                await run_daily_consistency_check(db_pool, season)
                logger.info(f"Manual data validation completed for season {season}")
            except Exception as e:
                logger.error(f"Manual data validation failed for season {season}: {e}")
        
        import asyncio
        asyncio.run(run_validation())
    
    background_tasks.add_task(validation_task)
    
    return {
        "message": f"Data validation started for season {season}",
        "season": season
    }


@app.get("/admin/circuit-breaker-status")
async def get_circuit_breaker_status():
    """Get circuit breaker status for all services"""
    try:
        from network_resilience import MLB_API_CIRCUIT_BREAKER, DATABASE_CIRCUIT_BREAKER
        
        return {
            "circuit_breakers": {
                "mlb_api": {
                    "state": MLB_API_CIRCUIT_BREAKER.state.value,
                    "stats": MLB_API_CIRCUIT_BREAKER.get_stats().__dict__
                },
                "database": {
                    "state": DATABASE_CIRCUIT_BREAKER.state.value,
                    "stats": DATABASE_CIRCUIT_BREAKER.get_stats().__dict__
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/reset-circuit-breaker/{breaker_name}")
async def reset_circuit_breaker(breaker_name: str):
    """Manually reset a circuit breaker"""
    try:
        from network_resilience import MLB_API_CIRCUIT_BREAKER, DATABASE_CIRCUIT_BREAKER
        
        if breaker_name == "mlb_api":
            MLB_API_CIRCUIT_BREAKER.reset()
        elif breaker_name == "database":
            DATABASE_CIRCUIT_BREAKER.reset()
        else:
            raise HTTPException(status_code=400, detail="Invalid circuit breaker name")
        
        return {"message": f"Circuit breaker '{breaker_name}' reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@validate_api_input(PLAYER_STATS_SCHEMA)
@app.get("/player/{player_id}/stats/{season}")
async def get_player_season_stats_enhanced(player_id: str, season: int, stats_type: str = "batting"):
    """Get season statistics for a specific player with enhanced validation"""
    global db_pool
    
    try:
        stats = await db_pool.fetchrow("""
            SELECT aggregated_stats, games_played, last_updated
            FROM player_season_aggregates
            WHERE player_id = $1 AND season = $2 AND stats_type = $3
        """, player_id, season, stats_type)
        
        if stats:
            return {
                "player_id": player_id,
                "season": season,
                "stats_type": stats_type,
                "stats": json.loads(stats['aggregated_stats']),
                "games_played": stats['games_played'],
                "last_updated": stats['last_updated']
            }
        else:
            raise HTTPException(status_code=404, detail="Player stats not found")
            
    except Exception as e:
        logger.error(f"Error getting player stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def handle_shutdown(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Run the application
    config = Config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        reload=True if os.getenv("ENV") == "development" else False
    )