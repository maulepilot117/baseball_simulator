"""
Simplified MLB Data Fetcher Service
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import PlayerStatsRequest, LeaderboardRequest, FetchRequest, DataFetchStatus, FetchType, HistoricalStatsRequest, ErrorResponse, CatcherMetricsRequest, OutfielderMetricsRequest, CatcherLeaderboardRequest, OutfielderLeaderboardRequest
from mlb_stats_api import MLBStatsAPI

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data-fetcher.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting MLB Data Fetcher service...")

    # Create database pool with optimized settings
    # Lower pool size to reduce "too many clients" errors
    # Pool size calculation: min for background tasks, max for burst traffic
    app.state.db_pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        min_size=5,        # Minimum connections for idle state
        max_size=15,       # Maximum connections for peak load
        max_queries=50000, # Recycle connection after 50k queries
        max_inactive_connection_lifetime=300,  # Close idle connections after 5min
        command_timeout=30 # 30s query timeout
    )

    # Ensure required tables exist
    logger.info("Connected to database with existing scheme.")

    # Start background fetch task
    app.state.fetch_task = asyncio.create_task(
        periodic_data_fetch(app.state.db_pool)
    )

    yield

    # Shutdown
    logger.info("Shutting down MLB Data Fetcher service...")

    # Cancel background task
    app.state.fetch_task.cancel()
    try:
        await app.state.fetch_task
    except asyncio.CancelledError:
        pass

    # Close database pool
    await app.state.db_pool.close()


app = FastAPI(
    title="MLB Data Fetcher",
    description="Simplified MLB statistics fetcher",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware with restricted headers for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


async def periodic_data_fetch(db_pool: asyncpg.Pool):
    """Background task to fetch data periodically"""
    while True:
        try:
            logger.info("Starting scheduled data fetch...")

            # Record fetch start
            await db_pool.execute("""
                INSERT INTO data_fetch_status (started_at, status)
                VALUES ($1, 'running')
            """, datetime.utcnow())

            # Create MLB API client and fetch data
            async with MLBStatsAPI(db_pool) as mlb_api:
                # Only fetch up to yesterday to avoid in-progress/future games
                end_date = datetime.now() - timedelta(days=1)  # Changed: subtract 1 day
                start_date = end_date - timedelta(days=7)
                await mlb_api.fetch_all_data(start_date, end_date)

            # Record successful completion
            await db_pool.execute("""
                UPDATE data_fetch_status
                SET completed_at = $1, status = 'completed'
                WHERE id = (SELECT MAX(id) FROM data_fetch_status)
            """, datetime.utcnow())

            logger.info("Data fetch completed successfully")

        except Exception as e:
            logger.error(f"Error during data fetch: {e}")

            # Record error
            await db_pool.execute("""
                UPDATE data_fetch_status
                SET completed_at = $1, status = 'error', error_message = $2
                WHERE id = (SELECT MAX(id) FROM data_fetch_status)
            """, datetime.utcnow(), str(e))

        # Wait for next fetch interval
        await asyncio.sleep(settings.fetch_interval)


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await app.state.db_pool.fetchval("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    except:
        return {"status": "unhealthy", "timestamp": datetime.utcnow()}


@app.get("/status", response_model=DataFetchStatus)
async def get_fetch_status():
    """Get current data fetch status"""
    # Get latest fetch status
    status = await app.state.db_pool.fetchrow("""
        SELECT started_at, completed_at, status, error_message
        FROM data_fetch_status
        ORDER BY id DESC
        LIMIT 1
    """)

    # Get data counts
    counts = await app.state.db_pool.fetchrow("""
        SELECT
            (SELECT COUNT(*) FROM teams) as teams,
            (SELECT COUNT(*) FROM players) as players,
            (SELECT COUNT(*) FROM games) as games
    """)

    if status:
        is_fetching = status['status'] == 'running'
        last_fetch = status['completed_at']
        next_fetch = last_fetch + timedelta(seconds=settings.fetch_interval) if last_fetch else None
    else:
        is_fetching = False
        last_fetch = None
        next_fetch = None

    return DataFetchStatus(
        last_fetch=last_fetch,
        next_fetch=next_fetch,
        is_fetching=is_fetching,
        last_error=status['error_message'] if status else None,
        total_teams=counts['teams'],
        total_players=counts['players'],
        total_games=counts['games']
    )


@app.post("/fetch")
async def trigger_manual_fetch(
    request: FetchRequest,
    background_tasks: BackgroundTasks
):
    """Trigger a manual data fetch"""
    # Check if fetch is already running
    status = await app.state.db_pool.fetchval("""
        SELECT status FROM data_fetch_status
        WHERE status = 'running'
        ORDER BY id DESC
        LIMIT 1
    """)

    if status:
        raise HTTPException(status_code=409, detail="Fetch already in progress")

    # Add fetch task to background
    background_tasks.add_task(
        manual_fetch,
        app.state.db_pool,
        request
    )

    return {"message": "Fetch triggered successfully"}

@app.post("/fetch/historical-stats")
async def fetch_historical_stats(
    request: HistoricalStatsRequest,
    background_tasks: BackgroundTasks
):
    """Fetch stats for a range of years"""
    background_tasks.add_task(
        fetch_stats_for_years,
        app.state.db_pool,
        request.start_year,
        request.end_year
    )

    return {
        "message": f"Stats fetch for years {request.start_year}-{request.end_year} triggered successfully"
    }


async def fetch_stats_for_years(db_pool: asyncpg.Pool, start_year: int, end_year: int):
    """Fetch stats for a range of years"""
    try:
        async with MLBStatsAPI(db_pool) as mlb_api:
            for year in range(start_year, end_year + 1):
                logger.info(f"Fetching stats for {year}")
                try:
                    await mlb_api.fetch_season_stats(year)
                except Exception as e:
                    logger.error(f"Error fetching stats for {year}: {e}")
                    # Continue with other years
    except Exception as e:
        logger.error(f"Error in historical stats fetch: {e}")


async def manual_fetch(db_pool: asyncpg.Pool, request: FetchRequest):
    """Perform manual data fetch"""
    try:
        # Record fetch start
        await db_pool.execute("""
            INSERT INTO data_fetch_status (started_at, status)
            VALUES ($1, 'running')
        """, datetime.utcnow())

        async with MLBStatsAPI(db_pool) as mlb_api:
            # Default date range if not provided
            end_date = request.end_date or (datetime.now() - timedelta(days=1))  # Changed
            start_date = request.start_date or (end_date - timedelta(days=30))

            # Ensure we're not fetching future games
            if end_date.date() >= datetime.now().date():
                end_date = datetime.now() - timedelta(days=1)

            if request.fetch_type == FetchType.all:
                await mlb_api.fetch_all_data(start_date, end_date)
            elif request.fetch_type == FetchType.teams:
                await mlb_api.fetch_teams_and_venues()
            elif request.fetch_type == FetchType.players:
                await mlb_api.fetch_all_players()
            elif request.fetch_type == FetchType.games:
                await mlb_api.fetch_games(start_date, end_date)
            elif request.fetch_type == FetchType.stats and request.season:
                await mlb_api.fetch_season_stats(request.season)

        # Record completion
        await db_pool.execute("""
            UPDATE data_fetch_status
            SET completed_at = $1, status = 'completed'
            WHERE id = (SELECT MAX(id) FROM data_fetch_status)
        """, datetime.utcnow())

    except Exception as e:
        logger.error(f"Manual fetch error: {e}")
        await db_pool.execute("""
            UPDATE data_fetch_status
            SET completed_at = $1, status = 'error', error_message = $2
            WHERE id = (SELECT MAX(id) FROM data_fetch_status)
        """, datetime.utcnow(), str(e))


@app.get("/teams")
async def get_teams():
    """Get all teams"""
    teams = await app.state.db_pool.fetch("""
        SELECT t.*, s.name as stadium_name
        FROM teams t
        LEFT JOIN stadiums s ON t.stadium_id = s.id
        ORDER BY t.league, t.division, t.name
    """)

    return [dict(team) for team in teams]


@app.get("/players/{team_id}")
async def get_team_roster(team_id: str):
    """Get roster for a specific team"""
    players = await app.state.db_pool.fetch("""
        SELECT p.*
        FROM players p
        WHERE p.team_id = (SELECT id FROM teams WHERE team_id = $1)
        ORDER BY p.position, p.last_name
    """, team_id)

    if not players:
        raise HTTPException(status_code=404, detail="Team not found")

    return [dict(player) for player in players]


@app.get("/player/{player_id}/stats/{season}")
async def get_player_stats(request: PlayerStatsRequest = Depends()):
    """Get player statistics"""
    stats = await app.state.db_pool.fetchrow("""
        SELECT aggregated_stats, games_played, last_updated
        FROM player_season_aggregates
        WHERE player_id = (SELECT id FROM players WHERE player_id = $1)
          AND season = $2
          AND stats_type = $3
    """, request.player_id, request.season, request.stats_type.value)

    if not stats:
        raise HTTPException(status_code=404, detail="Player stats not found")

    return {
        "player_id": request.player_id,
        "season": request.season,
        "stats_type": request.stats_type,
        "stats": stats['aggregated_stats'],
        "games_played": stats['games_played'],
        "last_updated": stats['last_updated']
    }


@app.get("/leaderboards/{season}")
async def get_leaderboards(request: LeaderboardRequest = Depends()):
    """Get statistical leaderboards"""
    # Build query based on stat type
    order_direction = "ASC" if request.stat_name in ['ERA', 'WHIP', 'FIP'] else "DESC"

    query = f"""
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.full_name,
            t.name as team_name,
            t.abbreviation as team_abbrev,
            psa.aggregated_stats,
            psa.games_played
        FROM player_season_aggregates psa
        JOIN players p ON psa.player_id = p.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE psa.season = $1
          AND psa.stats_type = $2
          AND psa.games_played >= 50
          AND (psa.aggregated_stats->>$3) IS NOT NULL
    """

    if request.position:
        query += " AND p.position = $5"

    query += f"""
        ORDER BY (psa.aggregated_stats->>$3)::float {order_direction}
        LIMIT $4
    """

    # Execute query
    params = [request.season, request.stats_type.value, request.stat_name, request.limit]
    if request.position:
        params.append(request.position)

    results = await app.state.db_pool.fetch(query, *params)

    # Format leaderboard
    leaderboard = []
    for i, row in enumerate(results):
        stats = row['aggregated_stats']
        leaderboard.append({
            "rank": i + 1,
            "player_id": row['player_id'],
            "name": row['full_name'],
            "team": row['team_abbrev'],
            "stat_value": stats.get(request.stat_name),
            "games_played": row['games_played']
        })

    return {
        "season": request.season,
        "stats_type": request.stats_type,
        "stat_name": request.stat_name,
        "leaderboard": leaderboard
    }


# Position-Specific Endpoints

@app.get("/player/{player_id}/catcher-metrics/{season}")
async def get_catcher_metrics(request: CatcherMetricsRequest = Depends()):
    """Get catcher-specific performance metrics"""
    # Get player info
    player_info = await app.state.db_pool.fetchrow("""
        SELECT id, full_name, position
        FROM players
        WHERE player_id = $1
    """, request.player_id)

    if not player_info:
        raise HTTPException(status_code=404, detail="Player not found")

    if player_info['position'] != 'C':
        raise HTTPException(status_code=400, detail="Player is not a catcher")

    # Get catcher stats
    catcher_stats = await app.state.db_pool.fetchrow("""
        SELECT framing_runs, blocking_runs, arm_runs, pop_time, exchange_time,
               framing_pct_above, blocking_pct_above, cs_above_avg, total_catcher_runs
        FROM catcher_stats
        WHERE player_id = $1 AND season = $2
    """, player_info['id'], request.season)

    if not catcher_stats:
        raise HTTPException(status_code=404, detail="Catcher stats not found for this season")

    return {
        "player_id": request.player_id,
        "player_name": player_info['full_name'],
        "season": request.season,
        "position": player_info['position'],
        "metrics": {
            "framing_runs": float(catcher_stats['framing_runs'] or 0),
            "blocking_runs": float(catcher_stats['blocking_runs'] or 0),
            "arm_runs": float(catcher_stats['arm_runs'] or 0),
            "pop_time_seconds": float(catcher_stats['pop_time'] or 2.0),
            "exchange_time_seconds": float(catcher_stats['exchange_time'] or 0.85),
            "framing_pct_above_avg": float(catcher_stats['framing_pct_above'] or 0),
            "blocking_pct_above_avg": float(catcher_stats['blocking_pct_above'] or 0),
            "cs_above_avg": float(catcher_stats['cs_above_avg'] or 0),
            "total_catcher_runs": float(catcher_stats['total_catcher_runs'] or 0)
        }
    }


@app.get("/player/{player_id}/outfielder-metrics/{season}")
async def get_outfielder_metrics(request: OutfielderMetricsRequest = Depends()):
    """Get outfielder-specific performance metrics"""
    # Get player info
    player_info = await app.state.db_pool.fetchrow("""
        SELECT id, full_name, position
        FROM players
        WHERE player_id = $1
    """, request.player_id)

    if not player_info:
        raise HTTPException(status_code=404, detail="Player not found")

    if player_info['position'] not in ['LF', 'CF', 'RF']:
        raise HTTPException(status_code=400, detail="Player is not an outfielder")

    # Get outfielder stats
    outfielder_stats = await app.state.db_pool.fetchrow("""
        SELECT range_runs, arm_runs, jump_rating, route_efficiency, sprint_speed,
               max_speed, first_step_time, total_outfielder_runs
        FROM outfielder_stats
        WHERE player_id = $1 AND season = $2 AND position = $3
    """, player_info['id'], request.season, request.position)

    if not outfielder_stats:
        raise HTTPException(status_code=404, detail="Outfielder stats not found for this season")

    return {
        "player_id": request.player_id,
        "player_name": player_info['full_name'],
        "season": request.season,
        "position": request.position,
        "metrics": {
            "range_runs": float(outfielder_stats['range_runs'] or 0),
            "arm_runs": float(outfielder_stats['arm_runs'] or 0),
            "jump_rating": float(outfielder_stats['jump_rating'] or 20.0),
            "route_efficiency": float(outfielder_stats['route_efficiency'] or 1.0),
            "sprint_speed": float(outfielder_stats['sprint_speed'] or 0),
            "max_speed_mph": float(outfielder_stats['max_speed'] or 0),
            "first_step_time": float(outfielder_stats['first_step_time'] or 0),
            "total_outfielder_runs": float(outfielder_stats['total_outfielder_runs'] or 0)
        }
    }


@app.get("/catcher-leaderboards/{season}")
async def get_catcher_leaderboards(request: CatcherLeaderboardRequest = Depends()):
    """Get catcher performance leaderboards"""
    # Map stat names to column names
    column_mapping = {
        'framing_runs': 'framing_runs',
        'blocking_runs': 'blocking_runs',
        'arm_runs': 'arm_runs',
        'pop_time_seconds': 'pop_time',
        'exchange_time_seconds': 'exchange_time',
        'framing_pct_above_avg': 'framing_pct_above',
        'blocking_pct_above_avg': 'blocking_pct_above',
        'cs_above_avg': 'cs_above_avg',
        'total_catcher_runs': 'total_catcher_runs'
    }

    order_column = column_mapping.get(request.stat_name.lower(), 'total_catcher_runs')

    # Get catcher leaderboard data
    query = f"""
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.full_name,
            t.name as team_name,
            t.abbreviation as team_abbrev,
            c.framing_runs,
            c.blocking_runs,
            c.arm_runs,
            c.pop_time,
            c.exchange_time,
            c.framing_pct_above,
            c.blocking_pct_above,
            c.cs_above_avg,
            c.total_catcher_runs
        FROM catcher_stats c
        JOIN players p ON c.player_id = p.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE c.season = $1
        ORDER BY c.{order_column} DESC
        LIMIT $2
    """

    catchers = await app.state.db_pool.fetch(query, request.season, request.limit)

    # Format leaderboard
    leaderboard = []
    for i, catcher in enumerate(catchers):
        leaderboard.append({
            "rank": i + 1,
            "player_id": catcher['player_id'],
            "name": catcher['full_name'],
            "team": catcher['team_abbrev'],
            "framing_runs": float(catcher['framing_runs'] or 0),
            "blocking_runs": float(catcher['blocking_runs'] or 0),
            "arm_runs": float(catcher['arm_runs'] or 0),
            "pop_time_seconds": float(catcher['pop_time'] or 2.0),
            "exchange_time_seconds": float(catcher['exchange_time'] or 0.85),
            "framing_pct_above_avg": float(catcher['framing_pct_above'] or 0),
            "blocking_pct_above_avg": float(catcher['blocking_pct_above'] or 0),
            "cs_above_avg": float(catcher['cs_above_avg'] or 0),
            "total_catcher_runs": float(catcher['total_catcher_runs'] or 0)
        })

    return {
        "season": request.season,
        "stat_name": request.stat_name,
        "leaderboard": leaderboard,
        "count": len(leaderboard)
    }


@app.get("/outfielder-leaderboards/{season}")
async def get_outfielder_leaderboards(request: OutfielderLeaderboardRequest = Depends()):
    """Get outfielder performance leaderboards"""
    # Map stat names to column names
    column_mapping = {
        'range_runs': 'range_runs',
        'arm_runs': 'arm_runs',
        'jump_rating': 'jump_rating',
        'route_efficiency': 'route_efficiency',
        'sprint_speed': 'sprint_speed',
        'max_speed_mph': 'max_speed',
        'first_step_time': 'first_step_time',
        'total_outfielder_runs': 'total_outfielder_runs'
    }

    order_column = column_mapping.get(request.stat_name.lower(), 'total_outfielder_runs')

    # Get outfielder leaderboard data
    query = f"""
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.full_name,
            p.position,
            t.name as team_name,
            t.abbreviation as team_abbrev,
            o.range_runs,
            o.arm_runs,
            o.jump_rating,
            o.route_efficiency,
            o.sprint_speed,
            o.max_speed,
            o.first_step_time,
            o.total_outfielder_runs
        FROM outfielder_stats o
        JOIN players p ON o.player_id = p.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE o.season = $1 AND o.position = $2
        ORDER BY o.{order_column} DESC
        LIMIT $3
    """

    outfielders = await app.state.db_pool.fetch(query, request.season, request.position, request.limit)

    # Format leaderboard
    leaderboard = []
    for i, outfielder in enumerate(outfielders):
        leaderboard.append({
            "rank": i + 1,
            "player_id": outfielder['player_id'],
            "name": outfielder['full_name'],
            "team": outfielder['team_abbrev'],
            "position": outfielder['position'],
            "range_runs": float(outfielder['range_runs'] or 0),
            "arm_runs": float(outfielder['arm_runs'] or 0),
            "jump_rating": float(outfielder['jump_rating'] or 20.0),
            "route_efficiency": float(outfielder['route_efficiency'] or 1.0),
            "sprint_speed": float(outfielder['sprint_speed'] or 0),
            "max_speed_mph": float(outfielder['max_speed'] or 0),
            "first_step_time": float(outfielder['first_step_time'] or 0),
            "total_outfielder_runs": float(outfielder['total_outfielder_runs'] or 0)
        })

    return {
        "season": request.season,
        "position": request.position,
        "stat_name": request.stat_name,
        "leaderboard": leaderboard,
        "count": len(leaderboard)
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=os.getenv("ENV") == "development"
    )
