"""
Position-Specific Advanced Metrics
Specialized statistics for catchers and outfielders
"""

import asyncio
import logging
import math
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class CatcherFramingPlay:
    """Individual pitch framing play"""
    game_id: str
    catcher_id: str
    pitcher_id: str
    pitch_type: str
    pitch_location: Tuple[float, float]  # x, z coordinates
    called_strike: bool
    expected_strike_prob: float
    framing_value: float  # runs added/lost


@dataclass
class OutfieldAssist:
    """Outfield assist tracking"""
    game_id: str
    fielder_id: str
    runner_id: str
    base_from: int
    base_to: int
    result: str  # out, safe, error
    throw_distance: float
    throw_time: float
    success: bool


class PositionSpecificMetrics:
    """Calculator for position-specific advanced metrics"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._strike_zone_model = self._initialize_strike_zone_model()
    
    def _initialize_strike_zone_model(self) -> Dict:
        """Initialize strike zone probability model"""
        # Simplified strike zone model - in reality this would be much more complex
        return {
            'center_x': 0.0,  # Home plate center
            'width': 17.0,    # inches
            'height_bottom': 1.5,  # feet 
            'height_top': 3.5,     # feet
            'edge_probability': 0.5  # 50% call rate at edge
        }
    
    # CATCHER METRICS
    
    def calculate_strike_zone_probability(self, pitch_x: float, pitch_z: float, 
                                        batter_stance: str = "R") -> float:
        """Calculate probability of strike call based on pitch location"""
        try:
            sz = self._strike_zone_model
            
            # Convert to inches and relative to plate center
            x_from_center = abs(pitch_x * 12)  # Convert feet to inches
            z_height = pitch_z  # Already in feet
            
            # X-axis probability (width)
            if x_from_center <= sz['width'] / 2:
                x_prob = 1.0
            elif x_from_center <= sz['width'] / 2 + 3:  # 3 inch buffer
                x_prob = max(0.0, 1.0 - (x_from_center - sz['width']/2) / 3)
            else:
                x_prob = 0.05  # Very low but not zero
            
            # Z-axis probability (height)
            if sz['height_bottom'] <= z_height <= sz['height_top']:
                z_prob = 1.0
            elif z_height < sz['height_bottom']:
                diff = sz['height_bottom'] - z_height
                z_prob = max(0.0, 1.0 - diff / 0.5)  # 6 inch buffer below
            elif z_height > sz['height_top']:
                diff = z_height - sz['height_top']
                z_prob = max(0.0, 1.0 - diff / 0.5)  # 6 inch buffer above
            else:
                z_prob = 0.05
            
            # Combined probability
            combined_prob = x_prob * z_prob
            return max(0.01, min(0.99, combined_prob))
            
        except Exception as e:
            logger.error(f"Error calculating strike probability: {e}")
            return 0.5
    
    async def calculate_framing_runs(self, catcher_id: str, season: int) -> float:
        """Calculate pitch framing runs above average"""
        try:
            # Get all pitches caught by this catcher
            pitches = await self.db_pool.fetch("""
                SELECT 
                    p.id,
                    p.pitch_type,
                    p.plate_location,
                    p.result,
                    p.balls,
                    p.strikes
                FROM pitches p
                JOIN games g ON p.game_id = g.id
                WHERE EXTRACT(YEAR FROM g.game_date) = $1
                  AND p.plate_location IS NOT NULL
                  AND p.result IN ('called_strike', 'ball', 'strike_looking')
                LIMIT 1000  -- Sample for performance
            """, season)
            
            total_framing_value = 0.0
            pitch_count = 0
            
            for pitch in pitches:
                try:
                    location = json.loads(pitch['plate_location'])
                    px, pz = location.get('x', 0), location.get('z', 0)
                    
                    # Calculate expected strike probability
                    expected_prob = self.calculate_strike_zone_probability(px, pz)
                    
                    # Actual result (1 = strike, 0 = ball)
                    actual_strike = 1 if pitch['result'] in ['called_strike', 'strike_looking'] else 0
                    
                    # Framing value = actual - expected
                    framing_value = actual_strike - expected_prob
                    
                    # Convert to run value (approximately 0.13 runs per strike)
                    run_value = framing_value * 0.13
                    
                    total_framing_value += run_value
                    pitch_count += 1
                    
                except Exception:
                    continue
            
            if pitch_count == 0:
                return 0.0
            
            # Scale to full season estimate
            estimated_pitches_per_season = 2500  # Approximate for full-time catcher
            scaling_factor = estimated_pitches_per_season / max(pitch_count, 1)
            
            return round(total_framing_value * scaling_factor, 1)
            
        except Exception as e:
            logger.error(f"Error calculating framing runs: {e}")
            return 0.0
    
    async def calculate_blocking_runs(self, catcher_id: str, season: int) -> float:
        """Calculate blocking runs above average"""
        try:
            # Get wild pitches and passed balls for this catcher
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'PB')::int) as total_pb,
                    SUM((aggregated_stats->>'G')::int) as total_games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, catcher_id, season)
            
            if not stats or stats['total_games'] == 0:
                return 0.0
            
            pb_rate = stats['total_pb'] / stats['total_games']
            
            # League average PB rate (approximately 0.05 per game)
            league_avg_pb_rate = 0.05
            
            # Calculate runs saved/cost (approximately 0.27 runs per passed ball)
            pb_diff = league_avg_pb_rate - pb_rate
            blocking_runs = pb_diff * stats['total_games'] * 0.27
            
            return round(blocking_runs, 1)
            
        except Exception as e:
            logger.error(f"Error calculating blocking runs: {e}")
            return 0.0
    
    async def calculate_catcher_arm_runs(self, catcher_id: str, season: int) -> float:
        """Calculate throwing arm runs above average"""
        try:
            # Get caught stealing stats
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'CS')::int) as total_cs,
                    SUM((aggregated_stats->>'SBA')::int) as total_sba,
                    SUM((aggregated_stats->>'G')::int) as total_games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, catcher_id, season)
            
            if not stats or stats['total_sba'] == 0:
                return 0.0
            
            # Calculate caught stealing percentage
            cs_rate = stats['total_cs'] / stats['total_sba']
            
            # League average CS rate (approximately 25%)
            league_avg_cs_rate = 0.25
            
            # Calculate runs saved (approximately 0.2 runs per stolen base prevented)
            cs_diff = cs_rate - league_avg_cs_rate
            arm_runs = cs_diff * stats['total_sba'] * 0.2
            
            return round(arm_runs, 1)
            
        except Exception as e:
            logger.error(f"Error calculating catcher arm runs: {e}")
            return 0.0
    
    async def calculate_catcher_era(self, catcher_id: str, season: int) -> float:
        """Calculate ERA of pitchers when caught by this catcher"""
        try:
            # This would require pitch-by-play data linking catchers to each pitch
            # For now, return a placeholder
            # In a full implementation, you'd track ERA for all pitches caught
            
            # Get basic stats as proxy
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'G')::int) as games_caught
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, catcher_id, season)
            
            if not stats or stats['games_caught'] == 0:
                return 0.0
            
            # Placeholder calculation - would need detailed pitch data
            return 4.00  # League average approximation
            
        except Exception as e:
            logger.error(f"Error calculating catcher ERA: {e}")
            return 0.0
    
    # OUTFIELDER METRICS
    
    async def calculate_outfield_arm_runs(self, fielder_id: str, season: int, position: str) -> float:
        """Calculate outfield arm strength runs above average"""
        try:
            # Get assist stats
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'A')::int) as total_assists,
                    SUM((aggregated_stats->>'G')::int) as total_games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or stats['total_games'] == 0:
                return 0.0
            
            assists_per_game = stats['total_assists'] / stats['total_games']
            
            # Position-specific league averages
            position_averages = {
                'LF': 0.05,  # Left field gets fewer opportunities
                'CF': 0.04,  # Center field rare assists but crucial
                'RF': 0.08   # Right field most assist opportunities
            }
            
            league_avg = position_averages.get(position, 0.06)
            
            # Calculate runs above average (approximately 0.8 runs per assist)
            assist_diff = assists_per_game - league_avg
            arm_runs = assist_diff * stats['total_games'] * 0.8
            
            return round(arm_runs, 1)
            
        except Exception as e:
            logger.error(f"Error calculating outfield arm runs: {e}")
            return 0.0
    
    async def calculate_outfield_range_runs(self, fielder_id: str, season: int, position: str) -> float:
        """Calculate outfield range runs above average"""
        try:
            # Get range factor
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'PO')::int) as total_po,
                    SUM((aggregated_stats->>'A')::int) as total_assists,
                    SUM((aggregated_stats->>'G')::int) as total_games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or stats['total_games'] == 0:
                return 0.0
            
            # Calculate range factor
            range_factor = (stats['total_po'] + stats['total_assists']) / stats['total_games']
            
            # Position-specific league averages for range factor
            position_rf_averages = {
                'LF': 2.0,   # Left field
                'CF': 2.7,   # Center field (most putouts)
                'RF': 2.1    # Right field
            }
            
            league_avg_rf = position_rf_averages.get(position, 2.3)
            
            # Calculate runs above average (approximately 0.8 runs per additional out)
            rf_diff = range_factor - league_avg_rf
            range_runs = rf_diff * stats['total_games'] * 0.8
            
            return round(range_runs, 1)
            
        except Exception as e:
            logger.error(f"Error calculating outfield range runs: {e}")
            return 0.0
    
    async def calculate_jump_rating(self, fielder_id: str, season: int) -> float:
        """Calculate first step/jump rating for outfielders"""
        try:
            # This would require Statcast data for actual jump calculations
            # For now, use range factor as a proxy
            
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'PO')::int) as total_po,
                    SUM((aggregated_stats->>'G')::int) as total_games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or stats['total_games'] == 0:
                return 50.0  # Average rating
            
            po_per_game = stats['total_po'] / stats['total_games']
            
            # Convert to 20-80 scouting scale
            # 2.5 PO/game = 50 rating, scale accordingly
            base_rating = 50
            rating_per_po = 8  # 8 rating points per 0.1 PO/game difference
            
            jump_rating = base_rating + ((po_per_game - 2.5) * rating_per_po * 10)
            
            return max(20.0, min(80.0, round(jump_rating, 1)))
            
        except Exception as e:
            logger.error(f"Error calculating jump rating: {e}")
            return 50.0
    
    async def calculate_route_efficiency(self, fielder_id: str, season: int) -> float:
        """Calculate route running efficiency for outfielders"""
        try:
            # This would require tracking actual routes vs optimal routes
            # For now, use error rate as an inverse proxy
            
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'E')::int) as total_errors,
                    SUM((aggregated_stats->>'TC')::int) as total_chances
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 
                  AND psa.season = $2 
                  AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or stats['total_chances'] == 0:
                return 0.85  # Average efficiency
            
            error_rate = stats['total_errors'] / stats['total_chances']
            
            # Convert error rate to efficiency (lower errors = higher efficiency)
            efficiency = 1.0 - (error_rate * 2)  # Scale error impact
            
            return max(0.5, min(1.0, round(efficiency, 3)))
            
        except Exception as e:
            logger.error(f"Error calculating route efficiency: {e}")
            return 0.85
    
    # COMPREHENSIVE POSITION CALCULATIONS
    
    async def calculate_all_catcher_metrics(self, catcher_id: str, season: int) -> Dict:
        """Calculate all catcher-specific advanced metrics"""
        try:
            metrics = {
                # Framing and receiving
                'FRAMING_RUNS': await self.calculate_framing_runs(catcher_id, season),
                'BLOCKING_RUNS': await self.calculate_blocking_runs(catcher_id, season),
                'CATCHER_ERA': await self.calculate_catcher_era(catcher_id, season),
                
                # Throwing and arm
                'ARM_RUNS': await self.calculate_catcher_arm_runs(catcher_id, season),
                
                # Get basic caught stealing percentage
                'CS_PCT': await self._get_cs_percentage(catcher_id, season),
                'SB_ALLOWED_PER_GAME': await self._get_sb_per_game(catcher_id, season),
                
                # Overall defensive value
                'TOTAL_CATCHER_RUNS': 0.0  # Will be calculated below
            }
            
            # Calculate total catcher runs
            metrics['TOTAL_CATCHER_RUNS'] = (
                metrics['FRAMING_RUNS'] + 
                metrics['BLOCKING_RUNS'] + 
                metrics['ARM_RUNS']
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating catcher metrics: {e}")
            return {}
    
    async def calculate_all_outfielder_metrics(self, fielder_id: str, season: int, position: str) -> Dict:
        """Calculate all outfielder-specific advanced metrics"""
        try:
            metrics = {
                # Range and coverage
                'RANGE_RUNS': await self.calculate_outfield_range_runs(fielder_id, season, position),
                'JUMP_RATING': await self.calculate_jump_rating(fielder_id, season),
                'ROUTE_EFFICIENCY': await self.calculate_route_efficiency(fielder_id, season),
                
                # Arm strength and accuracy
                'ARM_RUNS': await self.calculate_outfield_arm_runs(fielder_id, season, position),
                'ARM_ACCURACY': await self._get_arm_accuracy(fielder_id, season),
                
                # Position-specific
                'ASSISTS_PER_GAME': await self._get_assists_per_game(fielder_id, season),
                'PUTOUTS_PER_GAME': await self._get_putouts_per_game(fielder_id, season),
                
                # Overall value
                'TOTAL_OUTFIELD_RUNS': 0.0  # Will be calculated below
            }
            
            # Calculate total outfield runs
            metrics['TOTAL_OUTFIELD_RUNS'] = (
                metrics['RANGE_RUNS'] + 
                metrics['ARM_RUNS']
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating outfielder metrics: {e}")
            return {}
    
    # HELPER METHODS
    
    async def _get_cs_percentage(self, catcher_id: str, season: int) -> float:
        """Get caught stealing percentage for catcher"""
        try:
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'CS')::int) as cs,
                    SUM((aggregated_stats->>'SBA')::int) as sba
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 AND psa.season = $2 AND psa.stats_type = 'fielding'
            """, catcher_id, season)
            
            if not stats or stats['sba'] == 0:
                return 0.0
            
            return round((stats['cs'] / stats['sba']) * 100, 1)
            
        except Exception as e:
            logger.error(f"Error getting CS%: {e}")
            return 0.0
    
    async def _get_sb_per_game(self, catcher_id: str, season: int) -> float:
        """Get stolen bases allowed per game for catcher"""
        try:
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'SB')::int) as sb,
                    SUM((aggregated_stats->>'G')::int) as games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 AND psa.season = $2 AND psa.stats_type = 'fielding'
            """, catcher_id, season)
            
            if not stats or stats['games'] == 0:
                return 0.0
            
            return round(stats['sb'] / stats['games'], 2)
            
        except Exception as e:
            logger.error(f"Error getting SB per game: {e}")
            return 0.0
    
    async def _get_assists_per_game(self, fielder_id: str, season: int) -> float:
        """Get assists per game for outfielder"""
        try:
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'A')::int) as assists,
                    SUM((aggregated_stats->>'G')::int) as games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 AND psa.season = $2 AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or stats['games'] == 0:
                return 0.0
            
            return round(stats['assists'] / stats['games'], 3)
            
        except Exception as e:
            logger.error(f"Error getting assists per game: {e}")
            return 0.0
    
    async def _get_putouts_per_game(self, fielder_id: str, season: int) -> float:
        """Get putouts per game for outfielder"""
        try:
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'PO')::int) as putouts,
                    SUM((aggregated_stats->>'G')::int) as games
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 AND psa.season = $2 AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or stats['games'] == 0:
                return 0.0
            
            return round(stats['putouts'] / stats['games'], 2)
            
        except Exception as e:
            logger.error(f"Error getting putouts per game: {e}")
            return 0.0
    
    async def _get_arm_accuracy(self, fielder_id: str, season: int) -> float:
        """Get arm accuracy rating for outfielder"""
        try:
            # Use assists vs errors as proxy for accuracy
            stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((aggregated_stats->>'A')::int) as assists,
                    SUM((aggregated_stats->>'E')::int) as errors
                FROM player_season_aggregates psa
                WHERE psa.player_id = $1 AND psa.season = $2 AND psa.stats_type = 'fielding'
            """, fielder_id, season)
            
            if not stats or (stats['assists'] + stats['errors']) == 0:
                return 0.85  # Average accuracy
            
            accuracy = stats['assists'] / (stats['assists'] + stats['errors'])
            return round(accuracy, 3)
            
        except Exception as e:
            logger.error(f"Error getting arm accuracy: {e}")
            return 0.85
    
    async def update_position_specific_stats(self, player_id: str, season: int, position: str):
        """Update position-specific stats for a player"""
        try:
            advanced_stats = {}
            
            if position == 'C':
                advanced_stats = await self.calculate_all_catcher_metrics(player_id, season)
            elif position in ['LF', 'CF', 'RF']:
                advanced_stats = await self.calculate_all_outfielder_metrics(player_id, season, position)
            else:
                logger.info(f"No position-specific metrics for position: {position}")
                return
            
            if not advanced_stats:
                logger.warning(f"No advanced stats calculated for player {player_id}")
                return
            
            # Get existing fielding stats
            existing_stats = await self.db_pool.fetchrow("""
                SELECT aggregated_stats
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
            """, player_id, season)
            
            if existing_stats:
                current_stats = json.loads(existing_stats['aggregated_stats'])
                # Merge position-specific stats
                updated_stats = {**current_stats, **advanced_stats}
                
                # Update in database
                await self.db_pool.execute("""
                    UPDATE player_season_aggregates
                    SET aggregated_stats = $4, last_updated = NOW()
                    WHERE player_id = $1 AND season = $2 AND stats_type = $3
                """, player_id, season, 'fielding', json.dumps(updated_stats))
                
                logger.info(f"Updated position-specific stats for {position} {player_id}, season {season}")
            
        except Exception as e:
            logger.error(f"Failed to update position-specific stats: {e}")
    
    async def calculate_all_position_specific_stats(self, season: int):
        """Calculate position-specific stats for all qualifying players"""
        try:
            logger.info(f"Starting position-specific stats calculation for {season}")
            
            # Get catchers and outfielders with fielding stats
            players = await self.db_pool.fetch("""
                SELECT DISTINCT psa.player_id, p.position
                FROM player_season_aggregates psa
                JOIN players p ON psa.player_id = p.id
                WHERE psa.season = $1 
                  AND psa.stats_type = 'fielding'
                  AND p.position IN ('C', 'LF', 'CF', 'RF')
                  AND psa.games_played >= 20
                ORDER BY p.position, psa.player_id
            """, season)
            
            total_players = len(players)
            logger.info(f"Processing position-specific stats for {total_players} players")
            
            for i, player in enumerate(players):
                if i % 25 == 0:
                    logger.info(f"Processing player {i+1}/{total_players}")
                
                await self.update_position_specific_stats(
                    player['player_id'],
                    season,
                    player['position']
                )
                
                await asyncio.sleep(0.01)
            
            logger.info(f"Completed position-specific stats calculation for {season}")
            
        except Exception as e:
            logger.error(f"Failed to calculate position-specific stats: {e}")