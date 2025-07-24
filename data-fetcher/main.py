import os
import sys
import asyncio
import logging
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
    logger.info("Starting MLB Data Fetcher service...")
    
    # Create database pool
    db_pool = await create_db_pool(config)
    
    # Ensure required tables exist
    await ensure_db_tables(db_pool)
    
    # Perform initial data load if needed
    asyncio.create_task(initial_data_load(config))
    
    # Start background fetch task
    fetch_task = asyncio.create_task(fetch_data_task(config))
    
    yield
    
    # Shutdown
    logger.info("Shutting down MLB Data Fetcher service...")
    
    # Cancel fetch task
    if fetch_task:
        fetch_task.cancel()
        try:
            await fetch_task
        except asyncio.CancelledError:
            pass
    
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