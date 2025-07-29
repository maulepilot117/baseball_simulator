"""
Consolidated statistics calculator
Combines batting, pitching, fielding, and advanced stats in one place
"""
import asyncio
import logging
import json
from typing import Dict, Optional
from datetime import datetime

import asyncpg

logger = logging.getLogger(__name__)


class StatsCalculator:
    """Unified statistics calculator for all stat types"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def calculate_all_season_stats(self, season: int):
        """Calculate all advanced statistics for a season"""
        logger.info(f"Calculating advanced stats for {season}")
        
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
        
        logger.info(f"Completed advanced stats calculation for {season}")
    
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