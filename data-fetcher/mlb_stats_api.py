"""
Simplified MLB Stats API Client
Focuses on core functionality without over-engineering
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
import json

import asyncpg
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type

from config import settings
from stats_calculator import StatsCalculator
from umpire_scraper import update_umpire_scorecards
from game_details_fetcher import GameDetailsFetcher

logger = logging.getLogger(__name__)


class MLBStatsAPI:
    """Simple MLB Stats API Client"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            headers={'User-Agent': 'BaseballSimulation/2.0'},
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=50)
        )
        self.stats_calculator = StatsCalculator(db_pool)
        self.game_details_fetcher = GameDetailsFetcher(db_pool, self.client)

        # Simple caches for ID mappings
        self._team_cache: Dict[int, str] = {}
        self._player_cache: Dict[int, str] = {}

        self._api_semaphore = asyncio.Semaphore(50)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(httpx.HTTPStatusError)
    )
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to MLB API with simple retry logic"""
        async with self._api_semaphore:
            url = f"{settings.mlb_api_base_url}{endpoint}"
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    async def fetch_all_data(self, start_date: datetime, end_date: datetime):
        """Main entry point to fetch all data"""
        logger.info(f"Starting MLB data fetch from {start_date} to {end_date}")
        
        try:
            # 1. Fetch teams and venues
            await self.fetch_teams_and_venues()
            
            # 2. Fetch all players
            await self.fetch_all_players()
            
            # 3. Fetch games with detailed stats and pitch data
            logger.info("Fetching games with detailed stats...")
            await self.fetch_games(start_date, end_date)
            
            # 4. Fetch park factors for current season
            current_year = datetime.now().year
            await self.fetch_park_factors(current_year)

            # 6. Fetch umpire scorecard data
            try:
                logger.info("Fetching umpire scorecard data...")
                await update_umpire_scorecards(self.db_pool)
            except Exception as e:
                logger.error(f"Failed to fetch umpire scorecards: {e}")
                # Don't fail the entire fetch if umpire data fails
            
            # 5. Fetch stats for multiple seasons
            seasons_to_fetch = []
            
            # Add current season if we're past April
            if datetime.now().month >= 4:
                seasons_to_fetch.append(current_year)
            
            # Add previous seasons based on initial_years setting
            for i in range(1, settings.initial_years + 1):
                seasons_to_fetch.append(current_year - i)
            
            logger.info(f"Will fetch stats for seasons: {seasons_to_fetch}")
            
            for season in seasons_to_fetch:
                try:
                    logger.info(f"Fetching stats for {season} season...")
                    await self.fetch_season_stats(season)
                except Exception as e:
                    logger.error(f"Failed to fetch stats for {season}: {e}")
            
            logger.info("MLB data fetch completed successfully")
            
        except Exception as e:
            logger.error(f"Error during data fetch: {e}")
            raise
    
    async def fetch_teams_and_venues(self):
        """Fetch all teams and their venues"""
        logger.info("Fetching teams and venues...")
        
        data = await self._get("/teams", {"sportId": 1})
        teams = data.get("teams", [])
        
        # Process venues first
        venues_processed = set()
        for team in teams:
            if team.get("active", False) and team.get("venue", {}).get("id"):
                venue = team["venue"]
                if venue["id"] not in venues_processed:
                    await self._save_venue(venue)
                    venues_processed.add(venue["id"])
        
        # Process teams
        for team in teams:
            if team.get("active", False):
                await self._save_team(team)
        
        logger.info(f"Saved {len(teams)} teams and {len(venues_processed)} venues")
    
    async def fetch_all_players(self):
        """Fetch all players from current rosters"""
        logger.info("Fetching all players...")
        
        # Get all teams
        teams = await self.db_pool.fetch("SELECT id, team_id, name FROM teams")
        
        # Fetch team data from MLB API to get MLB IDs
        mlb_teams_data = await self._get("/teams", {"sportId": 1})
        mlb_teams_map = {}
        for mlb_team in mlb_teams_data.get("teams", []):
            if mlb_team.get("active", False):
                abbrev = mlb_team.get("abbreviation", "").lower()
                mlb_teams_map[abbrev] = mlb_team["id"]
        
        # Prepare roster fetch tasks
        roster_tasks = []
        for team in teams:
            team_abbrev = team['team_id']
            mlb_team_id = mlb_teams_map.get(team_abbrev)
            
            if mlb_team_id:
                self._team_cache[mlb_team_id] = team['id']
                roster_tasks.append(self._fetch_team_roster(mlb_team_id))
        
        # Fetch ALL rosters in parallel
        roster_results = await asyncio.gather(*roster_tasks, return_exceptions=True)
        
        total_players = sum(len(players) if not isinstance(players, Exception) else 0 
                        for players in roster_results)
        
        logger.info(f"Fetched {total_players} total players")
    
    async def fetch_games(self, start_date: datetime, end_date: datetime):
        """Fetch games in date range"""
        logger.info(f"Fetching games from {start_date} to {end_date}")
        
        # Create list of all dates
        dates_to_fetch = []
        current_date = start_date
        while current_date <= end_date:
            dates_to_fetch.append(current_date)
            current_date += timedelta(days=1)
        
        # Optimized batch processing with semaphore for concurrency control
        batch_size = 50  # Increased from 30 for better throughput
        max_concurrent = 10  # Limit concurrent requests
        total_games = 0

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(date):
            async with semaphore:
                return await self._fetch_games_for_date(date)

        for i in range(0, len(dates_to_fetch), batch_size):
            batch = dates_to_fetch[i:i + batch_size]
            results = await asyncio.gather(*[
                fetch_with_semaphore(date) for date in batch
            ], return_exceptions=True)

            for result in results:
                if not isinstance(result, Exception):
                    total_games += len(result)

            # Minimal delay between batches
            if i + batch_size < len(dates_to_fetch):
                await asyncio.sleep(0.05)  # Reduced from 0.1
        
        logger.info(f"Fetched {total_games} games")
    
    async def fetch_season_stats(self, season: int):
        """Fetch and calculate season statistics"""
        logger.info(f"Fetching stats for {season} season")
        
        # Get all players with MLB IDs
        players = await self.db_pool.fetch("""
            SELECT p.id, pm.mlb_id::int, p.full_name
            FROM players p
            JOIN player_mlb_mapping pm ON p.id = pm.player_id
            WHERE p.status = 'A'
        """)
        
        logger.info(f"Found {len(players)} active players to fetch stats for")
        
        # Track success/failure
        success_count = 0
        error_count = 0
        
        # Optimized batch processing with concurrency control
        batch_size = 250  # Increased from 200
        max_concurrent = 25  # Limit concurrent API requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_player_with_semaphore(player):
            async with semaphore:
                return await self._fetch_player_season_stats(player['id'], player['mlb_id'], season)

        for i in range(0, len(players), batch_size):
            batch = players[i:i + batch_size]
            results = await asyncio.gather(*[
                fetch_player_with_semaphore(player) for player in batch
            ], return_exceptions=True)

            # Count successes and failures
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    player = batch[j]
                    logger.error(f"Failed to fetch stats for {player['full_name']} ({player['mlb_id']}): {result}")
                else:
                    success_count += 1

            logger.info(f"Processed batch {i//batch_size + 1}/{(len(players) + batch_size - 1)//batch_size}")
            await asyncio.sleep(0.1)  # Reduced from 0.2
        
        logger.info(f"Stats fetch complete: {success_count} successful, {error_count} errors")
    
    # Calculate aggregated stats only if we have some successful fetches
        if success_count > 0:
            await self.stats_calculator.calculate_all_season_stats(season)
        
        logger.info(f"Completed stats processing for {season}")
    
    # Helper methods
    
    async def _fetch_team_roster(self, team_id: int) -> List[Dict]:
        """Fetch roster for a specific team"""
        try:
            data = await self._get(f"/teams/{team_id}/roster", {"rosterType": "40Man"})
            roster = data.get("roster", [])
            players = []
            
            for entry in roster:
                person = entry.get("person", {})
                if person.get("id"):
                    # Keep the original MLB status code
                    status_code = entry.get("status", {}).get("code", "A")
                    
                    player_data = {
                        'mlb_id': person["id"],
                        'full_name': person.get("fullName", ""),
                        'status': status_code,  # Use the actual MLB status code
                        'team_id': team_id
                    }
                    
                    # Get additional details
                    details = await self._get_player_details(person["id"])
                    player_data.update(details)
                    
                    await self._save_player(player_data)
                    players.append(player_data)
            
            return players
            
        except Exception as e:
            logger.error(f"Error fetching roster for team {team_id}: {e}")
            return []
    
    async def _get_player_details(self, player_id: int) -> Dict:
        """Get detailed player information"""
        try:
            data = await self._get(f"/people/{player_id}")
            person = data.get("people", [{}])[0]
            
            return {
                'birth_date': person.get("birthDate"),
                'birth_city': person.get("birthCity"),
                'birth_country': person.get("birthCountry"),
                'height': person.get("height"),
                'weight': person.get("weight"),
                'bats': person.get("batSide", {}).get("code"),
                'throws': person.get("pitchHand", {}).get("code"),
                'first_name': person.get("firstName"),
                'last_name': person.get("lastName"),
                'jersey_number': person.get("primaryNumber"),
                'position': person.get("primaryPosition", {}).get("abbreviation"),
                'debut_date': person.get("mlbDebutDate"),
                'strike_zone_top': person.get("strikeZoneTop"),
                'strike_zone_bottom': person.get("strikeZoneBottom")              
            }
        except:
            return {}
    
    async def _fetch_games_for_date(self, date: datetime) -> List[Dict]:
        """Fetch all games for a specific date (including scheduled games for simulations)"""
        date_str = date.strftime("%Y-%m-%d")

        try:
            data = await self._get("/schedule", {"sportId": 1, "date": date_str})
            games = []
            game_detail_tasks = []

            logger.info(f"API returned {len(data.get('dates', []))} dates with games for {date_str}")

            for date_data in data.get("dates", []):
                logger.info(f"Processing date {date_data.get('date')} with {len(date_data.get('games', []))} games")
                for game in date_data.get("games", []):
                    
                    game_type = game.get("gameType", "")
                    if not settings.fetch_spring_training and game_type in ["S", "E"]:  # Spring training or exhibition
                        logger.debug(f"Skipping non-regular season game {game_pk} - type: {game_type}")
                        continue
                    
                    game_status = game.get("status", {})
                    game_pk = game["gamePk"]
                    
                    # Log game status for debugging
                    logger.debug(f"Game {game_pk} status: {game_status.get('codedGameState')} - {game_status.get('detailedState')}")

                    # Process both final and scheduled games
                    coded_state = game_status.get("codedGameState", "")
                    detailed_state = game_status.get("detailedState", "")
                    abstract_state = game_status.get("abstractGameState", "")

                    # Skip postponed/suspended/cancelled games
                    if any(status in detailed_state.lower() for status in ["postponed", "suspended", "cancelled"]):
                        logger.debug(f"Skipping game {game_pk} - {detailed_state}")
                        continue

                    # Fetch scheduled games (for simulations) and final games (for historical data)
                    is_scheduled = coded_state == "S" and abstract_state == "Preview"
                    is_final = coded_state == "F" and abstract_state == "Final"

                    if not (is_scheduled or is_final):
                        logger.debug(f"Skipping game {game_pk} - not scheduled or final: {detailed_state}")
                        continue

                    # Get scores (will be None for scheduled games)
                    home_score = game["teams"]["home"].get("score")
                    away_score = game["teams"]["away"].get("score")

                    # For final games, require valid scores
                    if is_final and (home_score is None or away_score is None):
                        logger.debug(f"Skipping final game {game_pk} - no valid scores")
                        continue

                    # Determine game status
                    game_status_str = "scheduled" if is_scheduled else detailed_state

                    game_info = {
                        'game_pk': game_pk,
                        'game_date': date,
                        'home_team_id': game["teams"]["home"]["team"]["id"],
                        'away_team_id': game["teams"]["away"]["team"]["id"],
                        'home_score': home_score,
                        'away_score': away_score,
                        'status': game_status_str
                    }
                    
                    # Save basic game info
                    await self._save_game(game_info)
                    games.append(game_info)
                    
                    # Queue game stats fetch
                    game_detail_tasks.append(self.fetch_game_stats(game_pk))
            
            # Fetch all game details in parallel with error handling
            if game_detail_tasks:
                results = await asyncio.gather(*game_detail_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to fetch game details: {result}")
            
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games for {date_str}: {e}")
            return []
        
    async def _fetch_player_season_stats(self, player_uuid: str, mlb_id: int, season: int):
        """Fetch season stats for a player"""
        try:
            # Add more detailed logging
            logger.debug(f"Fetching stats for player {mlb_id} (UUID: {player_uuid}) for season {season}")
            
            # Batting stats
            batting = await self._get(f"/people/{mlb_id}/stats", {
                "stats": "season",
                "group": "hitting",
                "season": season,
                "sportId": 1
            })
            await self._process_stats(player_uuid, batting, 'batting', season)
            
            # Pitching stats
            pitching = await self._get(f"/people/{mlb_id}/stats", {
                "stats": "season",
                "group": "pitching", 
                "season": season,
                "sportId": 1
            })
            await self._process_stats(player_uuid, pitching, 'pitching', season)
            
            # Fielding stats
            fielding = await self._get(f"/people/{mlb_id}/stats", {
                "stats": "season",
                "group": "fielding", 
                "season": season,
                "sportId": 1
            })
            await self._process_stats(player_uuid, fielding, 'fielding', season)
            
        except Exception as e:
            logger.error(f"Error fetching stats for player {mlb_id} (season {season}): {e}")
            raise
    
    async def _process_stats(self, player_uuid: str, stats_data: Dict, 
                       stats_type: str, season: int):
        """Process and save player statistics"""
        # Add validation
        if not stats_data or not isinstance(stats_data, dict):
            logger.warning(f"Invalid stats data for player {player_uuid}, type {stats_type}")
            return
            
        stats_list = stats_data.get("stats", [])
        if not stats_list:
            logger.debug(f"No stats found for player {player_uuid}, type {stats_type}, season {season}")
            return
        
        # Log the structure for debugging
        logger.debug(f"Processing {len(stats_list)} stat groups for player {player_uuid}")
        
        for stat_group in stats_list:
            splits = stat_group.get("splits", [])
            if not splits:
                logger.debug(f"No splits found in stat group for player {player_uuid}")
                continue
                
            for split in splits:
                stat = split.get("stat", {})
                if stat:
                    # Log what we're saving
                    games_played = stat.get('gamesPlayed', 0)
                    logger.debug(f"Saving {stats_type} stats for player {player_uuid}: {games_played} games")
                    
                    # Save raw stats - let the calculator handle derived stats
                    await self.db_pool.execute("""
                        INSERT INTO player_season_aggregates 
                        (player_id, season, stats_type, aggregated_stats, games_played)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (player_id, season, stats_type) DO UPDATE
                        SET aggregated_stats = EXCLUDED.aggregated_stats,
                            games_played = EXCLUDED.games_played,
                            last_updated = NOW()
                    """, player_uuid, season, stats_type, json.dumps(stat), games_played)
    
    # Save methods
    
    async def _save_venue(self, venue: Dict):
        """Save venue to database"""
        try:
            location_parts = []
            if venue.get('location', {}).get('city'):
                location_parts.append(venue['location']['city'])
            if venue.get('location', {}).get('state'):
                location_parts.append(venue['location']['state'])
            location = ', '.join(location_parts) if location_parts else None
            
            # First check if updated_at column exists
            has_updated_at = await self.db_pool.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'stadiums' AND column_name = 'updated_at'
                )
            """)
            
            if has_updated_at:
                await self.db_pool.execute("""
                    INSERT INTO stadiums (stadium_id, name, location, capacity)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (stadium_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        capacity = EXCLUDED.capacity,
                        updated_at = NOW()
                """, str(venue.get("id")), venue.get("name"), 
                    location,
                    venue.get("capacity"))
            else:
                await self.db_pool.execute("""
                    INSERT INTO stadiums (stadium_id, name, location, capacity)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (stadium_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        capacity = EXCLUDED.capacity
                """, str(venue.get("id")), venue.get("name"), 
                    location,
                    venue.get("capacity"))
        except Exception as e:
            logger.error(f"Failed to save venue {venue.get('id')}: {e}")
    
    async def _save_team(self, team: Dict):
        """Save team to database"""
        try:
            team_abbrev = team.get("abbreviation", "").lower()
            
            # First check if stadium exists
            venue_id = None
            if team.get("venue", {}).get("id"):
                venue_id = await self.db_pool.fetchval("""
                    SELECT id FROM stadiums WHERE stadium_id = $1
                """, str(team.get("venue", {}).get("id")))
            
            # Insert or update team
            team_uuid = await self.db_pool.fetchval("""
                INSERT INTO teams (team_id, name, abbreviation, league, division, stadium_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (team_id) DO UPDATE
                SET name = EXCLUDED.name,
                    abbreviation = EXCLUDED.abbreviation,
                    league = EXCLUDED.league,
                    division = EXCLUDED.division,
                    stadium_id = EXCLUDED.stadium_id,
                    updated_at = NOW()
                RETURNING id
            """, team_abbrev, team.get("name"), team.get("abbreviation"),
                team.get("league", {}).get("name"), team.get("division", {}).get("name"),
                venue_id)
            
            if team_uuid:
                    self._team_cache[team.get("id")] = team_uuid
            
        except Exception as e:
            logger.error(f"Failed to save team {team.get('id')}: {e}")
    
    async def _save_player(self, player: Dict):
        """Save player to database with proper UUID handling"""
        try:
            # Normalize player names
            player = self._normalize_player_names(player)
            
            # Get team UUID from MLB team ID
            team_uuid = None
            if player.get('team_id'):
                # Look up from our cache first
                mlb_team_id = player.get('team_id')
                if mlb_team_id in self._team_cache:
                    team_uuid = self._team_cache[mlb_team_id]
                else:
                    # Query database
                    team_uuid = await self._get_team_uuid_by_mlb_id(mlb_team_id)
            
            # Save player
            player_uuid = await self.db_pool.fetchval("""
                INSERT INTO players (
                    player_id, first_name, last_name, full_name, birth_date,
                    position, bats, throws, team_id, status, jersey_number, 
                    debut_date, birth_city, birth_country, height, weight,
                    strike_zone_top, strike_zone_btm
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (player_id) DO UPDATE
                SET first_name = COALESCE(EXCLUDED.first_name, players.first_name),
                    last_name = COALESCE(EXCLUDED.last_name, players.last_name),
                    full_name = EXCLUDED.full_name,
                    team_id = EXCLUDED.team_id,
                    position = COALESCE(EXCLUDED.position, players.position),
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id
            """, f"mlb_{player['mlb_id']}", 
                player.get('first_name'), 
                player.get('last_name'),
                player['full_name'],
                datetime.strptime(player.get('birth_date'), '%Y-%m-%d').date() if player.get('birth_date') else None,
                player.get('position'), 
                player.get('bats', 'R'),
                player.get('throws', 'R'), 
                team_uuid, 
                player.get('status', 'active'),
                str(player.get('jersey_number', '')) if player.get('jersey_number') else None,
                datetime.strptime(player.get('debut_date'), '%Y-%m-%d').date() if player.get('debut_date') else None,
                player.get('birth_city', ''),
                player.get('birth_country', ''),
                str(player.get('height', '')) if player.get('height') else None,
                player.get('weight', '') if player.get('weight') else None,
                float(player.get('strike_zone_top', 0)),
                float(player.get('strike_zone_bottom', 0))
            )
            
            # Save MLB ID mapping
            await self.db_pool.execute("""
                INSERT INTO player_mlb_mapping (player_id, mlb_id)
                VALUES ($1, $2)
                ON CONFLICT (player_id) DO NOTHING
            """, player_uuid, player['mlb_id'])
            
            # Cache the mapping
            self._player_cache[player['mlb_id']] = player_uuid
            
        except Exception as e:
            logger.error(f"Failed to save player {player.get('mlb_id')}: {e}")
    
    async def _save_game(self, game: Dict):
        """Save game to database and fetch detailed game information"""
        try:
            home_team_uuid = await self._get_team_uuid_by_mlb_id(game['home_team_id'])
            away_team_uuid = await self._get_team_uuid_by_mlb_id(game['away_team_id'])

            # Get stadium from home team
            stadium_uuid = await self.db_pool.fetchval("""
                SELECT stadium_id FROM teams WHERE id = $1
            """, home_team_uuid)

            # Save game
            result = await self.db_pool.fetchrow("""
                INSERT INTO games (
                    game_id, game_date, home_team_id, away_team_id,
                    stadium_id, season, status, final_score_home, final_score_away
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (game_id) DO UPDATE
                SET final_score_home = EXCLUDED.final_score_home,
                    final_score_away = EXCLUDED.final_score_away,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id
            """, str(game['game_pk']), game['game_date'].date(),
                home_team_uuid, away_team_uuid, stadium_uuid,
                game['game_date'].year, game.get('status', 'Final'),
                game.get('home_score'), game.get('away_score'))

            # Fetch game details (box score, play-by-play, weather) for completed games
            game_uuid = result['id']
            game_id = str(game['game_pk'])

            # Check if we already have box score data
            has_box_score = await self.db_pool.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM game_box_score_batting WHERE game_id = $1 LIMIT 1
                )
            """, game_uuid)

            if not has_box_score:
                logger.info(f"Fetching details for game {game_id}")
                try:
                    await self.game_details_fetcher.fetch_game_details(game_id, game_uuid)
                except Exception as e:
                    logger.error(f"Failed to fetch game details for {game_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to save game {game.get('game_pk')}: {e}")
    
    # Utility methods
    
    def _normalize_player_names(self, player: Dict) -> Dict:
        """Normalize player names to ensure consistency"""
        # Get any version of full name
        full_name = player.get('full_name') or player.get('fullName', '').strip()
        
        # If no first/last name, try to parse from full name
        if (not player.get('first_name') or not player.get('last_name')) and full_name:
            name_parts = full_name.split(None, 1)
            if len(name_parts) == 1:
                player['first_name'] = name_parts[0]
                player['last_name'] = name_parts[0]
            else:
                player['first_name'] = name_parts[0]
                player['last_name'] = name_parts[1]
        
        # Ensure full_name exists
        if not full_name:
            first = player.get('first_name', '')
            last = player.get('last_name', '')
            if first and last:
                player['full_name'] = f"{first} {last}"
            else:
                player['full_name'] = f"Player_{player.get('mlb_id', 'Unknown')}"
        else:
            player['full_name'] = full_name
        
        return player
    
    async def _get_mlb_team_id(self, team_abbrev: str) -> Optional[int]:
        """Get MLB team ID from our abbreviation"""
        # First check if we have this team in the database
        result = await self.db_pool.fetchrow("""
            SELECT t.id as uuid, tm.mlb_id 
            FROM teams t
            LEFT JOIN (
                SELECT DISTINCT jsonb_object_keys(stats)::int as mlb_id, team_id
                FROM player_stats
            ) tm ON tm.team_id = t.id
            WHERE t.team_id = $1
        """, team_abbrev)
        
        if result and result['mlb_id']:
            # Cache the mapping
            self._team_cache[result['mlb_id']] = result['uuid']
            return result['mlb_id']
        
        # Not in database, fetch from API
        data = await self._get("/teams", {"sportId": 1})
        for team in data.get("teams", []):
            if team.get("abbreviation", "").lower() == team_abbrev:
                mlb_id = team["id"]
                # Get the UUID from database
                team_uuid = await self.db_pool.fetchval(
                    "SELECT id FROM teams WHERE team_id = $1", team_abbrev
                )
                if team_uuid:
                    self._team_cache[mlb_id] = team_uuid
                return mlb_id
        
        return None
    
    async def _get_team_uuid_by_mlb_id(self, mlb_id: int) -> Optional[str]:
        """Get our team UUID from MLB team ID"""
        # Check cache first
        if mlb_id in self._team_cache:
            cached_value = self._team_cache[mlb_id]
            # Verify it's a UUID (36 chars with dashes)
            if isinstance(cached_value, str) and len(cached_value) == 36:
                return cached_value
        
        # Not in cache or invalid, fetch from API and database
        try:
            data = await self._get(f"/teams/{mlb_id}")
            team = data.get("teams", [{}])[0]
            team_abbrev = team.get("abbreviation", "").lower()
            
            # Look up UUID from database
            team_uuid = await self.db_pool.fetchval(
                "SELECT id FROM teams WHERE team_id = $1", team_abbrev
            )
            
            if team_uuid:
                self._team_cache[mlb_id] = team_uuid
                
            return team_uuid
        except Exception as e:
            logger.error(f"Error getting team UUID for MLB ID {mlb_id}: {e}")
            return None
    
    async def _get_player_uuid_by_mlb_id(self, mlb_id: int) -> Optional[str]:
        """Get our player UUID from MLB player ID"""
        if mlb_id in self._player_cache:
            return self._player_cache[mlb_id]
        
        player_uuid = await self.db_pool.fetchval(
            "SELECT player_id FROM player_mlb_mapping WHERE mlb_id = $1", mlb_id
        )
        
        if player_uuid:
            self._player_cache[mlb_id] = player_uuid
        
        return player_uuid

    async def fetch_game_stats(self, game_pk: int):
        """Fetch detailed stats for a specific game using the feed/live endpoint"""
        try:
            logger.debug(f"Fetching detailed stats for game {game_pk}")
            
            # Don't use the retry decorator for this specific call
            async with self._api_semaphore:
                url = f"{settings.mlb_api_base_url}/game/{game_pk}/feed/live"
                response = await self.client.get(url)
                
                if response.status_code == 404:
                    logger.warning(f"Game {game_pk} not found (404) - may be postponed, cancelled, or not yet played")
                    return
                elif response.status_code != 200:
                    logger.error(f"Unexpected status code {response.status_code} for game {game_pk}")
                    return
                    
                game_feed = response.json()
            
            # Verify the game data is complete before processing
            game_data = game_feed.get('gameData', {})
            live_data = game_feed.get('liveData', {})
            
            # Check if game was actually played
            if not live_data or not game_data:
                logger.warning(f"Game {game_pk} has incomplete data - skipping")
                return
                
            # Process boxscore data
            boxscore = live_data.get('boxscore', {})
            if boxscore:
                await self._process_game_boxscore(game_pk, boxscore)
            
            # Process play-by-play for pitches
            plays = live_data.get('plays', {})
            if plays:
                await self._process_game_pitches(game_pk, plays)
            
            # Process umpire data
            if game_data:
                await self._process_umpires(game_pk, game_data)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Game {game_pk} not found (404)")
            else:
                logger.error(f"HTTP error fetching game stats for {game_pk}: {e}")
        except Exception as e:
            logger.error(f"Error fetching game stats for {game_pk}: {e}")

    async def _process_game_boxscore(self, game_pk: int, boxscore: Dict):
        """Process and save boxscore data to player_stats table"""
        try:
            # Get game info
            game_uuid = await self.db_pool.fetchval(
                "SELECT id FROM games WHERE game_id = $1", str(game_pk)
            )
            if not game_uuid:
                logger.warning(f"Game {game_pk} not found in database")
                return
                
            game_date = await self.db_pool.fetchval(
                "SELECT game_date FROM games WHERE id = $1", game_uuid
            )
            season = game_date.year
            
            # Process batting stats
            for team in ['home', 'away']:
                team_data = boxscore.get('teams', {}).get(team, {})
                
                # Batting stats
                batters = team_data.get('batters', [])
                for batter_id in batters:
                    player_uuid = await self._get_player_uuid_by_mlb_id(batter_id)
                    if player_uuid:
                        player_stats = team_data.get('players', {}).get(f'ID{batter_id}', {})
                        batting_stats = player_stats.get('stats', {}).get('batting', {})
                        
                        if batting_stats:
                            await self.db_pool.execute("""
                                INSERT INTO player_stats (player_id, game_id, season, game_date, stats_type, stats)
                                VALUES ($1, $2, $3, $4, $5, $6)
                                ON CONFLICT DO NOTHING
                            """, player_uuid, game_uuid, season, game_date, 'batting', json.dumps(batting_stats))
                
                # Pitching stats
                pitchers = team_data.get('pitchers', [])
                for pitcher_id in pitchers:
                    player_uuid = await self._get_player_uuid_by_mlb_id(pitcher_id)
                    if player_uuid:
                        player_stats = team_data.get('players', {}).get(f'ID{pitcher_id}', {})
                        pitching_stats = player_stats.get('stats', {}).get('pitching', {})
                        
                        if pitching_stats:
                            await self.db_pool.execute("""
                                INSERT INTO player_stats (player_id, game_id, season, game_date, stats_type, stats)
                                VALUES ($1, $2, $3, $4, $5, $6)
                                ON CONFLICT DO NOTHING
                            """, player_uuid, game_uuid, season, game_date, 'pitching', json.dumps(pitching_stats))
                
                # Fielding stats
                fielders = team_data.get('players', {})
                for player_key, player_data in fielders.items():
                    if player_key.startswith('ID'):
                        player_id = int(player_key[2:])
                        player_uuid = await self._get_player_uuid_by_mlb_id(player_id)
                        if player_uuid:
                            fielding_stats = player_data.get('stats', {}).get('fielding', {})
                            if fielding_stats:
                                await self.db_pool.execute("""
                                    INSERT INTO player_stats (player_id, game_id, season, game_date, stats_type, stats)
                                    VALUES ($1, $2, $3, $4, $5, $6)
                                    ON CONFLICT DO NOTHING
                                """, player_uuid, game_uuid, season, game_date, 'fielding', json.dumps(fielding_stats))
                                
        except Exception as e:
            logger.error(f"Error processing boxscore for game {game_pk}: {e}")

    async def _process_game_pitches(self, game_pk: int, plays_data: Dict):
        """Process pitch-by-pitch data from game feed"""
        try:
            game_uuid = await self.db_pool.fetchval(
                "SELECT id FROM games WHERE game_id = $1", str(game_pk)
            )
            if not game_uuid:
                logger.warning(f"Game {game_pk} not found in database")
                return
                
            game_date = await self.db_pool.fetchval(
                "SELECT game_date FROM games WHERE id = $1", game_uuid
            )
            
            all_plays = plays_data.get('allPlays', [])
            pitch_count = 0
            
            for play in all_plays:
                about = play.get('about', {})
                inning = about.get('inning', 0)
                inning_half = 'top' if about.get('halfInning', '') == 'top' else 'bottom'
                
                # Get batter and pitcher
                matchup = play.get('matchup', {})
                batter_id = matchup.get('batter', {}).get('id')
                pitcher_id = matchup.get('pitcher', {}).get('id')
                
                if not batter_id or not pitcher_id:
                    continue
                    
                batter_uuid = await self._get_player_uuid_by_mlb_id(batter_id)
                pitcher_uuid = await self._get_player_uuid_by_mlb_id(pitcher_id)
                
                if not batter_uuid or not pitcher_uuid:
                    continue
                
                # Process each pitch in the at-bat
                play_events = play.get('playEvents', [])
                for i, event in enumerate(play_events):
                    if event.get('isPitch', False):
                        pitch_data = event.get('pitchData', {})
                        
                        # Extract pitch details
                        pitch_type = event.get('details', {}).get('type', {}).get('code')
                        velocity = pitch_data.get('startSpeed')
                        spin_rate = pitch_data.get('breaks', {}).get('spinRate')
                        
                        # Location data
                        coordinates = pitch_data.get('coordinates', {})
                        plate_x = coordinates.get('pX')
                        plate_z = coordinates.get('pZ')
                        
                        # Result
                        details = event.get('details', {})
                        result = details.get('type', {}).get('description')
                        
                        # Hit data if applicable
                        hit_data = play.get('result', {}).get('hitData', {})
                        exit_velocity = hit_data.get('launchSpeed')
                        launch_angle = hit_data.get('launchAngle')
                        hit_distance = hit_data.get('totalDistance')
                        
                        # Only save if we have valid pitch data
                        if pitch_type:
                            await self.db_pool.execute("""
                                INSERT INTO pitches (
                                    game_id, pitcher_id, batter_id, game_date,
                                    inning, inning_half, pitch_number, pitch_type,
                                    velocity, spin_rate, plate_location, result,
                                    exit_velocity, launch_angle, hit_distance
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                                ON CONFLICT DO NOTHING
                            """, game_uuid, pitcher_uuid, batter_uuid, game_date,
                                inning, inning_half, i + 1, pitch_type,
                                velocity, spin_rate, 
                                json.dumps({'x': plate_x, 'z': plate_z}) if plate_x is not None and plate_z is not None else None,
                                result, exit_velocity, launch_angle, hit_distance)
                            pitch_count += 1
            
            logger.info(f"Saved {pitch_count} pitches for game {game_pk}")
                                
        except Exception as e:
            logger.error(f"Error processing pitches for game {game_pk}: {e}")

    async def fetch_umpires_for_game(self, game_pk: int):
        """Fetch and save umpire data for a game"""
        try:
            game_data = await self._get(f"/game/{game_pk}/linescore")
            
            officials = game_data.get('officialsByRole', {})
            home_plate_ump = officials.get('homePlate', {})
            
            if home_plate_ump.get('id'):
                ump_id = str(home_plate_ump['id'])
                ump_name = home_plate_ump.get('fullName', '')
                
                # Save umpire
                ump_uuid = await self.db_pool.fetchval("""
                    INSERT INTO umpires (umpire_id, name)
                    VALUES ($1, $2)
                    ON CONFLICT (umpire_id) DO UPDATE
                    SET name = EXCLUDED.name
                    RETURNING id
                """, ump_id, ump_name)
                
                # Update game with umpire
                await self.db_pool.execute("""
                    UPDATE games 
                    SET home_plate_umpire_id = $1
                    WHERE game_id = $2
                """, ump_uuid, str(game_pk))
                
        except Exception as e:
            logger.error(f"Error fetching umpires for game {game_pk}: {e}")
    
    async def fetch_park_factors(self, season: int):
        """Fetch park factors for all stadiums"""
        try:
            # Get all stadiums
            stadiums = await self.db_pool.fetch("SELECT id, stadium_id FROM stadiums")
            
            for stadium in stadiums:
                # MLB API doesn't directly provide park factors, so we'll set defaults
                # In a real implementation, you'd calculate these from historical data
                default_factors = [
                    ('hr', 1.000),
                    ('doubles', 1.000),
                    ('triples', 1.000),
                    ('batting_avg', 1.000)
                ]
                
                for factor_type, value in default_factors:
                    await self.db_pool.execute("""
                        INSERT INTO park_factors (stadium_id, season, factor_type, factor_value)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (stadium_id, season, factor_type, handedness) DO UPDATE
                        SET factor_value = EXCLUDED.factor_value
                    """, stadium['id'], season, factor_type, value)
                    
        except Exception as e:
            logger.error(f"Error fetching park factors: {e}")
    
    async def _process_umpires(self, game_pk: int, game_data: Dict):
        """Process and save umpire data from game feed"""
        try:
            officials = game_data.get('officials', [])
            
            for official in officials:
                if official.get('officialType') == 'Home Plate':
                    official_data = official.get('official', {})
                    ump_id = str(official_data.get('id', ''))
                    ump_name = official_data.get('fullName', '')
                    
                    if ump_id and ump_name:
                        # Save umpire
                        ump_uuid = await self.db_pool.fetchval("""
                            INSERT INTO umpires (umpire_id, name)
                            VALUES ($1, $2)
                            ON CONFLICT (umpire_id) DO UPDATE
                            SET name = EXCLUDED.name
                            RETURNING id
                        """, ump_id, ump_name)
                        
                        # Update game with umpire
                        await self.db_pool.execute("""
                            UPDATE games 
                            SET home_plate_umpire_id = $1
                            WHERE game_id = $2
                        """, ump_uuid, str(game_pk))
                        
                        logger.debug(f"Saved umpire {ump_name} for game {game_pk}")
                    
        except Exception as e:
            logger.error(f"Error processing umpires for game {game_pk}: {e}")
    
    async def _should_fetch_game_details(self, game_pk: int, game_date: date) -> bool:
        """Check if we should fetch detailed stats for a game"""
        # Don't fetch games from the last 24 hours to avoid in-progress games
        if (datetime.now().date() - game_date).days < 1:
            return False
            
        # Check if we already have game stats
        game_exists = await self.db_pool.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM player_stats ps
                JOIN games g ON ps.game_id = g.id
                WHERE g.game_id = $1
                LIMIT 1
            )
        """, str(game_pk))
        
        if game_exists:
            logger.debug(f"Game {game_pk} stats already exist - skipping")
            return False
            
        return True