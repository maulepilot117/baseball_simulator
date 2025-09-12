"""
Enhanced Umpire Scorecard Data Fetcher
Fetches and processes umpire performance data from umpscorecards.com and other sources
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass

import asyncpg
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class UmpireMetrics:
    """Structured umpire performance data"""
    name: str
    games_umped: int = 0
    accuracy_pct: float = 0.0
    consistency_pct: float = 0.0
    favor_home: float = 0.0
    expected_accuracy: float = 0.0
    expected_consistency: float = 0.0
    correct_calls: int = 0
    incorrect_calls: int = 0
    total_calls: int = 0
    strike_pct: float = 0.0
    ball_pct: float = 0.0
    k_pct_above_avg: float = 0.0
    bb_pct_above_avg: float = 0.0
    home_plate_calls_per_game: float = 0.0
    last_updated: Optional[datetime] = None


class UmpireScorecardClient:
    """Client for fetching umpire performance data"""

    BASE_URL = "https://umpscorecards.com"
    API_BASE_URL = "https://api.umpscorecards.com/v1"

    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'BaseballSimulation/2.0 (research@baseballsim.com)',
                'Accept': 'application/json',
                'Authorization': 'Bearer research_token_2024'  # Placeholder for API key
            },
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        self._last_request_time = datetime.min

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _rate_limited_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make rate-limited request to umpire API"""
        # Implement rate limiting
        elapsed = (datetime.now() - self._last_request_time).total_seconds()
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)

        self._last_request_time = datetime.now()

        url = f"{self.API_BASE_URL}{endpoint}"
        response = await self.client.get(url, params=params)

        if response.status_code == 429:
            logger.warning("Rate limited, backing off...")
            await asyncio.sleep(5.0)
            return await self._rate_limited_request(endpoint, params)

        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError))
    )
    async def fetch_umpire_list(self, season: Optional[int] = None) -> List[UmpireMetrics]:
        """Fetch list of active umpires with performance data"""
        try:
            params = {}
            if season:
                params['season'] = season

            logger.info(f"Fetching umpire list for season {season or 'current'}")
            data = await self._rate_limited_request("/umpires", params)

            umpires = []
            for ump_data in data.get('umpires', []):
                metrics = self._parse_umpire_data(ump_data)
                if metrics:
                    umpires.append(metrics)

            logger.info(f"Successfully fetched {len(umpires)} umpires")
            return umpires

        except Exception as e:
            logger.error(f"Failed to fetch umpire list: {e}")
            # Fallback to alternative data source
            return await self._fetch_fallback_umpire_data(season)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def fetch_umpire_details(self, umpire_name: str) -> Optional[UmpireMetrics]:
        """Fetch detailed performance data for specific umpire"""
        try:
            params = {'name': umpire_name, 'include_detailed': 'true'}
            data = await self._rate_limited_request("/umpires/details", params)

            if data and 'umpire' in data:
                return self._parse_umpire_data(data['umpire'])

        except Exception as e:
            logger.error(f"Failed to fetch details for umpire {umpire_name}: {e}")

        return None

    def _parse_umpire_data(self, data: Dict[str, Any]) -> Optional[UmpireMetrics]:
        """Parse raw umpire data into structured format"""
        try:
            name = data.get('name', '').strip()
            if not name:
                return None

            # Validate and convert numeric fields
            games = max(0, data.get('games', 0))
            accuracy = max(0, min(100, data.get('accuracy', 0)))
            consistency = max(0, min(100, data.get('consistency', 0)))
            favor_home = max(-50, min(50, data.get('favor_home', 0)))  # -50 to +50 range

            return UmpireMetrics(
                name=name,
                games_umped=games,
                accuracy_pct=round(accuracy, 2),
                consistency_pct=round(consistency, 2),
                favor_home=round(favor_home, 2),
                expected_accuracy=round(data.get('expected_accuracy', 0), 2),
                expected_consistency=round(data.get('expected_consistency', 0), 2),
                correct_calls=data.get('correct_calls', 0),
                incorrect_calls=data.get('incorrect_calls', 0),
                total_calls=data.get('total_calls', 0),
                strike_pct=round(data.get('strike_percentage', 0), 2),
                ball_pct=round(data.get('ball_percentage', 0), 2),
                k_pct_above_avg=round(data.get('k_pct_above_avg', 0), 2),
                bb_pct_above_avg=round(data.get('bb_pct_above_avg', 0), 2),
                home_plate_calls_per_game=round(data.get('calls_per_game', 0), 2),
                last_updated=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error parsing umpire data {data}: {e}")
            return None

    async def _fetch_fallback_umpire_data(self, season: Optional[int] = None) -> List[UmpireMetrics]:
        """Fallback method when primary API fails"""
        logger.info("Using fallback umpire data source")

        # This would implement alternative data sources or cached data
        # For now, return empty list - in production this could load from local files
        # or alternative APIs like MLB's umpire data

        try:
            # Attempt to fetch from MLB's public API as backup
            return await self._fetch_mlb_umpire_fallback(season)
        except Exception as e:
            logger.error(f"Fallback data source also failed: {e}")
            return []

    async def _fetch_mlb_umpire_fallback(self, season: Optional[int] = None) -> List[UmpireMetrics]:
        """Use MLB's public API as fallback for basic umpire info"""
        try:
            # MLB's jobs/umpires endpoint for basic umpire roster
            url = "https://statsapi.mlb.com/api/v1/jobs/umpires"
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            umpires = []

            for ump in data.get('roster', []):
                # Create basic UmpireMetrics from MLB data
                # This won't have performance metrics, but provides basic info
                metrics = UmpireMetrics(
                    name=ump.get('fullName', ''),
                    games_umped=0,  # Would need to be populated from other sources
                    last_updated=datetime.now()
                )
                if metrics.name:
                    umpires.append(metrics)

            logger.info(f"Fetched {len(umpires)} basic umpire records from MLB API")
            return umpires

        except Exception as e:
            logger.error(f"MLB fallback failed: {e}")
            return []


async def update_umpire_scorecards(db_pool: asyncpg.Pool, season: Optional[int] = None):
    """Main function to update umpire scorecard data in database"""

    async with UmpireScorecardClient() as client:
        try:
            logger.info("Starting umpire scorecard data update")

            # Fetch current umpire data
            umpires = await client.fetch_umpire_list(season)

            if not umpires:
                logger.warning("No umpire data fetched, skipping update")
                return

            success_count = 0

            for umpire in umpires:
                try:
                    # Create or update umpire record
                    ump_uuid = await db_pool.fetchval("""
                        INSERT INTO umpires (umpire_id, name)
                        VALUES ($1, $2)
                        ON CONFLICT (umpire_id) DO UPDATE
                        SET name = EXCLUDED.name
                        RETURNING id
                    """, f"ump_{umpire.name.lower().replace(' ', '_').replace('.', '')}", umpire.name)

                    # Update performance metrics
                    await db_pool.execute("""
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
                            strike_pct = $11,
                            ball_pct = $12,
                            k_pct_above_avg = $13,
                            bb_pct_above_avg = $14,
                            home_plate_calls_per_game = $15,
                            updated_at = NOW()
                        WHERE id = $1
                    """, ump_uuid,
                        umpire.games_umped,
                        umpire.accuracy_pct,
                        umpire.consistency_pct,
                        umpire.favor_home,
                        umpire.expected_accuracy,
                        umpire.expected_consistency,
                        umpire.correct_calls,
                        umpire.incorrect_calls,
                        umpire.total_calls,
                        umpire.strike_pct,
                        umpire.ball_pct,
                        umpire.k_pct_above_avg,
                        umpire.bb_pct_above_avg,
                        umpire.home_plate_calls_per_game)

                    success_count += 1

                except Exception as e:
                    logger.error(f"Error updating umpire {umpire.name}: {e}")

            logger.info(f"Successfully updated {success_count} umpire scorecards")

        except Exception as e:
            logger.error(f"Failed to update umpire scorecards: {e}")
            raise


# Backward compatibility function
async def update_umpire_scorecards_legacy(db_pool: asyncpg.Pool):
    """Legacy function for backward compatibility"""
    await update_umpire_scorecards(db_pool)
