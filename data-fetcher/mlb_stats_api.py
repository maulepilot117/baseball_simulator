"""
MLB Stats API Complete Data Fetcher
This module handles all data fetching using only the official MLB Stats API
"""

import asyncio
import logging
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
import json
from dataclasses import dataclass
from enum import Enum

import asyncpg
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from advanced_stats import AdvancedStatsCalculator
from fielding_metrics import FieldingMetricsCalculator
from position_specific_metrics import PositionSpecificMetrics
from network_resilience import NetworkResilientClient, MLB_API_CIRCUIT_BREAKER, with_circuit_breaker
from data_consistency import DataConsistencyValidator, run_daily_consistency_check
from performance_monitoring import monitor_performance, MetricType, initialize_monitoring, get_performance_manager
from input_validation import InputValidator, SecuritySanitizer

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for data validation errors"""
    pass


class DataValidator:
    """Data validation utility class"""
    
    @staticmethod
    def validate_team_data(team: Dict) -> Dict:
        """Validate team data before database insertion"""
        required_fields = ['id', 'name', 'abbreviation']
        errors = []
        
        # Check required fields
        for field in required_fields:
            if not team.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate specific fields
        if team.get('abbreviation'):
            if len(team['abbreviation']) > 5:
                errors.append("Team abbreviation too long (max 5 chars)")
            if not re.match(r'^[A-Z]+$', team['abbreviation']):
                errors.append("Team abbreviation must be uppercase letters only")
        
        if team.get('name') and len(team['name']) > 100:
            errors.append("Team name too long (max 100 chars)")
        
        if team.get('league', {}).get('name') and team['league']['name'] not in ['American League', 'National League']:
            errors.append(f"Invalid league: {team['league']['name']}")
        
        if errors:
            raise ValidationError(f"Team validation failed: {'; '.join(errors)}")
        
        return team
    
    @staticmethod
    def validate_venue_data(venue: Dict) -> Dict:
        """Validate venue/stadium data"""
        required_fields = ['id', 'name']
        errors = []
        
        for field in required_fields:
            if not venue.get(field):
                errors.append(f"Missing required field: {field}")
        
        if venue.get('name') and len(venue['name']) > 200:
            errors.append("Venue name too long (max 200 chars)")
        
        if venue.get('capacity') and not isinstance(venue['capacity'], int):
            try:
                venue['capacity'] = int(venue['capacity'])
            except (ValueError, TypeError):
                errors.append("Invalid capacity value")
        
        if errors:
            raise ValidationError(f"Venue validation failed: {'; '.join(errors)}")
        
        return venue
    
    @staticmethod
    def validate_player_data(player: Dict) -> Dict:
        """Validate player data"""
        required_fields = ['mlb_id', 'first_name', 'last_name']
        errors = []
        
        for field in required_fields:
            if not player.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate names
        if player.get('first_name') and len(player['first_name']) > 100:
            errors.append("First name too long (max 100 chars)")
        if player.get('last_name') and len(player['last_name']) > 100:
            errors.append("Last name too long (max 100 chars)")
        
        # Validate position
        valid_positions = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'OF', 'IF']
        if player.get('position') and player['position'] not in valid_positions:
            logger.warning(f"Unusual position for player {player.get('mlb_id')}: {player['position']}")
        
        # Validate bat/throw hands
        valid_hands = ['L', 'R', 'S']  # S for switch
        if player.get('bats') and player['bats'] not in valid_hands:
            errors.append(f"Invalid batting hand: {player['bats']}")
        if player.get('throws') and player['throws'] not in valid_hands:
            errors.append(f"Invalid throwing hand: {player['throws']}")
        
        # Validate birth date
        if player.get('birth_date'):
            try:
                birth_date = datetime.strptime(player['birth_date'], '%Y-%m-%d').date()
                if birth_date > date.today():
                    errors.append("Birth date cannot be in the future")
                if birth_date < date(1900, 1, 1):
                    errors.append("Birth date too old")
            except ValueError:
                errors.append("Invalid birth date format")
        
        if errors:
            raise ValidationError(f"Player validation failed: {'; '.join(errors)}")
        
        return player
    
    @staticmethod
    def validate_game_data(game: Dict) -> Dict:
        """Validate game data"""
        required_fields = ['game_pk', 'game_date', 'home_team_id', 'away_team_id']
        errors = []
        
        for field in required_fields:
            if not game.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate game date
        if isinstance(game.get('game_date'), datetime):
            if game['game_date'].date() > date.today() + timedelta(days=365):
                errors.append("Game date too far in future")
            if game['game_date'].date() < date(1900, 1, 1):
                errors.append("Game date too old")
        
        # Validate scores
        for score_field in ['home_score', 'away_score']:
            if game.get(score_field) is not None:
                try:
                    score = int(game[score_field])
                    if score < 0 or score > 50:  # Reasonable bounds
                        errors.append(f"Invalid {score_field}: {score}")
                    game[score_field] = score
                except (ValueError, TypeError):
                    errors.append(f"Invalid {score_field} format")
        
        # Validate teams are different
        if game.get('home_team_id') == game.get('away_team_id'):
            errors.append("Home and away teams cannot be the same")
        
        if errors:
            raise ValidationError(f"Game validation failed: {'; '.join(errors)}")
        
        return game
    
    @staticmethod
    def validate_pitch_data(pitch: Dict) -> Dict:
        """Validate pitch data"""
        required_fields = ['game_pk', 'pitcher_id', 'batter_id', 'inning']
        errors = []
        
        for field in required_fields:
            if not pitch.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate inning
        if pitch.get('inning'):
            try:
                inning = int(pitch['inning'])
                if inning < 1 or inning > 20:  # Max reasonable inning
                    errors.append(f"Invalid inning: {inning}")
                pitch['inning'] = inning
            except (ValueError, TypeError):
                errors.append("Invalid inning format")
        
        # Validate inning half
        if pitch.get('inning_half') and pitch['inning_half'] not in ['top', 'bottom']:
            errors.append(f"Invalid inning_half: {pitch['inning_half']}")
        
        # Validate velocity
        if pitch.get('velocity') is not None:
            try:
                velocity = float(pitch['velocity'])
                if velocity < 40 or velocity > 110:  # Reasonable bounds for MLB
                    errors.append(f"Invalid velocity: {velocity}")
                pitch['velocity'] = velocity
            except (ValueError, TypeError):
                errors.append("Invalid velocity format")
        
        # Validate spin rate
        if pitch.get('spin_rate') is not None:
            try:
                spin_rate = int(pitch['spin_rate'])
                if spin_rate < 0 or spin_rate > 4000:
                    errors.append(f"Invalid spin_rate: {spin_rate}")
                pitch['spin_rate'] = spin_rate
            except (ValueError, TypeError):
                errors.append("Invalid spin_rate format")
        
        # Validate exit velocity
        if pitch.get('exit_velocity') is not None:
            try:
                exit_velocity = float(pitch['exit_velocity'])
                if exit_velocity < 0 or exit_velocity > 130:
                    errors.append(f"Invalid exit_velocity: {exit_velocity}")
                pitch['exit_velocity'] = exit_velocity
            except (ValueError, TypeError):
                errors.append("Invalid exit_velocity format")
        
        # Validate launch angle
        if pitch.get('launch_angle') is not None:
            try:
                launch_angle = float(pitch['launch_angle'])
                if launch_angle < -90 or launch_angle > 90:
                    errors.append(f"Invalid launch_angle: {launch_angle}")
                pitch['launch_angle'] = launch_angle
            except (ValueError, TypeError):
                errors.append("Invalid launch_angle format")
        
        if errors:
            raise ValidationError(f"Pitch validation failed: {'; '.join(errors)}")
        
        return pitch
    
    @staticmethod
    def validate_stats_data(stats: Dict, stats_type: str) -> Dict:
        """Validate player statistics data"""
        errors = []
        
        if stats_type == 'batting':
            # Validate batting stats
            numeric_fields = ['AB', 'R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'SO', 'SB', 'CS', 'G', 'HBP', 'SF', 'SH', 'GIDP', 'TB', 'XBH', 'PA']
            for field in numeric_fields:
                if field in stats:
                    try:
                        stats[field] = int(stats[field])
                        if stats[field] < 0:
                            errors.append(f"Negative {field}: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
            
            # Validate rate stats
            rate_fields = ['AVG', 'OBP', 'SLG', 'OPS', 'wOBA', 'ISO', 'BABIP']
            for field in rate_fields:
                if field in stats and stats[field] is not None:
                    try:
                        rate_val = float(stats[field])
                        if field == 'OPS' and (rate_val < 0 or rate_val > 4.0):
                            errors.append(f"Invalid {field}: {rate_val}")
                        elif field != 'OPS' and (rate_val < 0 or rate_val > 1.0):
                            errors.append(f"Invalid {field}: {rate_val}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
            
            # Validate special integer fields
            special_int_fields = ['wRC_plus']
            for field in special_int_fields:
                if field in stats and stats[field] is not None:
                    try:
                        stats[field] = int(stats[field])
                        if stats[field] < 0 or stats[field] > 300:
                            errors.append(f"Invalid {field}: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
        
        elif stats_type == 'pitching':
            # Validate pitching stats
            numeric_fields = ['W', 'L', 'SV', 'H', 'R', 'ER', 'BB', 'SO', 'HR', 'Pitches', 'G', 'GS', 'CG', 'SHO', 'HLD', 'BS', 'IBB', 'HBP', 'BK', 'WP']
            for field in numeric_fields:
                if field in stats:
                    try:
                        stats[field] = int(stats[field])
                        if stats[field] < 0:
                            errors.append(f"Negative {field}: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
            
            # Validate float fields for pitching
            float_fields = ['IP', 'ERA', 'WHIP', 'K9', 'BB9', 'H9', 'HR9', 'K_BB', 'BABIP', 'LOB_PCT', 'FIP', 'xFIP']
            for field in float_fields:
                if field in stats and stats[field] is not None:
                    try:
                        stats[field] = float(stats[field])
                        if field == 'ERA' and (stats[field] < 0 or stats[field] > 20):
                            errors.append(f"Invalid ERA: {stats[field]}")
                        elif field == 'WHIP' and (stats[field] < 0 or stats[field] > 5):
                            errors.append(f"Invalid WHIP: {stats[field]}")
                        elif field in ['BABIP', 'LOB_PCT'] and (stats[field] < 0 or stats[field] > 1):
                            errors.append(f"Invalid {field}: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
            
            # Validate special integer fields
            special_int_fields = ['wRC_plus', 'ERA_plus']
            for field in special_int_fields:
                if field in stats and stats[field] is not None:
                    try:
                        stats[field] = int(stats[field])
                        if stats[field] < 0 or stats[field] > 300:
                            errors.append(f"Invalid {field}: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
        
        elif stats_type == 'fielding':
            # Validate fielding stats
            numeric_fields = ['G', 'GS', 'PO', 'A', 'E', 'TC', 'DP', 'TP', 'PB', 'SB', 'CS', 'SBA']
            for field in numeric_fields:
                if field in stats:
                    try:
                        stats[field] = int(stats[field])
                        if stats[field] < 0:
                            errors.append(f"Negative {field}: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
            
            # Validate float fields for fielding
            float_fields = ['INN', 'FPCT', 'RF', 'CSP']
            for field in float_fields:
                if field in stats and stats[field] is not None:
                    try:
                        stats[field] = float(stats[field])
                        if field == 'FPCT' and (stats[field] < 0 or stats[field] > 1):
                            errors.append(f"Invalid fielding percentage: {stats[field]}")
                        elif field == 'CSP' and (stats[field] < 0 or stats[field] > 100):
                            errors.append(f"Invalid caught stealing percentage: {stats[field]}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid {field} format")
        
        # Additional validation for season stats
        if 'G' in stats and stats['G'] > 162:  # MLB regular season max
            errors.append(f"Invalid games played: {stats['G']}")
        
        if 'AB' in stats and 'H' in stats and stats['AB'] > 0 and stats['H'] > stats['AB']:
            errors.append(f"Hits ({stats['H']}) cannot exceed at-bats ({stats['AB']})")
        
        if 'IP' in stats and stats['IP'] > 300:  # Reasonable season limit
            errors.append(f"Invalid innings pitched: {stats['IP']}")
        
        # Fielding validation
        if 'TC' in stats and 'PO' in stats and 'A' in stats and 'E' in stats:
            expected_tc = stats['PO'] + stats['A'] + stats['E']
            if abs(stats['TC'] - expected_tc) > 5:  # Allow small discrepancy
                errors.append(f"Total chances mismatch: TC={stats['TC']}, PO+A+E={expected_tc}")
        
        if errors:
            raise ValidationError(f"{stats_type.title()} stats validation failed: {'; '.join(errors)}")
        
        return stats


class SportId(Enum):
    """MLB Sport IDs"""
    MLB = 1
    TRIPLE_A = 11
    DOUBLE_A = 12
    SINGLE_A = 13
    ROOKIE = 14


@dataclass
class TeamInfo:
    """Team information"""
    id: int
    name: str
    abbreviation: str
    division: str
    league: str
    venue_id: int
    venue_name: str


class MLBStatsAPI:
    """Complete MLB Stats API Client"""
    
    BASE_URL = "https://statsapi.mlb.com/api/v1"
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        
        # Initialize resilient HTTP client
        self.client = NetworkResilientClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            rate_limit_requests=100,  # 100 requests per minute
            rate_limit_window=60
        )
        
        # Legacy client for backward compatibility
        self.legacy_client = httpx.AsyncClient(
            timeout=30.0,
            headers={'User-Agent': 'BaseballSimulation/2.0'}
        )
        
        # Cache for performance
        self._team_cache: Dict[int, str] = {}  # MLB ID -> our ID
        self._player_cache: Dict[int, str] = {}  # MLB ID -> our ID
        
        # Statistical calculators
        self.advanced_stats_calc = AdvancedStatsCalculator(db_pool)
        self.fielding_calc = FieldingMetricsCalculator(db_pool)
        self.position_specific_calc = PositionSpecificMetrics(db_pool)
        
        # Data validation and consistency
        self.validator = InputValidator()
        self.sanitizer = SecuritySanitizer()
        self.consistency_validator = DataConsistencyValidator(db_pool)
        
        # Performance monitoring
        self.performance_manager = initialize_monitoring(db_pool) if get_performance_manager() is None else get_performance_manager()
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()
        await self.legacy_client.aclose()
        if self.performance_manager:
            await self.performance_manager.stop_monitoring()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    @monitor_performance("mlb_api_request", MetricType.TIMER)
    @with_circuit_breaker(MLB_API_CIRCUIT_BREAKER)
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to API with resilience features"""
        try:
            # Use resilient client for new requests
            response = await self.client.get(endpoint, params=params)
            return response.json()
            
        except Exception as e:
            logger.error(f"Resilient request failed for {endpoint}: {str(e)}")
            
            # Fallback to legacy client for compatibility
            try:
                url = f"{self.BASE_URL}{endpoint}"
                response = await self.legacy_client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as fallback_error:
                logger.error(f"Fallback request also failed: {str(fallback_error)}")
                raise e  # Raise original error
    
    @monitor_performance("fetch_all_data", MetricType.TIMER)
    async def fetch_all_data(self, start_date: datetime, end_date: datetime):
        """Main entry point to fetch all data"""
        logger.info(f"Starting MLB Stats API fetch from {start_date} to {end_date}")
        
        # Start performance monitoring if not already started
        if self.performance_manager and not self.performance_manager.system_monitor._monitoring:
            await self.performance_manager.start_monitoring()
        
        # 1. Fetch teams and venues
        await self.fetch_teams_and_venues()
        
        # 2. Fetch all players (current rosters)
        await self.fetch_all_players()
        
        # 3. Fetch games and detailed data
        await self.fetch_games_with_details(start_date, end_date)
        
        # 4. Fetch player stats
        current_year = datetime.now().year
        await self.fetch_player_stats(current_year)
        
        # 5. Calculate advanced statistics
        await self.calculate_advanced_stats_for_season(current_year)
        
        # 6. Calculate fielding statistics
        await self.calculate_fielding_stats_for_season(current_year)
        
        # 7. Run data consistency validation
        try:
            season = start_date.year if start_date.year == end_date.year else None
            validation_report = await self.consistency_validator.run_full_validation(season)
            
            if validation_report.summary['critical'] > 0:
                logger.critical(f"CRITICAL: {validation_report.summary['critical']} critical data issues found!")
            elif validation_report.summary['error'] > 0:
                logger.error(f"WARNING: {validation_report.summary['error']} data errors found")
            else:
                logger.info(f"Data validation passed with {validation_report.summary['warning']} warnings")
                
        except Exception as e:
            logger.error(f"Data consistency validation failed: {e}")
        
        logger.info("MLB Stats API fetch completed with advanced statistics and fielding metrics")
    
    async def fetch_teams_and_venues(self):
        """Fetch all teams and their venues"""
        logger.info("Fetching teams and venues...")
        
        # Get all MLB teams
        data = await self._get("/teams", {"sportId": SportId.MLB.value})
        teams = data.get("teams", [])
        
        # First, fetch all unique venues
        venues = {}
        for team in teams:
            if team.get("active", False):
                venue = team.get("venue", {})
                if venue.get("id"):
                    venues[venue["id"]] = venue
        
        # Save venues (stadiums)
        for venue_id, venue in venues.items():
            await self._save_venue(venue)
        
        # Save teams
        for team in teams:
            if team.get("active", False):
                await self._save_team(team)
        
        logger.info(f"Saved {len(teams)} teams and {len(venues)} venues")
    
    async def fetch_all_players(self):
        """Fetch all players from current rosters"""
        logger.info("Fetching all players...")
        
        # Get all teams from database
        teams = await self.db_pool.fetch("SELECT team_id FROM teams")
        
        # Fetch roster for each team
        tasks = []
        for team in teams:
            # Our team_id is like 'nyy', MLB uses numbers
            mlb_team_id = await self._get_mlb_team_id(team['team_id'])
            if mlb_team_id:
                tasks.append(self.fetch_team_roster(mlb_team_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_players = sum(len(r) for r in results if isinstance(r, list))
        logger.info(f"Fetched {total_players} total players")
    
    async def fetch_team_roster(self, team_id: int) -> List[Dict]:
        """Fetch roster for a specific team"""
        try:
            # Get 40-man roster
            data = await self._get(f"/teams/{team_id}/roster", {
                "rosterType": "40Man"
            })
            
            roster = data.get("roster", [])
            players = []
            
            for entry in roster:
                person = entry.get("person", {})
                player_data = {
                    'mlb_id': person.get("id"),
                    'full_name': person.get("fullName"),
                    'first_name': person.get("firstName"),
                    'last_name': person.get("lastName"),
                    'position': entry.get("position", {}).get("abbreviation"),
                    'jersey_number': entry.get("jerseyNumber"),
                    'status': entry.get("status", {}).get("code", "Active"),
                    'team_id': team_id
                }
                
                # Get additional player details
                if player_data['mlb_id']:
                    details = await self._get_player_details(player_data['mlb_id'])
                    player_data.update(details)
                
                players.append(player_data)
                await self._save_player(player_data)
            
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
                'debut_date': person.get("mlbDebutDate")
            }
        except:
            return {}
    
    async def fetch_games_with_details(self, start_date: datetime, end_date: datetime):
        """Fetch games with play-by-play data"""
        logger.info(f"Fetching games from {start_date} to {end_date}...")
        
        current_date = start_date
        all_games = []
        
        while current_date <= end_date:
            games = await self._fetch_games_for_date(current_date)
            all_games.extend(games)
            current_date += timedelta(days=1)
            await asyncio.sleep(0.5)  # Rate limiting
        
        logger.info(f"Found {len(all_games)} total games")
        
        # Fetch detailed data for each game
        for i, game in enumerate(all_games):
            if game['status'] == 'Final':
                logger.info(f"Fetching details for game {i+1}/{len(all_games)}")
                await self._fetch_game_details(game['game_pk'], game['game_date'])
                await asyncio.sleep(0.5)  # Rate limiting
    
    async def _fetch_games_for_date(self, date: datetime) -> List[Dict]:
        """Fetch all games for a specific date"""
        date_str = date.strftime("%Y-%m-%d")
        
        try:
            data = await self._get("/schedule", {
                "sportId": SportId.MLB.value,
                "date": date_str
            })
            
            games = []
            for date_data in data.get("dates", []):
                for game in date_data.get("games", []):
                    game_info = {
                        'game_pk': game.get("gamePk"),
                        'game_date': date,
                        'game_time': game.get("gameDate"),
                        'home_team_id': game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                        'away_team_id': game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                        'venue_id': game.get("venue", {}).get("id"),
                        'status': game.get("status", {}).get("detailedState"),
                        'home_score': game.get("teams", {}).get("home", {}).get("score"),
                        'away_score': game.get("teams", {}).get("away", {}).get("score")
                    }
                    
                    games.append(game_info)
                    await self._save_game(game_info)
            
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games for {date_str}: {e}")
            return []
    
    async def _fetch_game_details(self, game_pk: int, game_date: datetime):
        """Fetch detailed game data including play-by-play"""
        try:
            # Get game content (includes everything)
            data = await self._get(f"/game/{game_pk}/content")
            
            # Get play-by-play data
            pbp_data = await self._get(f"/game/{game_pk}/playByPlay")
            
            # Extract weather data
            weather = data.get("gameData", {}).get("weather", {})
            await self._update_game_weather(game_pk, weather)
            
            # Extract and save pitch data
            await self._process_play_by_play(game_pk, pbp_data, game_date)
            
            # Get and save box score data
            box_data = await self._get(f"/game/{game_pk}/boxscore")
            await self._process_box_score(game_pk, box_data, game_date)
            
        except Exception as e:
            logger.error(f"Error fetching details for game {game_pk}: {e}")
    
    async def _process_play_by_play(self, game_pk: int, pbp_data: Dict, game_date: datetime):
        """Process play-by-play data to extract pitches"""
        all_plays = pbp_data.get("allPlays", [])
        pitches = []
        
        for play in all_plays:
            inning = play.get("about", {}).get("inning", 0)
            is_top = play.get("about", {}).get("isTopInning", True)
            inning_half = "top" if is_top else "bottom"
            
            pitcher_id = play.get("matchup", {}).get("pitcher", {}).get("id")
            batter_id = play.get("matchup", {}).get("batter", {}).get("id")
            
            # Process each pitch in the at-bat
            for i, event in enumerate(play.get("playEvents", [])):
                if event.get("isPitch", False):
                    pitch_data = self._extract_pitch_data(
                        event, game_pk, pitcher_id, batter_id,
                        inning, inning_half, i + 1, game_date
                    )
                    if pitch_data:  # Only add valid pitch data
                        pitches.append(pitch_data)
        
        # Save pitches in batches
        if pitches:
            await self._save_pitches(pitches)
            logger.info(f"Saved {len(pitches)} pitches for game {game_pk}")
    
    def _extract_pitch_data(self, event: Dict, game_pk: int, pitcher_id: int,
                           batter_id: int, inning: int, inning_half: str,
                           pitch_number: int, game_date: datetime) -> Optional[Dict]:
        """Extract pitch data from play event"""
        try:
            pitch_data = event.get("pitchData", {})
            details = event.get("details", {})
            
            raw_pitch = {
                'game_pk': game_pk,
                'pitcher_id': pitcher_id,
                'batter_id': batter_id,
                'game_date': game_date,
                'inning': inning,
                'inning_half': inning_half,
                'pitch_number': pitch_number,
                'pitch_type': details.get("type", {}).get("code"),
                'pitch_description': details.get("type", {}).get("description"),
                'velocity': pitch_data.get("startSpeed"),
                'end_velocity': pitch_data.get("endSpeed"),
                'spin_rate': pitch_data.get("breaks", {}).get("spinRate"),
                'spin_direction': pitch_data.get("breaks", {}).get("spinDirection"),
                'px': pitch_data.get("coordinates", {}).get("pX"),
                'pz': pitch_data.get("coordinates", {}).get("pZ"),
                'x0': pitch_data.get("coordinates", {}).get("x0"),
                'y0': pitch_data.get("coordinates", {}).get("y0"),
                'z0': pitch_data.get("coordinates", {}).get("z0"),
                'result': details.get("description"),
                'code': details.get("code"),
                'balls': details.get("ballColor", 0),
                'strikes': details.get("strikeColor", 0),
                'exit_velocity': event.get("hitData", {}).get("launchSpeed"),
                'launch_angle': event.get("hitData", {}).get("launchAngle"),
                'hit_distance': event.get("hitData", {}).get("totalDistance"),
                'hit_coordinates': event.get("hitData", {}).get("coordinates")
            }
            
            # Validate the pitch data
            return DataValidator.validate_pitch_data(raw_pitch)
            
        except ValidationError as e:
            logger.warning(f"Invalid pitch data in game {game_pk}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting pitch data: {e}")
            return None
    
    async def _process_box_score(self, game_pk: int, box_data: Dict, game_date: datetime):
        """Process box score data for player game stats"""
        teams = box_data.get("teams", {})
        
        for team_side in ["home", "away"]:
            team_data = teams.get(team_side, {})
            
            # Process batting stats
            batters = team_data.get("batters", [])
            for batter_id in batters:
                stats = team_data.get("players", {}).get(f"ID{batter_id}", {}).get("stats", {})
                batting = stats.get("batting", {})
                if batting:
                    await self._save_batting_stats(batter_id, game_pk, game_date, batting)
            
            # Process pitching stats
            pitchers = team_data.get("pitchers", [])
            for pitcher_id in pitchers:
                stats = team_data.get("players", {}).get(f"ID{pitcher_id}", {}).get("stats", {})
                pitching = stats.get("pitching", {})
                if pitching:
                    await self._save_pitching_stats(pitcher_id, game_pk, game_date, pitching)
    
    async def fetch_player_stats(self, season: int):
        """Fetch season stats for all players"""
        logger.info(f"Fetching player stats for {season} season...")
        
        # Get all players
        players = await self.db_pool.fetch("""
            SELECT p.id, p.player_id, pm.mlb_id::int
            FROM players p
            JOIN player_mlb_mapping pm ON p.id = pm.player_id
            WHERE p.status = 'active'
        """)
        
        # Fetch stats for each player (remove limit for production)
        total_players = len(players)
        logger.info(f"Processing season stats for {total_players} players")
        
        for i, player in enumerate(players):
            mlb_id = player['mlb_id']
            
            if i % 50 == 0:  # Progress logging
                logger.info(f"Processing player {i+1}/{total_players}")
            
            # Fetch hitting stats
            try:
                hitting = await self._get(f"/people/{mlb_id}/stats", {
                    "stats": "season",
                    "group": "hitting",
                    "season": season
                })
                await self._process_season_stats(player['id'], hitting, 'batting', season)
            except:
                pass
            
            # Fetch pitching stats
            try:
                pitching = await self._get(f"/people/{mlb_id}/stats", {
                    "stats": "season",
                    "group": "pitching", 
                    "season": season
                })
                await self._process_season_stats(player['id'], pitching, 'pitching', season)
            except:
                pass
            
            # Fetch fielding stats
            try:
                fielding = await self._get(f"/people/{mlb_id}/stats", {
                    "stats": "season",
                    "group": "fielding", 
                    "season": season
                })
                await self._process_season_stats(player['id'], fielding, 'fielding', season)
            except:
                pass
            
            await asyncio.sleep(0.1)  # Rate limiting
    
    # Database save methods
    async def _save_venue(self, venue: Dict):
        """Save venue (stadium) to database"""
        try:
            # Validate venue data
            validated_venue = DataValidator.validate_venue_data(venue)
            
            await self.db_pool.execute("""
                INSERT INTO stadiums (stadium_id, name, location, capacity, surface, roof_type)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (stadium_id) DO UPDATE
                SET name = EXCLUDED.name,
                    location = EXCLUDED.location,
                    capacity = EXCLUDED.capacity
            """, str(validated_venue.get("id")), validated_venue.get("name"), 
                validated_venue.get("location", {}).get("city", "") + ", " + validated_venue.get("location", {}).get("state", ""),
                validated_venue.get("capacity"), validated_venue.get("surface", {}).get("surfaceType"),
                validated_venue.get("roofType"))
        except ValidationError as e:
            logger.error(f"Skipping invalid venue data: {e}")
        except Exception as e:
            logger.error(f"Failed to save venue {venue.get('id', 'unknown')}: {e}")
    
    @monitor_performance("save_team", MetricType.TIMER)
    async def _save_team(self, team: Dict):
        """Save team to database with enhanced validation"""
        try:
            # Enhanced input validation
            team_name = self.sanitizer.sanitize_string(team.get("name", ""), max_length=100)
            team_abbrev = self.sanitizer.sanitize_string(team.get("abbreviation", ""), max_length=5)
            
            # Validate team data using existing validator
            validated_team = DataValidator.validate_team_data(team)
            
            # Additional baseball-specific validation
            if not self.validator.baseball_validator.validate_team_abbreviation(team_abbrev):
                logger.warning(f"Unusual team abbreviation format: {team_abbrev}")
            
            # Performance metric
            if self.performance_manager:
                self.performance_manager.collector.record_metric(
                    "team_data_processed", 1, MetricType.COUNTER
                )
            
            # Map MLB team ID to our format
            team_abbrev = validated_team.get("abbreviation", "").lower()
            
            # Get venue UUID
            venue_id = await self.db_pool.fetchval("""
                SELECT id FROM stadiums WHERE stadium_id = $1
            """, str(validated_team.get("venue", {}).get("id")))
            
            await self.db_pool.execute("""
                INSERT INTO teams (team_id, name, abbreviation, league, division, stadium_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (team_id) DO UPDATE
                SET name = EXCLUDED.name,
                    league = EXCLUDED.league,
                    division = EXCLUDED.division,
                    stadium_id = EXCLUDED.stadium_id
            """, team_abbrev, validated_team.get("name"), validated_team.get("abbreviation"),
                validated_team.get("league", {}).get("name"), validated_team.get("division", {}).get("name"),
                venue_id)
            
            # Cache the mapping
            self._team_cache[validated_team.get("id")] = team_abbrev
        except ValidationError as e:
            logger.error(f"Skipping invalid team data: {e}")
        except Exception as e:
            logger.error(f"Failed to save team {team.get('id', 'unknown')}: {e}")
    
    async def _save_player(self, player: Dict):
        """Save player to database"""
        try:
            # Validate player data
            validated_player = DataValidator.validate_player_data(player)
            
            # Get team UUID
            team_uuid = await self._get_team_uuid_by_mlb_id(validated_player.get('team_id'))
            
            # Save player
            player_uuid = await self.db_pool.fetchval("""
                INSERT INTO players (player_id, first_name, last_name, birth_date,
                                   position, bats, throws, team_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (player_id) DO UPDATE
                SET first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    team_id = EXCLUDED.team_id,
                    position = EXCLUDED.position,
                    status = EXCLUDED.status
                RETURNING id
            """, f"mlb_{validated_player['mlb_id']}", validated_player.get('first_name'), validated_player.get('last_name'),
                validated_player.get('birth_date'), validated_player.get('position'), validated_player.get('bats'),
                validated_player.get('throws'), team_uuid, validated_player.get('status', 'Active'))
            
            # Save MLB ID mapping
            await self.db_pool.execute("""
                INSERT INTO player_mlb_mapping (player_id, mlb_id)
                VALUES ($1, $2)
                ON CONFLICT (player_id) DO NOTHING
            """, player_uuid, validated_player['mlb_id'])
            
            self._player_cache[validated_player['mlb_id']] = player_uuid
        except ValidationError as e:
            logger.error(f"Skipping invalid player data: {e}")
        except Exception as e:
            logger.error(f"Failed to save player {player.get('mlb_id', 'unknown')}: {e}")
    
    async def _save_game(self, game: Dict):
        """Save game to database"""
        try:
            # Validate game data
            validated_game = DataValidator.validate_game_data(game)
            
            home_team_uuid = await self._get_team_uuid_by_mlb_id(validated_game['home_team_id'])
            away_team_uuid = await self._get_team_uuid_by_mlb_id(validated_game['away_team_id'])
            venue_uuid = await self.db_pool.fetchval("""
                SELECT id FROM stadiums WHERE stadium_id = $1
            """, str(validated_game.get('venue_id')))
            
            await self.db_pool.execute("""
                INSERT INTO games (game_id, game_date, game_time, home_team_id, away_team_id,
                                 stadium_id, season, status, final_score_home, final_score_away)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (game_id) DO UPDATE
                SET status = EXCLUDED.status,
                    final_score_home = EXCLUDED.final_score_home,
                    final_score_away = EXCLUDED.final_score_away
            """, str(validated_game['game_pk']), validated_game['game_date'].date(),
                datetime.fromisoformat(validated_game['game_time'].replace('Z', '+00:00')).time() if validated_game.get('game_time') else None,
                home_team_uuid, away_team_uuid, venue_uuid, validated_game['game_date'].year,
                validated_game['status'], validated_game.get('home_score'), validated_game.get('away_score'))
        except ValidationError as e:
            logger.error(f"Skipping invalid game data: {e}")
        except Exception as e:
            logger.error(f"Failed to save game {game.get('game_pk', 'unknown')}: {e}")
    
    async def _save_pitches(self, pitches: List[Dict]):
        """Save multiple pitches efficiently"""
        # Get game UUID
        if not pitches:
            return
            
        game_uuid = await self.db_pool.fetchval("""
            SELECT id FROM games WHERE game_id = $1
        """, str(pitches[0]['game_pk']))
        
        if not game_uuid:
            logger.warning(f"Game not found for pitches: {pitches[0]['game_pk']}")
            return
        
        # Prepare data for batch insert
        values = []
        for pitch in pitches:
            pitcher_uuid = await self._get_player_uuid_by_mlb_id(pitch['pitcher_id'])
            batter_uuid = await self._get_player_uuid_by_mlb_id(pitch['batter_id'])
            
            if pitcher_uuid and batter_uuid:
                values.append((
                    game_uuid, pitcher_uuid, batter_uuid, pitch['game_date'].date(),
                    pitch['inning'], pitch['inning_half'], pitch['pitch_number'],
                    pitch['pitch_type'], pitch['velocity'], pitch['spin_rate'],
                    json.dumps({
                        'x': pitch.get('x0'), 'y': pitch.get('y0'), 'z': pitch.get('z0')
                    }) if pitch.get('x0') is not None else None,
                    json.dumps({
                        'x': pitch.get('px'), 'z': pitch.get('pz')
                    }) if pitch.get('px') is not None else None,
                    pitch['result'], pitch.get('exit_velocity'),
                    pitch.get('launch_angle'), pitch.get('hit_distance')
                ))
        
        # Batch insert
        if values:
            await self.db_pool.executemany("""
                INSERT INTO pitches (game_id, pitcher_id, batter_id, game_date,
                                   inning, inning_half, pitch_number, pitch_type,
                                   velocity, spin_rate, release_point, plate_location,
                                   result, exit_velocity, launch_angle, hit_distance)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (id, game_date) DO NOTHING
            """, values)
    
    # Helper methods
    async def _get_mlb_team_id(self, team_abbrev: str) -> Optional[int]:
        """Get MLB team ID from our abbreviation"""
        # Reverse lookup from cache
        for mlb_id, abbrev in self._team_cache.items():
            if abbrev == team_abbrev:
                return mlb_id
        
        # If not in cache, fetch from API
        data = await self._get("/teams", {"sportId": SportId.MLB.value})
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
            # Fetch from API if not cached
            try:
                data = await self._get(f"/teams/{mlb_id}")
                team = data.get("teams", [{}])[0]
                team_id = team.get("abbreviation", "").lower()
                self._team_cache[mlb_id] = team_id
            except:
                return None
        
        return await self.db_pool.fetchval("""
            SELECT id FROM teams WHERE team_id = $1
        """, team_id)
    
    async def _get_player_uuid_by_mlb_id(self, mlb_id: int) -> Optional[str]:
        """Get our player UUID from MLB player ID"""
        if mlb_id in self._player_cache:
            return self._player_cache[mlb_id]
        
        # Check database
        player_uuid = await self.db_pool.fetchval("""
            SELECT player_id FROM player_mlb_mapping WHERE mlb_id = $1
        """, mlb_id)
        
        if player_uuid:
            self._player_cache[mlb_id] = player_uuid
        
        return player_uuid
    
    async def _update_game_weather(self, game_pk: int, weather: Dict):
        """Update game with weather data"""
        weather_data = {
            'temperature': weather.get('temp'),
            'condition': weather.get('condition'),
            'wind': weather.get('wind'),
            'wind_direction': weather.get('windDirection', {}).get('code'),
            'wind_speed': weather.get('windSpeed')
        }
        
        await self.db_pool.execute("""
            UPDATE games 
            SET weather_data = $2
            WHERE game_id = $1
        """, str(game_pk), json.dumps(weather_data))
    
    async def _save_batting_stats(self, player_mlb_id: int, game_pk: int, 
                                 game_date: datetime, stats: Dict):
        """Save batting stats for a game"""
        try:
            player_uuid = await self._get_player_uuid_by_mlb_id(player_mlb_id)
            game_uuid = await self.db_pool.fetchval("""
                SELECT id FROM games WHERE game_id = $1
            """, str(game_pk))
            
            if player_uuid and game_uuid:
                # Prepare stats data
                batting_stats = {
                    'AB': stats.get('atBats', 0),
                    'R': stats.get('runs', 0),
                    'H': stats.get('hits', 0),
                    '2B': stats.get('doubles', 0),
                    '3B': stats.get('triples', 0),
                    'HR': stats.get('homeRuns', 0),
                    'RBI': stats.get('rbi', 0),
                    'BB': stats.get('baseOnBalls', 0),
                    'SO': stats.get('strikeOuts', 0),
                    'SB': stats.get('stolenBases', 0),
                    'CS': stats.get('caughtStealing', 0),
                    'AVG': stats.get('avg', '.000'),
                    'OBP': stats.get('obp', '.000'),
                    'SLG': stats.get('slg', '.000'),
                    'OPS': stats.get('ops', '.000')
                }
                
                # Validate stats
                validated_stats = DataValidator.validate_stats_data(batting_stats, 'batting')
                stats_json = json.dumps(validated_stats)
                
                await self.db_pool.execute("""
                    INSERT INTO player_stats (player_id, game_id, season, game_date,
                                            stats_type, stats)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id, season) DO NOTHING
                """, player_uuid, game_uuid, game_date.year, game_date.date(),
                    'batting', stats_json)
        except ValidationError as e:
            logger.error(f"Invalid batting stats for player {player_mlb_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to save batting stats for player {player_mlb_id}: {e}")
    
    async def _save_pitching_stats(self, player_mlb_id: int, game_pk: int,
                                  game_date: datetime, stats: Dict):
        """Save pitching stats for a game"""
        try:
            player_uuid = await self._get_player_uuid_by_mlb_id(player_mlb_id)
            game_uuid = await self.db_pool.fetchval("""
                SELECT id FROM games WHERE game_id = $1
            """, str(game_pk))
            
            if player_uuid and game_uuid:
                # Prepare stats data
                pitching_stats = {
                    'W': 1 if stats.get('wins', 0) > 0 else 0,
                    'L': 1 if stats.get('losses', 0) > 0 else 0,
                    'SV': stats.get('saves', 0),
                    'IP': stats.get('inningsPitched', '0.0'),
                    'H': stats.get('hits', 0),
                    'R': stats.get('runs', 0),
                    'ER': stats.get('earnedRuns', 0),
                    'BB': stats.get('baseOnBalls', 0),
                    'SO': stats.get('strikeOuts', 0),
                    'HR': stats.get('homeRuns', 0),
                    'ERA': stats.get('era', '0.00'),
                    'WHIP': stats.get('whip', '0.00'),
                    'K9': stats.get('strikeoutsPer9Inn', '0.0'),
                    'BB9': stats.get('walksPer9Inn', '0.0'),
                    'Pitches': stats.get('numberOfPitches', 0)
                }
                
                # Validate stats
                validated_stats = DataValidator.validate_stats_data(pitching_stats, 'pitching')
                stats_json = json.dumps(validated_stats)
                
                await self.db_pool.execute("""
                    INSERT INTO player_stats (player_id, game_id, season, game_date,
                                            stats_type, stats)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id, season) DO NOTHING
                """, player_uuid, game_uuid, game_date.year, game_date.date(),
                    'pitching', stats_json)
        except ValidationError as e:
            logger.error(f"Invalid pitching stats for player {player_mlb_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to save pitching stats for player {player_mlb_id}: {e}")
    
    async def _process_season_stats(self, player_uuid: str, stats_data: Dict,
                                   stats_type: str, season: int):
        """Process and save season statistics"""
        try:
            stats_list = stats_data.get("stats", [])
            if not stats_list:
                logger.warning(f"No season stats found for player {player_uuid}")
                return
            
            # Get the season stats (should be first item for season stats)
            season_stats = stats_list[0].get("splits", [])
            if not season_stats:
                logger.warning(f"No season splits found for player {player_uuid}")
                return
            
            # Process each split (usually just one for season totals)
            for split in season_stats:
                split_stats = split.get("stat", {})
                if not split_stats:
                    continue
                
                # Process based on stats type
                if stats_type == 'batting':
                    aggregated_stats = await self._aggregate_batting_season_stats(split_stats)
                elif stats_type == 'pitching':
                    aggregated_stats = await self._aggregate_pitching_season_stats(split_stats)
                elif stats_type == 'fielding':
                    aggregated_stats = await self._aggregate_fielding_season_stats(split_stats)
                else:
                    logger.warning(f"Unsupported stats type: {stats_type}")
                    continue
                
                # Validate the aggregated stats
                validated_stats = DataValidator.validate_stats_data(aggregated_stats, stats_type)
                
                # Save to season aggregates table
                await self._save_season_aggregate_stats(
                    player_uuid, season, stats_type, validated_stats,
                    split_stats.get('gamesPlayed', 0)
                )
                
                # Calculate and add advanced stats
                await self._add_advanced_stats_to_player(player_uuid, season, stats_type)
                
                logger.info(f"Processed {stats_type} season stats with advanced metrics for player {player_uuid}, season {season}")
                
        except ValidationError as e:
            logger.error(f"Invalid season stats for player {player_uuid}: {e}")
        except Exception as e:
            logger.error(f"Failed to process season stats for player {player_uuid}: {e}")
    
    async def _add_advanced_stats_to_player(self, player_uuid: str, season: int, stats_type: str):
        """Add advanced statistics to a player's season stats"""
        try:
            if stats_type == 'fielding':
                await self.fielding_calc.update_player_fielding_stats(player_uuid, season)
                
                # Add position-specific metrics for catchers and outfielders
                player_info = await self.db_pool.fetchrow(
                    "SELECT position FROM players WHERE id = $1", player_uuid
                )
                if player_info and player_info['position'] in ['C', 'LF', 'CF', 'RF']:
                    await self.position_specific_calc.update_position_specific_stats(
                        player_uuid, season, player_info['position']
                    )
                    logger.info(f"Added position-specific stats for {player_info['position']} {player_uuid}")
            else:
                await self.advanced_stats_calc.update_player_advanced_stats(player_uuid, season, stats_type)
        except Exception as e:
            logger.error(f"Failed to add advanced stats for player {player_uuid}: {e}")
    
    async def _aggregate_batting_season_stats(self, stats: Dict) -> Dict:
        """Aggregate batting season statistics"""
        return {
            # Counting stats
            'G': stats.get('gamesPlayed', 0),
            'AB': stats.get('atBats', 0),
            'R': stats.get('runs', 0),
            'H': stats.get('hits', 0),
            '2B': stats.get('doubles', 0),
            '3B': stats.get('triples', 0),
            'HR': stats.get('homeRuns', 0),
            'RBI': stats.get('rbi', 0),
            'BB': stats.get('baseOnBalls', 0),
            'SO': stats.get('strikeOuts', 0),
            'SB': stats.get('stolenBases', 0),
            'CS': stats.get('caughtStealing', 0),
            'HBP': stats.get('hitByPitch', 0),
            'SF': stats.get('sacFlies', 0),
            'SH': stats.get('sacBunts', 0),
            'GIDP': stats.get('groundIntoDoublePlay', 0),
            
            # Rate stats
            'AVG': float(stats.get('avg', '0.000')),
            'OBP': float(stats.get('obp', '0.000')),
            'SLG': float(stats.get('slg', '0.000')),
            'OPS': float(stats.get('ops', '0.000')),
            'wOBA': float(stats.get('woba', '0.000')) if stats.get('woba') else None,
            'wRC_plus': int(stats.get('wrcPlus', 0)) if stats.get('wrcPlus') else None,
            
            # Advanced stats
            'ISO': float(stats.get('iso', '0.000')) if stats.get('iso') else None,
            'BABIP': float(stats.get('babip', '0.000')) if stats.get('babip') else None,
            'TB': stats.get('totalBases', 0),
            'XBH': stats.get('extraBaseHits', 0),
            
            # Plate appearances
            'PA': stats.get('plateAppearances', 0),
        }
    
    async def _aggregate_pitching_season_stats(self, stats: Dict) -> Dict:
        """Aggregate pitching season statistics"""
        return {
            # Counting stats
            'G': stats.get('gamesPlayed', 0),
            'GS': stats.get('gamesStarted', 0),
            'W': stats.get('wins', 0),
            'L': stats.get('losses', 0),
            'SV': stats.get('saves', 0),
            'CG': stats.get('completeGames', 0),
            'SHO': stats.get('shutouts', 0),
            'HLD': stats.get('holds', 0),
            'BS': stats.get('blownSaves', 0),
            'IP': float(stats.get('inningsPitched', '0.0')),
            'H': stats.get('hits', 0),
            'R': stats.get('runs', 0),
            'ER': stats.get('earnedRuns', 0),
            'HR': stats.get('homeRuns', 0),
            'BB': stats.get('baseOnBalls', 0),
            'IBB': stats.get('intentionalWalks', 0),
            'SO': stats.get('strikeOuts', 0),
            'HBP': stats.get('hitBatsmen', 0),
            'BK': stats.get('balks', 0),
            'WP': stats.get('wildPitches', 0),
            
            # Rate stats
            'ERA': float(stats.get('era', '0.00')),
            'WHIP': float(stats.get('whip', '0.00')),
            'K9': float(stats.get('strikeoutsPer9Inn', '0.0')),
            'BB9': float(stats.get('walksPer9Inn', '0.0')),
            'H9': float(stats.get('hitsPer9Inn', '0.0')),
            'HR9': float(stats.get('homeRunsPer9Inn', '0.0')),
            
            # Advanced stats
            'K_BB': float(stats.get('strikeoutWalkRatio', '0.0')),
            'BABIP': float(stats.get('babip', '0.000')) if stats.get('babip') else None,
            'LOB_PCT': float(stats.get('leftOnBasePct', '0.0')) if stats.get('leftOnBasePct') else None,
            'ERA_plus': int(stats.get('eraPlus', 0)) if stats.get('eraPlus') else None,
            'FIP': float(stats.get('fip', '0.00')) if stats.get('fip') else None,
            'xFIP': float(stats.get('xfip', '0.00')) if stats.get('xfip') else None,
            
            # Pitches
            'Pitches': stats.get('numberOfPitches', 0),
            'Strikes': stats.get('strikes', 0) if stats.get('strikes') else None,
        }
    
    async def _aggregate_fielding_season_stats(self, stats: Dict) -> Dict:
        """Aggregate fielding season statistics"""
        return {
            # Basic fielding stats
            'G': stats.get('gamesPlayed', 0),
            'GS': stats.get('gamesStarted', 0),
            'INN': float(stats.get('innings', '0.0')),
            'PO': stats.get('putOuts', 0),
            'A': stats.get('assists', 0),
            'E': stats.get('errors', 0),
            'TC': stats.get('chances', 0),  # Total chances
            'DP': stats.get('doublePlays', 0),
            'TP': stats.get('triplePlays', 0),
            'PB': stats.get('passedBalls', 0),  # Catchers only
            'SB': stats.get('stolenBases', 0),  # Allowed by catchers
            'CS': stats.get('caughtStealing', 0),  # By catchers
            
            # Calculated stats
            'FPCT': float(stats.get('fielding', '0.000')),  # Fielding percentage
            'RF': float(stats.get('rangeFactorPerGame', '0.00')),  # Range factor
            
            # Position-specific
            'SBA': stats.get('stolenBaseAttempts', 0),  # Stolen base attempts against (C)
            'CSP': float(stats.get('caughtStealingPercentage', '0.0')) if stats.get('caughtStealingPercentage') else None,
            
            # Advanced placeholders (calculated later)
            'UZR': None,
            'DRS': None,
            'FPCT_PLUS': None,
            'ARM': None,
            'POS_ADJ': None
        }
    
    async def _save_season_aggregate_stats(self, player_uuid: str, season: int, 
                                         stats_type: str, aggregated_stats: Dict, 
                                         games_played: int):
        """Save aggregated season statistics"""
        try:
            stats_json = json.dumps(aggregated_stats)
            
            await self.db_pool.execute("""
                INSERT INTO player_season_aggregates 
                (player_id, season, stats_type, aggregated_stats, games_played, last_updated)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (player_id, season, stats_type) DO UPDATE
                SET aggregated_stats = EXCLUDED.aggregated_stats,
                    games_played = EXCLUDED.games_played,
                    last_updated = NOW()
            """, player_uuid, season, stats_type, stats_json, games_played)
            
        except Exception as e:
            logger.error(f"Failed to save season aggregate stats: {e}")
            raise
    
    async def get_player_season_stats(self, player_id: str, season: int, stats_type: str) -> Optional[Dict]:
        """Get aggregated season stats for a player"""
        try:
            result = await self.db_pool.fetchrow("""
                SELECT aggregated_stats, games_played, last_updated
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = $3
            """, player_id, season, stats_type)
            
            if result:
                return {
                    'stats': json.loads(result['aggregated_stats']),
                    'games_played': result['games_played'],
                    'last_updated': result['last_updated']
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get season stats: {e}")
            return None
    
    async def get_recent_performance(self, player_id: str, stats_type: str, days: int = 30) -> List[Dict]:
        """Get recent game performance for a player"""
        try:
            results = await self.db_pool.fetch("""
                SELECT stats, game_date
                FROM player_stats
                WHERE player_id = $1 
                  AND stats_type = $2 
                  AND game_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY game_date DESC
            """, player_id, stats_type, days)
            
            return [{'stats': json.loads(row['stats']), 'game_date': row['game_date']} for row in results]
        except Exception as e:
            logger.error(f"Failed to get recent performance: {e}")
            return []
    
    async def calculate_advanced_stats_for_season(self, season: int):
        """Calculate advanced statistics for all players in a season"""
        try:
            logger.info(f"Starting advanced statistics calculation for {season}")
            await self.advanced_stats_calc.calculate_all_players_advanced_stats(season)
            logger.info(f"Completed advanced statistics calculation for {season}")
        except Exception as e:
            logger.error(f"Failed to calculate advanced stats for season {season}: {e}")
    
    async def calculate_fielding_stats_for_season(self, season: int):
        """Calculate fielding statistics for all players in a season"""
        try:
            logger.info(f"Starting fielding statistics calculation for {season}")
            await self.fielding_calc.calculate_all_players_fielding_stats(season)
            logger.info(f"Completed fielding statistics calculation for {season}")
        except Exception as e:
            logger.error(f"Failed to calculate fielding stats for season {season}: {e}")
    
    async def recalculate_advanced_stats_for_player(self, player_id: str, season: int):
        """Recalculate advanced stats for a specific player and season"""
        try:
            # Update batting stats
            await self.advanced_stats_calc.update_player_advanced_stats(player_id, season, 'batting')
            # Update pitching stats
            await self.advanced_stats_calc.update_player_advanced_stats(player_id, season, 'pitching')
            logger.info(f"Recalculated advanced stats for player {player_id}, season {season}")
        except Exception as e:
            logger.error(f"Failed to recalculate advanced stats for player {player_id}: {e}")
    
    async def get_player_advanced_stats(self, player_id: str, season: int, stats_type: str) -> Optional[Dict]:
        """Get a player's advanced statistics"""
        try:
            return await self.get_player_season_stats(player_id, season, stats_type)
        except Exception as e:
            logger.error(f"Failed to get advanced stats for player {player_id}: {e}")
            return None