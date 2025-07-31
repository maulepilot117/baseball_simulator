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
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from stats_calculator import StatsCalculator

logger = logging.getLogger(__name__)


class MLBStatsAPI:
    """Simple MLB Stats API Client"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            headers={'User-Agent': 'BaseballSimulation/2.0'}
        )
        self.stats_calculator = StatsCalculator(db_pool)
        
        # Simple caches for ID mappings
        self._team_cache: Dict[int, str] = {}
        self._player_cache: Dict[int, str] = {}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(settings.max_retries), 
           wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to MLB API with simple retry logic"""
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
            
            # 3. Fetch games
            await self.fetch_games(start_date, end_date)
            
            # 4. Fetch and calculate stats for current season
            current_season = datetime.now().year
            await self.fetch_season_stats(current_season)
            
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
        
        teams = await self.db_pool.fetch("SELECT team_id FROM teams")
        total_players = 0
        
        for team in teams:
            mlb_team_id = await self._get_mlb_team_id(team['team_id'])
            if mlb_team_id:
                players = await self._fetch_team_roster(mlb_team_id)
                total_players += len(players)
        
        logger.info(f"Fetched {total_players} total players")
    
    async def fetch_games(self, start_date: datetime, end_date: datetime):
        """Fetch games in date range"""
        logger.info(f"Fetching games from {start_date} to {end_date}")
        
        current_date = start_date
        total_games = 0
        
        while current_date <= end_date:
            games = await self._fetch_games_for_date(current_date)
            total_games += len(games)
            current_date += timedelta(days=1)
            await asyncio.sleep(0.1)  # Simple rate limiting
        
        logger.info(f"Fetched {total_games} games")
    
    async def fetch_season_stats(self, season: int):
        """Fetch and calculate season statistics"""
        logger.info(f"Fetching stats for {season} season")
        
        # Get all players
        players = await self.db_pool.fetch("""
            SELECT p.id, pm.mlb_id::int
            FROM players p
            JOIN player_mlb_mapping pm ON p.id = pm.player_id
            WHERE p.status = 'active'
        """)
        
        # Process in batches to avoid overwhelming the API
        batch_size = 50
        for i in range(0, len(players), batch_size):
            batch = players[i:i + batch_size]
            await asyncio.gather(*[
                self._fetch_player_season_stats(player['id'], player['mlb_id'], season)
                for player in batch
            ])
            await asyncio.sleep(1)  # Rate limiting between batches
        
        # Calculate aggregated stats
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
                    player_data = {
                        'mlb_id': person["id"],
                        'full_name': person.get("fullName", ""),
                        'status': entry.get("status", {}).get("code", "Active"),
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
        """Fetch all games for a specific date"""
        date_str = date.strftime("%Y-%m-%d")
        
        try:
            data = await self._get("/schedule", {"sportId": 1, "date": date_str})
            games = []
            
            for date_data in data.get("dates", []):
                for game in date_data.get("games", []):
                    if game.get("status", {}).get("codedGameState") == "F":  # Final games only
                        game_info = {
                            'game_pk': game["gamePk"],
                            'game_date': date,
                            'home_team_id': game["teams"]["home"]["team"]["id"],
                            'away_team_id': game["teams"]["away"]["team"]["id"],
                            'home_score': game["teams"]["home"].get("score"),
                            'away_score': game["teams"]["away"].get("score")
                        }
                        await self._save_game(game_info)
                        games.append(game_info)
            
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games for {date_str}: {e}")
            return []
    
    async def _fetch_player_season_stats(self, player_uuid: str, mlb_id: int, season: int):
        """Fetch season stats for a player"""
        try:
            # Batting stats
            batting = await self._get(f"/people/{mlb_id}/stats", {
                "stats": "season",
                "group": "hitting",
                "season": season
            })
            await self._process_stats(player_uuid, batting, 'batting', season)
            
            # Pitching stats
            pitching = await self._get(f"/people/{mlb_id}/stats", {
                "stats": "season",
                "group": "pitching", 
                "season": season
            })
            await self._process_stats(player_uuid, pitching, 'pitching', season)
            
            # Fielding stats
            fielding = await self._get(f"/people/{mlb_id}/stats", {
                "stats": "season",
                "group": "fielding", 
                "season": season
            })
            await self._process_stats(player_uuid, fielding, 'fielding', season)
            
        except Exception as e:
            logger.error(f"Error fetching stats for player {mlb_id}: {e}")
    
    async def _process_stats(self, player_uuid: str, stats_data: Dict, 
                           stats_type: str, season: int):
        """Process and save player statistics"""
        stats_list = stats_data.get("stats", [])
        if not stats_list:
            return
        
        for stat_group in stats_list:
            splits = stat_group.get("splits", [])
            for split in splits:
                stat = split.get("stat", {})
                if stat:
                    # Save raw stats - let the calculator handle derived stats
                    await self.db_pool.execute("""
                        INSERT INTO player_season_aggregates 
                        (player_id, season, stats_type, aggregated_stats, games_played)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (player_id, season, stats_type) DO UPDATE
                        SET aggregated_stats = EXCLUDED.aggregated_stats,
                            games_played = EXCLUDED.games_played,
                            last_updated = NOW()
                    """, player_uuid, season, stats_type, json.dumps(stat), 
                        stat.get('gamesPlayed', 0))
    
    # Save methods
    
    async def _save_venue(self, venue: Dict):
        """Save venue to database"""
        try:
            await self.db_pool.execute("""
                INSERT INTO stadiums (stadium_id, name, location, capacity)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (stadium_id) DO UPDATE
                SET name = EXCLUDED.name,
                    location = EXCLUDED.location,
                    capacity = EXCLUDED.capacity
            """, str(venue.get("id")), venue.get("name"), 
                f"{venue.get('location', {}).get('city', '')}, {venue.get('location', {}).get('state', '')}",
                venue.get("capacity"))
        except Exception as e:
            logger.error(f"Failed to save venue {venue.get('id')}: {e}")
    
    async def _save_team(self, team: Dict):
        """Save team to database"""
        try:
            team_abbrev = team.get("abbreviation", "").lower()
            
            venue_id = await self.db_pool.fetchval("""
                SELECT id FROM stadiums WHERE stadium_id = $1
            """, str(team.get("venue", {}).get("id")))
            
            await self.db_pool.execute("""
                INSERT INTO teams (team_id, name, abbreviation, league, division, stadium_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (team_id) DO UPDATE
                SET name = EXCLUDED.name,
                    league = EXCLUDED.league,
                    division = EXCLUDED.division,
                    stadium_id = EXCLUDED.stadium_id
            """, team_abbrev, team.get("name"), team.get("abbreviation"),
                team.get("league", {}).get("name"), team.get("division", {}).get("name"),
                venue_id)
            
            self._team_cache[team.get("id")] = team_abbrev
            
        except Exception as e:
            logger.error(f"Failed to save team {team.get('id')}: {e}")
    
    async def _save_player(self, player: Dict):
        """Save player to database with proper name handling"""
        try:
            # Normalize player names
            player = self._normalize_player_names(player)
            
            # Get team UUID
            team_uuid = await self._get_team_uuid_by_mlb_id(player.get('team_id'))
            
            # Save player
            player_uuid = await self.db_pool.fetchval("""
                INSERT INTO players (player_id, first_name, last_name, full_name, birth_date,
                                   position, bats, throws, team_id, status, jersey_number, debut_date, birth_city, birth_country, height, weight,
                                    strike_zone_top, strike_zone_btm)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (player_id) DO UPDATE
                SET first_name = COALESCE(EXCLUDED.first_name, players.first_name),
                    last_name = COALESCE(EXCLUDED.last_name, players.last_name),
                    full_name = EXCLUDED.full_name,
                    team_id = EXCLUDED.team_id,
                    position = EXCLUDED.position,
                    status = EXCLUDED.status
                RETURNING id
            """, f"mlb_{player['mlb_id']}", 
                player.get('first_name'), 
                player.get('last_name'),
                player['full_name'],  # This is guaranteed to exist after normalization
                datetime.strptime(player.get('birth_date'), '%Y-%m-%d').date() if player.get('birth_date') else None, 
                player.get('position'), 
                player.get('bats', 'R'),
                player.get('throws', 'R'), 
                team_uuid, 
                player.get('status', 'Active'),
                player.get('jersey_number', ''),
                datetime.strptime(player.get('debut_date'), '%Y-%m-%d').date() if player.get('debut_date') else None,
                player.get('birth_city', ''),
                player.get('birth_country', ''),
                player.get('height', ''),
                player.get('weight', ''),
                player.get('strike_zone_top', 0),
                player.get('strike_zone_bottom', 0)
            )

            
            # Save MLB ID mapping
            await self.db_pool.execute("""
                INSERT INTO player_mlb_mapping (player_id, mlb_id)
                VALUES ($1, $2)
                ON CONFLICT (player_id) DO NOTHING
            """, player_uuid, player['mlb_id'])
            
            self._player_cache[player['mlb_id']] = player_uuid
            
        except Exception as e:
            logger.error(f"Failed to save player {player.get('mlb_id')}: {e}")
    
    async def _save_game(self, game: Dict):
        """Save game to database"""
        try:
            home_team_uuid = await self._get_team_uuid_by_mlb_id(game['home_team_id'])
            away_team_uuid = await self._get_team_uuid_by_mlb_id(game['away_team_id'])
            
            await self.db_pool.execute("""
                INSERT INTO games (game_id, game_date, home_team_id, away_team_id,
                                 season, status, final_score_home, final_score_away)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (game_id) DO UPDATE
                SET final_score_home = EXCLUDED.final_score_home,
                    final_score_away = EXCLUDED.final_score_away
            """, str(game['game_pk']), game['game_date'].date(),
                home_team_uuid, away_team_uuid, game['game_date'].year,
                'completed', game.get('home_score'), game.get('away_score'))
            
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
        for mlb_id, abbrev in self._team_cache.items():
            if abbrev == team_abbrev:
                return mlb_id
        
        # Not in cache, fetch from API
        data = await self._get("/teams", {"sportId": 1})
        for team in data.get("teams", []):
            if team.get("abbreviation", "").lower() == team_abbrev:
                self._team_cache[team["id"]] = team_abbrev
                return team["id"]
        
        return None
    
    async def _get_team_uuid_by_mlb_id(self, mlb_id: int) -> Optional[str]:
        """Get our team UUID from MLB team ID"""
        if mlb_id in self._team_cache:
            team_id = self._team_cache[mlb_id]
        else:
            try:
                data = await self._get(f"/teams/{mlb_id}")
                team = data.get("teams", [{}])[0]
                team_id = team.get("abbreviation", "").lower()
                self._team_cache[mlb_id] = team_id
            except:
                return None
        
        return await self.db_pool.fetchval(
            "SELECT id FROM teams WHERE team_id = $1", team_id
        )
    
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