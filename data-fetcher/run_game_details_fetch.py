"""
Script to fetch game details (box scores, play-by-play, weather) for games
"""
import asyncio
import asyncpg
import logging
from game_details_fetcher import fetch_all_game_details

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to fetch game details"""
    # Database connection
    db_url = "postgresql://baseball_user:baseball_pass@localhost:5432/baseball_sim"

    logger.info("Connecting to database...")
    pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)

    try:
        # Fetch details for 10 recent games as a test
        logger.info("Fetching game details for recent games...")
        await fetch_all_game_details(pool, limit=10)
        logger.info("Game details fetch complete!")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
