"""
Advanced Baseball Statistics Calculator
Implements sabermetric calculations for Baseball Reference and Fangraphs style metrics
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import math

import asyncpg

logger = logging.getLogger(__name__)


class League(Enum):
    """League identifiers"""
    AL = "AL"
    NL = "NL"
    MLB = "MLB"


@dataclass
class LeagueConstants:
    """League-wide constants for calculations"""
    season: int
    league: League
    # Batting constants
    woba_scale: float = 1.000
    woba_weights: Dict[str, float] = None
    runs_per_win: float = 10.0
    park_factor: float = 1.000
    # Pitching constants
    league_era: float = 4.00
    league_fip: float = 4.00
    fip_constant: float = 3.20
    # Environment factors
    league_hr_per_fb: float = 0.105
    league_babip: float = 0.300
    league_lob_rate: float = 0.720

    def __post_init__(self):
        if self.woba_weights is None:
            # Default wOBA weights (2023 season approximation)
            self.woba_weights = {
                'BB': 0.690,
                'HBP': 0.720,
                '1B': 0.880,
                '2B': 1.247,
                '3B': 1.578,
                'HR': 2.031
            }


class AdvancedStatsCalculator:
    """Calculator for advanced baseball statistics"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._league_constants_cache: Dict[Tuple[int, str], LeagueConstants] = {}
    
    async def get_league_constants(self, season: int, league: str = "MLB") -> LeagueConstants:
        """Get or calculate league constants for a season"""
        cache_key = (season, league)
        
        if cache_key not in self._league_constants_cache:
            constants = await self._calculate_league_constants(season, league)
            self._league_constants_cache[cache_key] = constants
        
        return self._league_constants_cache[cache_key]
    
    async def _calculate_league_constants(self, season: int, league: str) -> LeagueConstants:
        """Calculate league-wide constants from database"""
        try:
            # Get league totals for the season
            league_stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((stats->>'AB')::int) as total_ab,
                    SUM((stats->>'H')::int) as total_h,
                    SUM((stats->>'2B')::int) as total_2b,
                    SUM((stats->>'3B')::int) as total_3b,
                    SUM((stats->>'HR')::int) as total_hr,
                    SUM((stats->>'BB')::int) as total_bb,
                    SUM((stats->>'HBP')::int) as total_hbp,
                    SUM((stats->>'R')::int) as total_r,
                    SUM((stats->>'G')::int) as total_g
                FROM player_season_aggregates psa
                JOIN players p ON psa.player_id = p.id
                JOIN teams t ON p.team_id = t.id
                WHERE psa.season = $1 
                  AND psa.stats_type = 'batting'
                  AND ($2 = 'MLB' OR t.league = $2)
            """, season, league)
            
            pitching_stats = await self.db_pool.fetchrow("""
                SELECT 
                    SUM((stats->>'IP')::float) as total_ip,
                    SUM((stats->>'ER')::int) as total_er,
                    SUM((stats->>'HR')::int) as total_hr_allowed,
                    SUM((stats->>'BB')::int) as total_bb_allowed,
                    SUM((stats->>'SO')::int) as total_so,
                    SUM((stats->>'H')::int) as total_h_allowed
                FROM player_season_aggregates psa
                JOIN players p ON psa.player_id = p.id
                JOIN teams t ON p.team_id = t.id
                WHERE psa.season = $1 
                  AND psa.stats_type = 'pitching'
                  AND ($2 = 'MLB' OR t.league = $2)
            """, season, league)
            
            # Calculate derived constants
            constants = LeagueConstants(season=season, league=League(league))
            
            if league_stats and pitching_stats:
                # Calculate league ERA
                if pitching_stats['total_ip'] and pitching_stats['total_ip'] > 0:
                    constants.league_era = (pitching_stats['total_er'] * 9.0) / pitching_stats['total_ip']
                
                # Calculate league BABIP
                if league_stats['total_ab'] and league_stats['total_hr']:
                    hits_minus_hr = league_stats['total_h'] - league_stats['total_hr']
                    ab_minus_hr_minus_so = (league_stats['total_ab'] - league_stats['total_hr'] - 
                                           (pitching_stats['total_so'] or 0))
                    if ab_minus_hr_minus_so > 0:
                        constants.league_babip = hits_minus_hr / ab_minus_hr_minus_so
                
                # Calculate wOBA scale and weights (simplified)
                if league_stats['total_ab'] and league_stats['total_r']:
                    # Runs per plate appearance
                    total_pa = (league_stats['total_ab'] + league_stats['total_bb'] + 
                              league_stats['total_hbp'])
                    if total_pa > 0:
                        constants.woba_scale = league_stats['total_r'] / total_pa
            
            return constants
            
        except Exception as e:
            logger.error(f"Failed to calculate league constants: {e}")
            # Return default constants
            return LeagueConstants(season=season, league=League(league))
    
    # BATTING ADVANCED STATS
    
    def calculate_woba(self, stats: Dict, constants: LeagueConstants) -> float:
        """Calculate weighted On-Base Average (wOBA)"""
        try:
            weights = constants.woba_weights
            
            # Get counting stats
            bb = stats.get('BB', 0)
            hbp = stats.get('HBP', 0)
            singles = stats.get('H', 0) - stats.get('2B', 0) - stats.get('3B', 0) - stats.get('HR', 0)
            doubles = stats.get('2B', 0)
            triples = stats.get('3B', 0)
            homers = stats.get('HR', 0)
            
            # Calculate weighted numerator
            numerator = (weights['BB'] * bb + 
                        weights['HBP'] * hbp +
                        weights['1B'] * singles +
                        weights['2B'] * doubles +
                        weights['3B'] * triples +
                        weights['HR'] * homers)
            
            # Calculate denominator (plate appearances)
            ab = stats.get('AB', 0)
            sf = stats.get('SF', 0)
            denominator = ab + bb + sf + hbp
            
            return numerator / denominator if denominator > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating wOBA: {e}")
            return 0.0
    
    def calculate_wrc_plus(self, stats: Dict, constants: LeagueConstants, 
                          park_factor: float = 1.0) -> int:
        """Calculate Weighted Runs Created Plus (wRC+)"""
        try:
            woba = self.calculate_woba(stats, constants)
            
            # League average wOBA (approximate)
            league_woba = 0.320
            
            # wOBA scale
            woba_scale = constants.woba_scale
            
            # Calculate wRC per PA
            wrc_per_pa = ((woba - league_woba) / woba_scale) + (constants.runs_per_win / 600)
            
            # Adjust for park factor
            wrc_per_pa = wrc_per_pa / park_factor
            
            # Convert to wRC+
            wrc_plus = (wrc_per_pa / (constants.runs_per_win / 600)) * 100
            
            return max(0, round(wrc_plus))
            
        except Exception as e:
            logger.error(f"Error calculating wRC+: {e}")
            return 100
    
    def calculate_iso(self, stats: Dict) -> float:
        """Calculate Isolated Power (ISO)"""
        try:
            ab = stats.get('AB', 0)
            if ab == 0:
                return 0.0
            
            doubles = stats.get('2B', 0)
            triples = stats.get('3B', 0)
            homers = stats.get('HR', 0)
            
            extra_bases = doubles + (2 * triples) + (3 * homers)
            return extra_bases / ab
            
        except Exception as e:
            logger.error(f"Error calculating ISO: {e}")
            return 0.0
    
    def calculate_babip(self, stats: Dict) -> float:
        """Calculate Batting Average on Balls In Play (BABIP)"""
        try:
            hits = stats.get('H', 0)
            homers = stats.get('HR', 0)
            ab = stats.get('AB', 0)
            strikeouts = stats.get('SO', 0)
            
            hits_minus_hr = hits - homers
            ab_minus_hr_minus_so = ab - homers - strikeouts
            
            return hits_minus_hr / ab_minus_hr_minus_so if ab_minus_hr_minus_so > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating BABIP: {e}")
            return 0.0
    
    def calculate_bb_rate(self, stats: Dict) -> float:
        """Calculate Walk Rate (BB%)"""
        try:
            bb = stats.get('BB', 0)
            pa = stats.get('PA', 0)
            
            return bb / pa if pa > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating BB%: {e}")
            return 0.0
    
    def calculate_k_rate(self, stats: Dict) -> float:
        """Calculate Strikeout Rate (K%)"""
        try:
            so = stats.get('SO', 0)
            pa = stats.get('PA', 0)
            
            return so / pa if pa > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating K%: {e}")
            return 0.0
    
    # PITCHING ADVANCED STATS
    
    def calculate_fip(self, stats: Dict, constants: LeagueConstants) -> float:
        """Calculate Fielding Independent Pitching (FIP)"""
        try:
            hr = stats.get('HR', 0)
            bb = stats.get('BB', 0)
            hbp = stats.get('HBP', 0)
            so = stats.get('SO', 0)
            ip = stats.get('IP', 0)
            
            if ip == 0:
                return 0.0
            
            # FIP formula: ((13*HR)+(3*(BB+HBP))-(2*K))/IP + constant
            fip = ((13 * hr) + (3 * (bb + hbp)) - (2 * so)) / ip + constants.fip_constant
            
            return max(0.0, fip)
            
        except Exception as e:
            logger.error(f"Error calculating FIP: {e}")
            return 0.0
    
    def calculate_xfip(self, stats: Dict, constants: LeagueConstants) -> float:
        """Calculate Expected Fielding Independent Pitching (xFIP)"""
        try:
            bb = stats.get('BB', 0)
            hbp = stats.get('HBP', 0)
            so = stats.get('SO', 0)
            ip = stats.get('IP', 0)
            
            # Estimate fly balls (approximate)
            total_batters = stats.get('H', 0) + stats.get('BB', 0) + stats.get('HBP', 0) + stats.get('SO', 0)
            estimated_fb = total_batters * 0.35  # Rough estimate
            
            if ip == 0:
                return 0.0
            
            # Expected home runs based on league average HR/FB rate
            expected_hr = estimated_fb * constants.league_hr_per_fb
            
            # xFIP calculation
            xfip = ((13 * expected_hr) + (3 * (bb + hbp)) - (2 * so)) / ip + constants.fip_constant
            
            return max(0.0, xfip)
            
        except Exception as e:
            logger.error(f"Error calculating xFIP: {e}")
            return 0.0
    
    def calculate_whip(self, stats: Dict) -> float:
        """Calculate Walks plus Hits per Inning Pitched (WHIP)"""
        try:
            hits = stats.get('H', 0)
            bb = stats.get('BB', 0)
            ip = stats.get('IP', 0)
            
            return (hits + bb) / ip if ip > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating WHIP: {e}")
            return 0.0
    
    def calculate_era_plus(self, stats: Dict, constants: LeagueConstants, 
                          park_factor: float = 1.0) -> int:
        """Calculate ERA+ (ERA adjusted for league and park)"""
        try:
            era = stats.get('ERA', 0)
            if era == 0:
                return 100
            
            # ERA+ = (League ERA / Player ERA) * 100, adjusted for park
            era_plus = (constants.league_era / era) * 100 / park_factor
            
            return max(0, round(era_plus))
            
        except Exception as e:
            logger.error(f"Error calculating ERA+: {e}")
            return 100
    
    def calculate_k_bb_ratio(self, stats: Dict) -> float:
        """Calculate Strikeout to Walk Ratio (K/BB)"""
        try:
            so = stats.get('SO', 0)
            bb = stats.get('BB', 0)
            
            return so / bb if bb > 0 else float('inf') if so > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating K/BB: {e}")
            return 0.0
    
    def calculate_pitcher_babip(self, stats: Dict) -> float:
        """Calculate BABIP allowed by pitcher"""
        try:
            hits = stats.get('H', 0)
            hr = stats.get('HR', 0)
            so = stats.get('SO', 0)
            
            # Estimate batters faced
            ip = stats.get('IP', 0)
            bb = stats.get('BB', 0)
            hbp = stats.get('HBP', 0)
            
            # Rough estimate of batters faced
            bf = round(ip * 3) + hits + bb + hbp
            
            hits_minus_hr = hits - hr
            bf_minus_hr_minus_so = bf - hr - so
            
            return hits_minus_hr / bf_minus_hr_minus_so if bf_minus_hr_minus_so > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating pitcher BABIP: {e}")
            return 0.0
    
    def calculate_lob_rate(self, stats: Dict) -> float:
        """Calculate Left on Base percentage (LOB%)"""
        try:
            hits = stats.get('H', 0)
            bb = stats.get('BB', 0)
            hbp = stats.get('HBP', 0)
            runs = stats.get('R', 0)
            hr = stats.get('HR', 0)
            
            baserunners = hits + bb + hbp
            runners_scored = runs - hr  # Subtract HR since they score automatically
            
            if baserunners == 0:
                return 0.0
            
            lob_rate = (baserunners - runners_scored) / baserunners
            return max(0.0, min(1.0, lob_rate))
            
        except Exception as e:
            logger.error(f"Error calculating LOB%: {e}")
            return constants.league_lob_rate
    
    # CALCULATION METHODS FOR DATABASE INTEGRATION
    
    async def calculate_all_advanced_batting_stats(self, player_stats: Dict, season: int, 
                                                  league: str = "MLB") -> Dict:
        """Calculate all advanced batting statistics for a player"""
        try:
            constants = await self.get_league_constants(season, league)
            
            advanced_stats = {
                'wOBA': round(self.calculate_woba(player_stats, constants), 3),
                'wRC+': self.calculate_wrc_plus(player_stats, constants),
                'ISO': round(self.calculate_iso(player_stats), 3),
                'BABIP': round(self.calculate_babip(player_stats), 3),
                'BB%': round(self.calculate_bb_rate(player_stats) * 100, 1),
                'K%': round(self.calculate_k_rate(player_stats) * 100, 1),
            }
            
            return advanced_stats
            
        except Exception as e:
            logger.error(f"Error calculating advanced batting stats: {e}")
            return {}
    
    async def calculate_all_advanced_pitching_stats(self, player_stats: Dict, season: int,
                                                   league: str = "MLB") -> Dict:
        """Calculate all advanced pitching statistics for a player"""
        try:
            constants = await self.get_league_constants(season, league)
            
            advanced_stats = {
                'FIP': round(self.calculate_fip(player_stats, constants), 2),
                'xFIP': round(self.calculate_xfip(player_stats, constants), 2),
                'WHIP': round(self.calculate_whip(player_stats), 3),
                'ERA+': self.calculate_era_plus(player_stats, constants),
                'K/BB': round(self.calculate_k_bb_ratio(player_stats), 2),
                'BABIP': round(self.calculate_pitcher_babip(player_stats), 3),
                'LOB%': round(self.calculate_lob_rate(player_stats) * 100, 1),
            }
            
            return advanced_stats
            
        except Exception as e:
            logger.error(f"Error calculating advanced pitching stats: {e}")
            return {}
    
    async def update_player_advanced_stats(self, player_id: str, season: int, stats_type: str):
        """Update advanced stats for a specific player"""
        try:
            # Get base stats
            base_stats = await self.db_pool.fetchrow("""
                SELECT aggregated_stats
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = $3
            """, player_id, season, stats_type)
            
            if not base_stats:
                logger.warning(f"No base stats found for player {player_id}")
                return
            
            import json
            player_stats = json.loads(base_stats['aggregated_stats'])
            
            # Calculate advanced stats
            if stats_type == 'batting':
                advanced_stats = await self.calculate_all_advanced_batting_stats(player_stats, season)
            elif stats_type == 'pitching':
                advanced_stats = await self.calculate_all_advanced_pitching_stats(player_stats, season)
            else:
                logger.warning(f"Unsupported stats type: {stats_type}")
                return
            
            # Merge with existing stats
            updated_stats = {**player_stats, **advanced_stats}
            
            # Update in database
            await self.db_pool.execute("""
                UPDATE player_season_aggregates
                SET aggregated_stats = $4, last_updated = NOW()
                WHERE player_id = $1 AND season = $2 AND stats_type = $3
            """, player_id, season, stats_type, json.dumps(updated_stats))
            
            logger.info(f"Updated advanced {stats_type} stats for player {player_id}, season {season}")
            
        except Exception as e:
            logger.error(f"Failed to update advanced stats: {e}")
    
    async def calculate_all_players_advanced_stats(self, season: int):
        """Calculate advanced stats for all players in a season"""
        try:
            logger.info(f"Starting advanced stats calculation for {season} season")
            
            # Get all players with stats for the season
            players = await self.db_pool.fetch("""
                SELECT DISTINCT player_id, stats_type
                FROM player_season_aggregates
                WHERE season = $1
                ORDER BY player_id, stats_type
            """, season)
            
            total_players = len(players)
            logger.info(f"Processing advanced stats for {total_players} player records")
            
            for i, player_record in enumerate(players):
                if i % 100 == 0:
                    logger.info(f"Processing record {i+1}/{total_players}")
                
                await self.update_player_advanced_stats(
                    player_record['player_id'], 
                    season, 
                    player_record['stats_type']
                )
                
                # Small delay to prevent overwhelming the database
                await asyncio.sleep(0.01)
            
            logger.info(f"Completed advanced stats calculation for {season} season")
            
        except Exception as e:
            logger.error(f"Failed to calculate advanced stats for all players: {e}")