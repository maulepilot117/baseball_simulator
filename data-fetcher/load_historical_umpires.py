#!/usr/bin/env python3
"""
Load historical umpire data for the last 5+ years from umpscorecards.com

umpscorecards.com provides historical season data via a season selector dropdown
on the /umpires page. This script loads data for years 2020-2025.
"""

import asyncio
import asyncpg
import logging
from umpire_scraper import update_umpire_scorecards

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_all_historical_data():
    """Load umpire data for years 2020-2025"""

    # Connect to database
    pool = await asyncpg.create_pool(
        host='baseball-db',
        user='baseball_user',
        password='baseball_pass',
        database='baseball_sim',
        min_size=1,
        max_size=2
    )

    try:
        # Only load current season - historical season selection not working on umpscorecards.com
        # The site has a season dropdown but it doesn't respond to programmatic selection
        years = [2025]

        logger.info(f"Starting umpire data load for current season: {years}")
        logger.info("Note: Historical data scraping from umpscorecards.com requires manual interaction")

        for year in years:
            logger.info(f"\n{'='*60}")
            logger.info(f"Loading data for year {year}")
            logger.info(f"{'='*60}\n")

            try:
                await update_umpire_scorecards(pool, season=year)

                # Check what we loaded
                count = await pool.fetchval(
                    "SELECT COUNT(*) FROM umpire_season_stats WHERE season = $1",
                    year
                )
                logger.info(f"✓ Successfully loaded {count} umpires for season {year}")

                # Get a sample
                sample = await pool.fetchrow("""
                    SELECT uss.season, u.name, uss.games_umped, uss.accuracy_pct
                    FROM umpire_season_stats uss
                    JOIN umpires u ON u.id = uss.umpire_id
                    WHERE uss.season = $1
                    ORDER BY uss.games_umped DESC
                    LIMIT 1
                """, year)

                if sample:
                    logger.info(
                        f"  Top umpire: {sample['name']} - "
                        f"{sample['games_umped']} games, "
                        f"{sample['accuracy_pct']}% accuracy"
                    )

                # Brief pause between years to avoid overwhelming the site
                if year != years[-1]:
                    logger.info("Waiting 5 seconds before next year...")
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error loading data for year {year}: {e}")
                continue

        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info("FINAL SUMMARY")
        logger.info(f"{'='*60}\n")

        total_records = await pool.fetchval(
            "SELECT COUNT(*) FROM umpire_season_stats"
        )
        logger.info(f"Total season records: {total_records}")

        total_umpires = await pool.fetchval(
            "SELECT COUNT(*) FROM umpires"
        )
        logger.info(f"Total unique umpires: {total_umpires}")

        # Records by season
        by_season = await pool.fetch("""
            SELECT season, COUNT(*) as umpire_count
            FROM umpire_season_stats
            ORDER BY season DESC
        """)

        logger.info("\nRecords by season:")
        for row in by_season:
            logger.info(f"  {row['season']}: {row['umpire_count']} umpires")

        logger.info("\n✓ Historical data load complete!")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(load_all_historical_data())
