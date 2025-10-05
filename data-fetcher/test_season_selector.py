#!/usr/bin/env python3
"""Test season selector functionality for umpire scraper"""

import asyncio
import asyncpg
import logging
from umpire_scraper import update_umpire_scorecards

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_season_selector():
    """Test the season selector with a specific year"""

    # Connect to database
    pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        user='baseball_user',
        password='baseball_pass',
        database='baseball_sim',
        min_size=1,
        max_size=2
    )

    try:
        # Test with 2024 season
        logger.info("Testing season selector with 2024...")
        await update_umpire_scorecards(pool, season=2024)

        # Check what we got in the database
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM umpire_season_stats WHERE season = 2024"
        )
        logger.info(f"✓ Loaded {count} umpires for season 2024")

        # Check a sample record
        sample = await pool.fetchrow("""
            SELECT uss.season, u.name, uss.games_umped, uss.accuracy_pct
            FROM umpire_season_stats uss
            JOIN umpires u ON u.id = uss.umpire_id
            WHERE uss.season = 2024
            ORDER BY uss.games_umped DESC
            LIMIT 1
        """)

        if sample:
            logger.info(f"Sample: {sample['name']} - {sample['games_umped']} games, {sample['accuracy_pct']}% accuracy in {sample['season']}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_season_selector())
