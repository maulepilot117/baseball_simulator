"""
Advanced Fielding Metrics Calculator
Implements UZR, DRS, OAA, and other defensive statistics for baseball simulation
"""

import asyncio
import logging
import math
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json

import asyncpg

logger = logging.getLogger(__name__)


class Position(Enum):
    """Baseball positions"""
    P = 1
    C = 2
    FIRST_B = 3
    SECOND_B = 4
    THIRD_B = 5
    SS = 6
    LF = 7
    CF = 8
    RF = 9


@dataclass
class PositionalConstants:
    """Positional adjustments and constants for fielding metrics"""
    position: Position
    # Positional adjustment runs per 150 games (Fangraphs style)
    positional_adjustment: float
    # Expected range factor for position
    expected_range_factor: float
    # Difficulty multiplier for plays
    difficulty_multiplier: float
    # Zone coverage weights
    zone_weights: Dict[str, float]

    @classmethod
    def get_constants(cls, position: Position) -> 'PositionalConstants':
        """Get positional constants for fielding calculations"""
        position_data = {
            Position.C: cls(Position.C, 9.0, 6.5, 1.2, {'steal_prevention': 0.3, 'framing': 0.3, 'blocking': 0.2, 'throwing': 0.2}),
            Position.FIRST_B: cls(Position.FIRST_B, -12.0, 9.8, 0.8, {'scoop': 0.4, 'range': 0.3, 'hold_runners': 0.3}),
            Position.SECOND_B: cls(Position.SECOND_B, 3.0, 4.8, 1.1, {'double_play': 0.3, 'range_right': 0.25, 'range_left': 0.25, 'hands': 0.2}),
            Position.THIRD_B: cls(Position.THIRD_B, 2.0, 2.6, 1.3, {'reaction': 0.4, 'arm': 0.3, 'range': 0.3}),
            Position.SS: cls(Position.SS, 7.5, 4.5, 1.4, {'range': 0.35, 'arm': 0.25, 'double_play': 0.25, 'hands': 0.15}),
            Position.LF: cls(Position.LF, -7.5, 2.0, 0.9, {'range': 0.4, 'arm': 0.3, 'reads': 0.3}),
            Position.CF: cls(Position.CF, 2.5, 2.7, 1.2, {'range': 0.5, 'reads': 0.3, 'arm': 0.2}),
            Position.RF: cls(Position.RF, -7.5, 2.1, 1.0, {'arm': 0.4, 'range': 0.3, 'reads': 0.3}),
            Position.P: cls(Position.P, -2.0, 1.8, 0.7, {'fielding': 0.4, 'hold_runners': 0.3, 'covering': 0.3})
        }
        return position_data.get(position, position_data[Position.CF])


@dataclass 
class FieldingPlay:
    """Individual fielding play data"""
    game_id: str
    player_id: str
    position: Position
    play_type: str  # ground_ball, fly_ball, line_drive, popup
    hit_location: Tuple[float, float]  # x, y coordinates
    hang_time: Optional[float]  # for fly balls
    exit_velocity: Optional[float]
    result: str  # out, hit, error
    difficulty: float  # 0.0 to 1.0
    zone: str  # fielding zone identifier
    runner_advancement: Dict[str, int]  # base advancement data


class FieldingMetricsCalculator:
    """Calculator for advanced fielding statistics"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._league_averages_cache: Dict[Tuple[int, str], Dict] = {}
        self._positional_constants = {pos: PositionalConstants.get_constants(pos) for pos in Position}
    
    async def get_league_fielding_averages(self, season: int, position: str) -> Dict:
        """Get league average fielding statistics for position"""
        cache_key = (season, position)
        
        if cache_key not in self._league_averages_cache:
            averages = await self._calculate_league_fielding_averages(season, position)
            self._league_averages_cache[cache_key] = averages
        
        return self._league_averages_cache[cache_key]
    
    async def _calculate_league_fielding_averages(self, season: int, position: str) -> Dict:
        """Calculate league average fielding statistics"""
        try:
            # Get aggregate fielding stats for position
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    AVG((aggregated_stats->>'PO')::int) as avg_putouts,
                    AVG((aggregated_stats->>'A')::int) as avg_assists,
                    AVG((aggregated_stats->>'E')::int) as avg_errors,
                    AVG((aggregated_stats->>'TC')::int) as avg_total_chances,
                    AVG((aggregated_stats->>'DP')::int) as avg_double_plays,
                    AVG((aggregated_stats->>'FPCT')::float) as avg_fielding_pct,
                    COUNT(*) as player_count
                FROM player_season_aggregates psa
                JOIN players p ON psa.player_id = p.id
                WHERE psa.season = $1 
                  AND psa.stats_type = 'fielding'
                  AND p.position = $2
                  AND (psa.aggregated_stats->>'G')::int >= 50
            """, season, position)
            
            if stats and stats['player_count'] > 0:
                return {
                    'avg_putouts': float(stats['avg_putouts'] or 0),
                    'avg_assists': float(stats['avg_assists'] or 0),
                    'avg_errors': float(stats['avg_errors'] or 0),
                    'avg_total_chances': float(stats['avg_total_chances'] or 0),
                    'avg_double_plays': float(stats['avg_double_plays'] or 0),
                    'avg_fielding_pct': float(stats['avg_fielding_pct'] or 0.975),
                    'player_count': stats['player_count']
                }
            else:
                # Default values if no data
                return self._get_default_fielding_averages(position)
                
        except Exception as e:
            logger.error(f"Failed to calculate league fielding averages: {e}")
            return self._get_default_fielding_averages(position)
    
    def _get_default_fielding_averages(self, position: str) -> Dict:
        """Get default fielding averages by position"""
        defaults = {
            'C': {'avg_putouts': 700, 'avg_assists': 65, 'avg_errors': 6, 'avg_total_chances': 771, 'avg_double_plays': 8, 'avg_fielding_pct': 0.993},
            '1B': {'avg_putouts': 1200, 'avg_assists': 80, 'avg_errors': 8, 'avg_total_chances': 1288, 'avg_double_plays': 130, 'avg_fielding_pct': 0.994},
            '2B': {'avg_putouts': 250, 'avg_assists': 430, 'avg_errors': 8, 'avg_total_chances': 688, 'avg_double_plays': 85, 'avg_fielding_pct': 0.988},
            '3B': {'avg_putouts': 100, 'avg_assists': 270, 'avg_errors': 12, 'avg_total_chances': 382, 'avg_double_plays': 25, 'avg_fielding_pct': 0.969},
            'SS': {'avg_putouts': 200, 'avg_assists': 450, 'avg_errors': 12, 'avg_total_chances': 662, 'avg_double_plays': 80, 'avg_fielding_pct': 0.982},
            'LF': {'avg_putouts': 190, 'avg_assists': 8, 'avg_errors': 3, 'avg_total_chances': 201, 'avg_double_plays': 1, 'avg_fielding_pct': 0.985},
            'CF': {'avg_putouts': 310, 'avg_assists': 6, 'avg_errors': 3, 'avg_total_chances': 319, 'avg_double_plays': 1, 'avg_fielding_pct': 0.991},
            'RF': {'avg_putouts': 210, 'avg_assists': 12, 'avg_errors': 3, 'avg_total_chances': 225, 'avg_double_plays': 2, 'avg_fielding_pct': 0.987},
            'P': {'avg_putouts': 15, 'avg_assists': 45, 'avg_errors': 2, 'avg_total_chances': 62, 'avg_double_plays': 3, 'avg_fielding_pct': 0.968}
        }
        return defaults.get(position, defaults['CF'])
    
    # ADVANCED FIELDING METRICS
    
    def calculate_range_factor(self, fielding_stats: Dict) -> float:
        """Calculate Range Factor (RF) - (PO + A) / G"""
        try:
            putouts = fielding_stats.get('PO', 0)
            assists = fielding_stats.get('A', 0)
            games = fielding_stats.get('G', 0)
            
            return (putouts + assists) / games if games > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating range factor: {e}")
            return 0.0
    
    def calculate_zone_rating(self, fielding_stats: Dict, position: str, season: int) -> float:
        """Calculate Zone Rating (ZR) - simplified version"""
        try:
            # This is a simplified version - full ZR requires play-by-play data
            # with hit location and player positioning
            total_chances = fielding_stats.get('TC', 0)
            errors = fielding_stats.get('E', 0)
            
            if total_chances == 0:
                return 0.0
            
            # Basic zone rating approximation
            successful_plays = total_chances - errors
            zone_rating = successful_plays / total_chances
            
            return min(1.0, max(0.0, zone_rating))
            
        except Exception as e:
            logger.error(f"Error calculating zone rating: {e}")
            return 0.0
    
    async def calculate_uzr(self, player_id: str, season: int, position: str) -> float:
        """Calculate Ultimate Zone Rating (UZR) - simplified version"""
        try:
            # Get player's fielding stats
            player_stats = await self.db_pool.fetchrow("""
                SELECT aggregated_stats
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
            """, player_id, season)
            
            if not player_stats:
                return 0.0
            
            stats = json.loads(player_stats['aggregated_stats'])
            league_avg = await self.get_league_fielding_averages(season, position)
            
            # Simplified UZR calculation
            player_chances = stats.get('TC', 0)
            player_errors = stats.get('E', 0)
            games_played = stats.get('G', 0)
            
            if games_played == 0 or player_chances == 0:
                return 0.0
            
            # Player rate vs league average rate
            player_success_rate = (player_chances - player_errors) / player_chances
            league_success_rate = ((league_avg['avg_total_chances'] - league_avg['avg_errors']) / 
                                 league_avg['avg_total_chances'])
            
            # Convert to runs above/below average
            rate_diff = player_success_rate - league_success_rate
            chances_per_game = player_chances / games_played
            
            # UZR approximation (runs above average per 150 games)
            uzr = rate_diff * chances_per_game * 150 * 0.8  # 0.8 runs per additional out
            
            return round(uzr, 1)
            
        except Exception as e:
            logger.error(f"Error calculating UZR: {e}")
            return 0.0
    
    async def calculate_drs(self, player_id: str, season: int, position: str) -> int:
        """Calculate Defensive Runs Saved (DRS) - simplified version"""
        try:
            # Get player's fielding stats
            player_stats = await self.db_pool.fetchrow("""
                SELECT aggregated_stats
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
            """, player_id, season)
            
            if not player_stats:
                return 0
            
            stats = json.loads(player_stats['aggregated_stats'])
            league_avg = await self.get_league_fielding_averages(season, position)
            
            # Simplified DRS calculation
            player_rf = self.calculate_range_factor(stats)
            expected_rf = league_avg['avg_total_chances'] / 150  # Assume 150 games
            
            games_played = stats.get('G', 0)
            if games_played == 0:
                return 0
            
            # Range component
            rf_diff = player_rf - expected_rf
            range_runs = rf_diff * games_played * 0.8
            
            # Error component
            player_error_rate = stats.get('E', 0) / max(stats.get('TC', 1), 1)
            league_error_rate = league_avg['avg_errors'] / league_avg['avg_total_chances']
            error_diff = league_error_rate - player_error_rate  # Positive if fewer errors
            error_runs = error_diff * stats.get('TC', 0) * 1.0
            
            # Double play component (for infielders)
            if position in ['2B', 'SS', '3B', '1B']:
                player_dp_rate = stats.get('DP', 0) / max(games_played, 1)
                league_dp_rate = league_avg['avg_double_plays'] / 150
                dp_diff = player_dp_rate - league_dp_rate
                dp_runs = dp_diff * games_played * 0.8
            else:
                dp_runs = 0
            
            total_drs = range_runs + error_runs + dp_runs
            return round(total_drs)
            
        except Exception as e:
            logger.error(f"Error calculating DRS: {e}")
            return 0
    
    def calculate_fielding_percentage_plus(self, fielding_stats: Dict, league_avg: Dict) -> int:
        """Calculate Fielding Percentage Plus (similar to ERA+)"""
        try:
            total_chances = fielding_stats.get('TC', 0)
            errors = fielding_stats.get('E', 0)
            
            if total_chances == 0:
                return 100
            
            player_fpct = (total_chances - errors) / total_chances
            league_fpct = league_avg.get('avg_fielding_pct', 0.975)
            
            if player_fpct == 0:
                return 0
            
            fpct_plus = (player_fpct / league_fpct) * 100
            return round(fpct_plus)
            
        except Exception as e:
            logger.error(f"Error calculating FPCT+: {e}")
            return 100
    
    def calculate_arm_strength_rating(self, fielding_stats: Dict, position: str) -> float:
        """Calculate arm strength rating based on assists and position"""
        try:
            assists = fielding_stats.get('A', 0)
            games = fielding_stats.get('G', 0)
            
            if games == 0:
                return 50.0  # Average rating
            
            assists_per_game = assists / games
            
            # Position-specific arm strength expectations
            position_multipliers = {
                'C': 0.4,    # Assists mainly on stolen bases
                '1B': 0.5,   # Fewer assist opportunities
                '2B': 2.7,   # Many double plays and range plays
                '3B': 1.8,   # Hard throws across diamond
                'SS': 3.0,   # Most assists of any position
                'LF': 0.05,  # Rare assist opportunities
                'CF': 0.04,  # Rare assist opportunities  
                'RF': 0.08,  # Occasional throws to 3B/home
                'P': 0.3     # Occasional fielding plays
            }
            
            expected_assists = position_multipliers.get(position, 1.0)
            arm_rating = (assists_per_game / expected_assists) * 50
            
            # Scale to 20-80 scouting scale
            return max(20.0, min(80.0, arm_rating))
            
        except Exception as e:
            logger.error(f"Error calculating arm strength: {e}")
            return 50.0
    
    async def calculate_positional_adjustment(self, position: str, games_played: int) -> float:
        """Calculate positional adjustment in runs"""
        try:
            pos_enum = Position.P if position == 'P' else getattr(Position, position.replace('B', '_B'))
            constants = self._positional_constants.get(pos_enum, self._positional_constants[Position.CF])
            
            # Scale to games played
            adjustment = constants.positional_adjustment * (games_played / 150)
            return round(adjustment, 1)
            
        except Exception as e:
            logger.error(f"Error calculating positional adjustment: {e}")
            return 0.0
    
    # COMPREHENSIVE FIELDING METRICS
    
    async def calculate_all_advanced_fielding_stats(self, player_id: str, season: int, 
                                                   position: str) -> Dict:
        """Calculate all advanced fielding statistics for a player"""
        try:
            # Get base fielding stats
            player_stats = await self.db_pool.fetchrow("""
                SELECT aggregated_stats, games_played
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
            """, player_id, season)
            
            if not player_stats:
                return {}
            
            stats = json.loads(player_stats['aggregated_stats'])
            games_played = player_stats['games_played']
            league_avg = await self.get_league_fielding_averages(season, position)
            
            advanced_stats = {
                # Range and Coverage
                'RF': round(self.calculate_range_factor(stats), 2),
                'ZR': round(self.calculate_zone_rating(stats, position, season), 3),
                
                # Advanced Metrics
                'UZR': await self.calculate_uzr(player_id, season, position),
                'DRS': await self.calculate_drs(player_id, season, position),
                
                # Relative Performance
                'FPCT+': self.calculate_fielding_percentage_plus(stats, league_avg),
                
                # Position-Specific
                'ARM': round(self.calculate_arm_strength_rating(stats, position), 1),
                'POS_ADJ': await self.calculate_positional_adjustment(position, games_played),
                
                # Context Stats
                'CHANCES_PER_GAME': round(stats.get('TC', 0) / max(games_played, 1), 2),
                'ERROR_PCT': round((stats.get('E', 0) / max(stats.get('TC', 1), 1)) * 100, 2)
            }
            
            return advanced_stats
            
        except Exception as e:
            logger.error(f"Error calculating advanced fielding stats: {e}")
            return {}
    
    async def update_player_fielding_stats(self, player_id: str, season: int):
        """Update fielding stats for a specific player"""
        try:
            # Get player position
            player_info = await self.db_pool.fetchrow("""
                SELECT position FROM players WHERE id = $1
            """, player_id)
            
            if not player_info:
                logger.warning(f"Player not found: {player_id}")
                return
            
            position = player_info['position']
            
            # Get base fielding stats
            base_stats = await self.db_pool.fetchrow("""
                SELECT aggregated_stats
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
            """, player_id, season)
            
            if not base_stats:
                logger.warning(f"No base fielding stats found for player {player_id}")
                return
            
            player_stats = json.loads(base_stats['aggregated_stats'])
            
            # Calculate advanced fielding stats
            advanced_stats = await self.calculate_all_advanced_fielding_stats(player_id, season, position)
            
            # Merge with existing stats
            updated_stats = {**player_stats, **advanced_stats}
            
            # Update in database
            await self.db_pool.execute("""
                UPDATE player_season_aggregates
                SET aggregated_stats = $4, last_updated = NOW()
                WHERE player_id = $1 AND season = $2 AND stats_type = $3
            """, player_id, season, 'fielding', json.dumps(updated_stats))
            
            logger.info(f"Updated advanced fielding stats for player {player_id}, season {season}")
            
        except Exception as e:
            logger.error(f"Failed to update fielding stats: {e}")
    
    async def calculate_all_players_fielding_stats(self, season: int):
        """Calculate advanced fielding stats for all players in a season"""
        try:
            logger.info(f"Starting advanced fielding stats calculation for {season} season")
            
            # Get all players with fielding stats for the season
            players = await self.db_pool.fetch("""
                SELECT DISTINCT player_id
                FROM player_season_aggregates
                WHERE season = $1 AND stats_type = 'fielding'
                ORDER BY player_id
            """, season)
            
            total_players = len(players)
            logger.info(f"Processing fielding stats for {total_players} players")
            
            for i, player_record in enumerate(players):
                if i % 50 == 0:
                    logger.info(f"Processing player {i+1}/{total_players}")
                
                await self.update_player_fielding_stats(
                    player_record['player_id'], 
                    season
                )
                
                # Small delay to prevent overwhelming the database
                await asyncio.sleep(0.01)
            
            logger.info(f"Completed advanced fielding stats calculation for {season} season")
            
        except Exception as e:
            logger.error(f"Failed to calculate fielding stats for all players: {e}")
    
    async def get_fielding_leaderboards(self, season: int, stat_name: str, 
                                       position: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get fielding statistics leaderboards"""
        try:
            position_filter = ""
            params = [season, stat_name, limit]
            
            if position:
                position_filter = "AND p.position = $4"
                params.append(position)
            
            # Determine sort order (lower is better for errors, higher for most others)
            sort_order = "ASC" if stat_name in ['E', 'ERROR_PCT'] else "DESC"
            
            query = f"""
                SELECT 
                    p.player_id,
                    p.first_name,
                    p.last_name,
                    p.position,
                    t.abbreviation as team_abbrev,
                    psa.aggregated_stats,
                    psa.games_played
                FROM player_season_aggregates psa
                JOIN players p ON psa.player_id = p.id
                JOIN teams t ON p.team_id = t.id
                WHERE psa.season = $1 
                  AND psa.stats_type = 'fielding'
                  AND (psa.aggregated_stats->>$2) IS NOT NULL
                  AND psa.games_played >= 50
                  {position_filter}
                ORDER BY (psa.aggregated_stats->>$2)::float {sort_order}
                LIMIT $3
            """
            
            results = await self.db_pool.fetch(query, *params)
            
            leaderboard = []
            for i, row in enumerate(results):
                stats = json.loads(row['aggregated_stats'])
                leaderboard.append({
                    "rank": i + 1,
                    "player_id": row['player_id'],
                    "name": f"{row['first_name']} {row['last_name']}",
                    "position": row['position'],
                    "team": row['team_abbrev'],
                    "stat_value": stats.get(stat_name),
                    "games_played": row['games_played']
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting fielding leaderboards: {e}")
            return []