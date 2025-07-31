"""
Umpire scorecard data scraper
Fetches umpire performance metrics from umpscorecards.com
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime

import asyncpg
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class UmpireScorecardScraper:
    """Scrapes umpire performance data from umpscorecards.com"""
    
    BASE_URL = "https://umpscorecards.com"
    DATA_URL = f"{BASE_URL}/api/umpires"
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                'User-Agent': 'BaseballSimulation/2.0',
                'Accept': 'application/json'
            }
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def fetch_all_umpire_data(self):
        """Fetch all umpire scorecards data"""
        try:
            logger.info("Fetching umpire scorecard data...")
            
            # Try the API endpoint first
            response = await self.client.get(self.DATA_URL)
            
            if response.status_code == 200:
                umpires = response.json()
                await self._process_umpire_data(umpires)
            else:
                # Fallback to scraping if API fails
                logger.warning(f"API returned status {response.status_code}, trying web scraping")
                await self._scrape_umpire_list()
                
        except Exception as e:
            logger.error(f"Error fetching umpire data: {e}")
            raise
    
    async def _process_umpire_data(self, umpires: List[Dict]):
        """Process and save umpire scorecard data"""
        success_count = 0
        
        for umpire in umpires:
            try:
                # Extract umpire name and create ID
                name = umpire.get('name', '')
                if not name:
                    continue
                
                # Create a consistent umpire_id from name
                umpire_id = f"ump_{name.lower().replace(' ', '_').replace('.', '')}"
                
                # First, ensure umpire exists
                ump_uuid = await self.db_pool.fetchval("""
                    INSERT INTO umpires (umpire_id, name)
                    VALUES ($1, $2)
                    ON CONFLICT (umpire_id) DO UPDATE
                    SET name = EXCLUDED.name
                    RETURNING id
                """, umpire_id, name)
                
                # Update with scorecard data
                await self.db_pool.execute("""
                    UPDATE umpires SET
                        games_umped = $2,
                        accuracy_pct = $3,
                        consistency_pct = $4,
                        favor_home = $5,
                        expected_accuracy = $6,
                        expected_consistency = $7,
                        correct_calls = $8,
                        incorrect_calls = $9,
                        total_calls = $10,
                        updated_at = NOW()
                    WHERE id = $1
                """, ump_uuid,
                    umpire.get('games', 0),
                    umpire.get('accuracy', 0),
                    umpire.get('consistency', 0),
                    umpire.get('favor_home', 0),
                    umpire.get('expected_accuracy', 0),
                    umpire.get('expected_consistency', 0),
                    umpire.get('correct_calls', 0),
                    umpire.get('incorrect_calls', 0),
                    umpire.get('total_calls', 0))
                
                success_count += 1
                logger.debug(f"Updated scorecard data for umpire: {name}")
                
            except Exception as e:
                logger.error(f"Error processing umpire {umpire.get('name', 'Unknown')}: {e}")
        
        logger.info(f"Successfully updated {success_count} umpire scorecards")
    
    async def _scrape_umpire_list(self):
        """Fallback method to scrape umpire data from website"""
        try:
            response = await self.client.get(f"{self.BASE_URL}/umpires")
            if response.status_code != 200:
                logger.error(f"Failed to scrape umpire list: {response.status_code}")
                return
            
            # Parse HTML and extract umpire data
            # This is a simplified example - actual implementation would depend on site structure
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.warning("Web scraping implementation needed for umpscorecards.com")
            
        except Exception as e:
            logger.error(f"Error scraping umpire list: {e}")


async def update_umpire_scorecards(db_pool: asyncpg.Pool):
    """Standalone function to update umpire scorecards"""
    async with UmpireScorecardScraper(db_pool) as scraper:
        await scraper.fetch_all_umpire_data()