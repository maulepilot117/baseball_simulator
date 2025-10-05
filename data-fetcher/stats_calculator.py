"""
Enhanced Statistics Calculator with Position-Specific Metrics
Combines batting, pitching, fielding, and advanced stats with catcher and outfielder analytics
"""
import asyncio
import logging
import json
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class CatcherMetrics:
    """Advanced catcher performance metrics"""
    framing_runs: float = 0.0
    blocking_runs: float = 0.0
    arm_runs: float = 0.0
    pop_time_seconds: float = 2.0
    exchange_time_seconds: float = 0.85
    framing_pct_above_avg: float = 0.0
    blocking_pct_above_avg: float = 0.0
    cs_above_avg: float = 0.0
    total_catcher_runs: float = 0.0


@dataclass
class OutfielderMetrics:
    """Advanced outfielder performance metrics"""
    range_runs: float = 0.0
    arm_runs: float = 0.0
    jump_rating: float = 20.0  # 20-80 scouting scale
    route_efficiency: float = 1.0
    sprint_speed: float = 0.0  # seconds to home
    max_speed_mph: float = 0.0
    first_step_time: float = 0.0  # seconds
    total_outfielder_runs: float = 0.0


class StatsCalculator:
    """Enhanced statistics calculator with position-specific metrics"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def calculate_all_season_stats(self, season: int):
        """Calculate all advanced statistics for a season"""
        logger.info(f"Calculating enhanced stats for {season}")

        # Get all players with stats
        players = await self.db_pool.fetch("""
            SELECT DISTINCT player_id, stats_type
            FROM player_season_aggregates
            WHERE season = $1
        """, season)

        # Process each player
        for player in players:
            await self._calculate_player_stats(
                player['player_id'],
                season,
                player['stats_type']
            )

        # Calculate position-specific metrics
        await self._calculate_position_specific_stats(season)

        logger.info(f"Completed enhanced stats calculation for {season}")

    async def _calculate_player_stats(self, player_id: str, season: int, stats_type: str):
        """Calculate advanced stats for a single player"""
        try:
            # Get base stats
            result = await self.db_pool.fetchrow("""
                SELECT aggregated_stats
                FROM player_season_aggregates
                WHERE player_id = $1 AND season = $2 AND stats_type = $3
            """, player_id, season, stats_type)

            if not result:
                return

            stats = json.loads(result['aggregated_stats'])

            # Calculate advanced stats based on type
            if stats_type == 'batting':
                advanced = self._calculate_batting_advanced(stats)
            elif stats_type == 'pitching':
                advanced = self._calculate_pitching_advanced(stats)
            elif stats_type == 'fielding':
                advanced = self._calculate_fielding_advanced(stats)
            else:
                return

            # Merge advanced stats with base stats
            stats.update(advanced)

            # Save back to database
            await self.db_pool.execute("""
                UPDATE player_season_aggregates
                SET aggregated_stats = $4, last_updated = NOW()
                WHERE player_id = $1 AND season = $2 AND stats_type = $3
            """, player_id, season, stats_type, json.dumps(stats))

        except Exception as e:
            logger.error(f"Error calculating stats for player {player_id}: {e}")

    async def _calculate_position_specific_stats(self, season: int):
        """Calculate position-specific statistics for catchers and outfielders"""
        logger.info(f"Calculating position-specific stats for {season}")

        # Calculate catcher metrics
        await self._calculate_catcher_stats(season)

        # Calculate outfielder metrics
        await self._calculate_outfielder_stats(season)

    async def _calculate_catcher_stats(self, season: int):
        """Calculate advanced catcher metrics"""
        logger.info(f"Calculating catcher stats for {season}")

        # Get all catchers for the season
        catchers = await self.db_pool.fetch("""
            SELECT DISTINCT p.id, p.player_id, p.full_name
            FROM players p
            JOIN player_season_aggregates psa ON p.id = psa.player_id
            WHERE psa.season = $1 AND psa.stats_type = 'fielding'
              AND p.position = 'C'
        """, season)

        for catcher in catchers:
            try:
                metrics = await self._calculate_single_catcher_metrics(
                    catcher['id'], season, catcher['full_name']
                )

                if metrics:
                    # Store catcher metrics in database
                    await self.db_pool.execute("""
                        INSERT INTO catcher_stats (player_id, season, framing_runs, blocking_runs,
                                                 arm_runs, pop_time, exchange_time, framing_pct_above,
                                                 blocking_pct_above, cs_above_avg, total_catcher_runs)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (player_id, season) DO UPDATE SET
                            framing_runs = EXCLUDED.framing_runs,
                            blocking_runs = EXCLUDED.blocking_runs,
                            arm_runs = EXCLUDED.arm_runs,
                            pop_time = EXCLUDED.pop_time,
                            exchange_time = EXCLUDED.exchange_time,
                            framing_pct_above = EXCLUDED.framing_pct_above,
                            blocking_pct_above = EXCLUDED.blocking_pct_above,
                            cs_above_avg = EXCLUDED.cs_above_avg,
                            total_catcher_runs = EXCLUDED.total_catcher_runs,
                            updated_at = NOW()
                    """, catcher['id'], season,
                        metrics.framing_runs, metrics.blocking_runs, metrics.arm_runs,
                        metrics.pop_time_seconds, metrics.exchange_time_seconds,
                        metrics.framing_pct_above_avg, metrics.blocking_pct_above_avg,
                        metrics.cs_above_avg, metrics.total_catcher_runs)

            except Exception as e:
                logger.error(f"Error calculating catcher stats for {catcher['full_name']}: {e}")

    async def _calculate_single_catcher_metrics(self, player_id: str, season: int, player_name: str) -> Optional[CatcherMetrics]:
        """Calculate advanced metrics for a single catcher"""
        # This is a simplified calculation - in reality, you'd need pitch-by-pitch data
        # and advanced fielding metrics from sources like Baseball Savant

        # Get fielding stats
        fielding_result = await self.db_pool.fetchrow("""
            SELECT aggregated_stats
            FROM player_season_aggregates
            WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
        """, player_id, season)

        if not fielding_result:
            return None

        fielding_stats = json.loads(fielding_result['aggregated_stats'])
        games = fielding_stats.get('gamesPlayed', 0)

        if games == 0:
            return None

        # Simplified calculations based on available data
        # In a real implementation, these would use Statcast data
        metrics = CatcherMetrics()

        # Framing runs (simplified - based on caught stealing above average)
        cs = fielding_stats.get('caughtStealing', 0)
        cs_pct = cs / max(1, (cs + fielding_stats.get('stolenBasesAllowed', 0)))
        league_avg_cs_pct = 0.27  # Approximate MLB average
        cs_above_avg = (cs_pct - league_avg_cs_pct) * games
        metrics.cs_above_avg = round(cs_above_avg, 1)

        # Simplified framing runs based on CS above average
        metrics.framing_runs = round(cs_above_avg * 0.15, 1)

        # Blocking runs (simplified estimate)
        pb = fielding_stats.get('passedBalls', 0)
        sb = fielding_stats.get('stolenBasesAllowed', 0)
        blocking_efficiency = 1 - (pb / max(1, pb + cs))
        league_avg_blocking = 0.70
        metrics.blocking_runs = round((blocking_efficiency - league_avg_blocking) * games * 0.05, 1)

        # Arm runs (based on SB/CS ratio)
        if cs + sb > 0:
            arm_strength = cs / (cs + sb)
            league_avg_arm = 0.75
            metrics.arm_runs = round((arm_strength - league_avg_arm) * games * 0.1, 1)

        # Total catcher runs
        metrics.total_catcher_runs = round(
            metrics.framing_runs + metrics.blocking_runs + metrics.arm_runs, 1
        )

        logger.debug(f"Calculated catcher metrics for {player_name}: FRAMING_RUNS={metrics.framing_runs}, TOTAL_CATCHER_RUNS={metrics.total_catcher_runs}")

        return metrics

    async def _calculate_outfielder_stats(self, season: int):
        """Calculate advanced outfielder metrics"""
        logger.info(f"Calculating outfielder stats for {season}")

        # Get all outfielders for the season
        positions = ['LF', 'CF', 'RF']
        outfielders = await self.db_pool.fetch("""
            SELECT DISTINCT p.id, p.player_id, p.full_name, p.position
            FROM players p
            JOIN player_season_aggregates psa ON p.id = psa.player_id
            WHERE psa.season = $1 AND psa.stats_type = 'fielding'
              AND p.position = ANY($2)
        """, season, positions)

        for outfielder in outfielders:
            try:
                metrics = await self._calculate_single_outfielder_metrics(
                    outfielder['id'], season, outfielder['full_name'], outfielder['position']
                )

                if metrics:
                    # Store outfielder metrics in database
                    await self.db_pool.execute("""
                        INSERT INTO outfielder_stats (player_id, season, position, range_runs, arm_runs,
                                                   jump_rating, route_efficiency, sprint_speed, max_speed,
                                                   first_step_time, total_outfielder_runs)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (player_id, season) DO UPDATE SET
                            range_runs = EXCLUDED.range_runs,
                            arm_runs = EXCLUDED.arm_runs,
                            jump_rating = EXCLUDED.jump_rating,
                            route_efficiency = EXCLUDED.route_efficiency,
                            sprint_speed = EXCLUDED.sprint_speed,
                            max_speed = EXCLUDED.max_speed,
                            first_step_time = EXCLUDED.first_step_time,
                            total_outfielder_runs = EXCLUDED.total_outfielder_runs,
                            updated_at = NOW()
                    """, outfielder['id'], season, outfielder['position'],
                        metrics.range_runs, metrics.arm_runs, metrics.jump_rating,
                        metrics.route_efficiency, metrics.sprint_speed, metrics.max_speed,
                        metrics.first_step_time, metrics.total_outfielder_runs)

            except Exception as e:
                logger.error(f"Error calculating outfielder stats for {outfielder['full_name']}: {e}")

    async def _calculate_single_outfielder_metrics(self, player_id: str, season: int, player_name: str, position: str) -> Optional[OutfielderMetrics]:
        """Calculate advanced metrics for a single outfielder"""
        # Get batting and fielding stats
        batting_result = await self.db_pool.fetchrow("""
            SELECT aggregated_stats
            FROM player_season_aggregates
            WHERE player_id = $1 AND season = $2 AND stats_type = 'batting'
        """, player_id, season)

        fielding_result = await self.db_pool.fetchrow("""
            SELECT aggregated_stats
            FROM player_season_aggregates
            WHERE player_id = $1 AND season = $2 AND stats_type = 'fielding'
        """, player_id, season)

        if not fielding_result:
            return None

        fielding_stats = json.loads(fielding_result['aggregated_stats'])
        games = fielding_stats.get('gamesPlayed', 0)

        if games == 0:
            return None

        metrics = OutfielderMetrics()

        # Range runs (simplified - based on defensive stats)
        assists = fielding_stats.get('assists', 0)
        putouts = fielding_stats.get('putOuts', 0)
        errors = fielding_stats.get('errors', 0)

        # Different expectations for different positions
        position_multipliers = {'LF': 1.2, 'CF': 1.0, 'RF': 1.1}
        pos_multiplier = position_multipliers.get(position, 1.0)

        # Simplified range calculation
        if position == 'CF':
            # Center fielders are expected to have more assists
            range_factor = (assists + putouts) / games if games > 0 else 0
            league_avg_range = 2.5
            metrics.range_runs = round((range_factor - league_avg_range) * 0.3, 1)
        else:
            # Corner outfielders
            range_factor = putouts / games if games > 0 else 0
            league_avg_range = 1.8 * pos_multiplier
            metrics.range_runs = round((range_factor - league_avg_range) * 0.2, 1)

        # Arm runs (based on assists for outfielders)
        if position == 'RF':
            # Right fielders expected to have strongest arms
            league_avg_assists = 0.12 * games
            arm_strength = assists - league_avg_assists
            metrics.arm_runs = round(arm_strength * 0.1, 1)
        elif position == 'CF':
            # Center fielders expected to have moderate assists
            league_avg_assists = 0.08 * games
            arm_strength = assists - league_avg_assists
            metrics.arm_runs = round(arm_strength * 0.08, 1)
        else:  # LF
            # Left fielders expected to have fewer assists
            league_avg_assists = 0.05 * games
            arm_strength = assists - league_avg_assists
            metrics.arm_runs = round(arm_strength * 0.06, 1)

        # Jump rating and other speed metrics (simplified)
        # In a real implementation, these would come from Statcast data
        if batting_result:
            batting_stats = json.loads(batting_result['aggregated_stats'])
            speed_indicators = batting_stats.get('stolenBases', 0)
            metrics.jump_rating = min(80, max(20, 40 + (speed_indicators * 2)))
            metrics.route_efficiency = 0.95 + (speed_indicators * 0.005)

        # Total outfielder runs
        metrics.total_outfielder_runs = round(metrics.range_runs + metrics.arm_runs, 1)

        logger.debug(f"Calculated outfielder metrics for {player_name}: RANGE_RUNS={metrics.range_runs}, ARM_RUNS={metrics.arm_runs}, TOTAL_OUTFIELDER_RUNS={metrics.total_outfielder_runs}")

        return metrics

    def _calculate_batting_advanced(self, stats: Dict) -> Dict:
        """Calculate advanced batting statistics"""
        advanced = {}

        # Basic rate stats
        ab = stats.get('atBats', 0)
        h = stats.get('hits', 0)
        bb = stats.get('baseOnBalls', 0)
        hbp = stats.get('hitByPitch', 0)
        sf = stats.get('sacFlies', 0)
        pa = ab + bb + hbp + sf

        if ab > 0:
            # OPS (On-base Plus Slugging)
            obp = float(stats.get('obp', 0))
            slg = float(stats.get('slg', 0))
            advanced['OPS'] = round(obp + slg, 3)

            # ISO (Isolated Power)
            avg = float(stats.get('avg', 0))
            advanced['ISO'] = round(slg - avg, 3)

            # BABIP (simplified)
            hr = stats.get('homeRuns', 0)
            so = stats.get('strikeOuts', 0)
            babip_h = h - hr
            babip_ab = ab - hr - so + sf
            if babip_ab > 0:
                advanced['BABIP'] = round(babip_h / babip_ab, 3)

        if pa > 0:
            # Walk and strikeout rates
            advanced['BB%'] = round((bb / pa) * 100, 1)
            advanced['K%'] = round((stats.get('strikeOuts', 0) / pa) * 100, 1)

        # wOBA (simplified version)
        if pa > 0:
            singles = h - stats.get('doubles', 0) - stats.get('triples', 0) - stats.get('homeRuns', 0)
            woba = (0.69 * bb + 0.72 * hbp + 0.88 * singles +
                   1.247 * stats.get('doubles', 0) + 1.578 * stats.get('triples', 0) +
                   2.031 * stats.get('homeRuns', 0)) / pa
            advanced['wOBA'] = round(woba, 3)

        return advanced

    def _calculate_pitching_advanced(self, stats: Dict) -> Dict:
        """Calculate advanced pitching statistics"""
        advanced = {}

        ip = float(stats.get('inningsPitched', '0'))
        if ip == 0:
            return advanced

        # FIP (Fielding Independent Pitching)
        hr = stats.get('homeRuns', 0)
        bb = stats.get('baseOnBalls', 0)
        hbp = stats.get('hitBatsmen', 0)
        so = stats.get('strikeOuts', 0)

        fip = ((13 * hr) + (3 * (bb + hbp)) - (2 * so)) / ip + 3.20
        advanced['FIP'] = round(fip, 2)

        # WHIP
        h = stats.get('hits', 0)
        whip = (h + bb) / ip
        advanced['WHIP'] = round(whip, 3)

        # K/9 and BB/9
        advanced['K/9'] = round((so / ip) * 9, 1)
        advanced['BB/9'] = round((bb / ip) * 9, 1)

        # K/BB ratio
        if bb > 0:
            advanced['K/BB'] = round(so / bb, 2)

        return advanced

    def _calculate_fielding_advanced(self, stats: Dict) -> Dict:
        """Calculate advanced fielding statistics"""
        advanced = {}

        # Range Factor
        po = stats.get('putOuts', 0)
        a = stats.get('assists', 0)
        g = stats.get('gamesPlayed', 0)

        if g > 0:
            advanced['RF'] = round((po + a) / g, 2)

        # Fielding percentage
        e = stats.get('errors', 0)
        tc = po + a + e

        if tc > 0:
            advanced['FPCT'] = round((tc - e) / tc, 3)

        return advanced
