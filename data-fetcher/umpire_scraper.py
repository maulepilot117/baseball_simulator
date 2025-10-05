"""
Umpire Scorecard Data Scraper using Playwright
Scrapes umpire performance data from umpscorecards.com
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import re

import asyncpg
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

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


class UmpireScraper:
    """Web scraper for umpire performance data using Playwright"""

    BASE_URL = "https://umpscorecards.com"
    UMPIRES_URL = f"{BASE_URL}/data/umpires"

    def get_season_url(self, season: Optional[int] = None) -> str:
        """Generate URL for specific season"""
        if season is None:
            return self.UMPIRES_URL

        # Try different URL patterns that sports sites commonly use
        # We'll try the first one that loads successfully
        return self.UMPIRES_URL  # For now, use base URL with season filter

    async def scrape_umpire_data(self, season: Optional[int] = None) -> List[UmpireMetrics]:
        """
        Scrape umpire performance data using Playwright
        """
        umpires = []

        try:
            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )

                try:
                    context = await browser.new_context(
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    )
                    page = await context.new_page()

                    logger.info(f"Navigating to {self.UMPIRES_URL}")

                    # Navigate to umpires page (use longer timeout and domcontentloaded instead of networkidle)
                    await page.goto(self.UMPIRES_URL, wait_until='domcontentloaded', timeout=60000)

                    # Wait for content to load
                    try:
                        await page.wait_for_selector('table, .umpire-card, [data-umpire]', timeout=15000)
                    except PlaywrightTimeout:
                        logger.warning("Timeout waiting for umpire data to load")

                    # Wait for page to fully render (longer wait for JS-heavy page)
                    await page.wait_for_timeout(5000)

                    # First, try to set the season if specified
                    if season:
                        try:
                            logger.info(f"Looking for season selector to set year to {season}")

                            # Common season selector patterns
                            season_selectors = [
                                'select[name*="season" i]',
                                'select[name*="year" i]',
                                'select[id*="season" i]',
                                'select[id*="year" i]',
                                'select[aria-label*="season" i]',
                                'select[aria-label*="year" i]',
                            ]

                            season_set = False
                            for selector in season_selectors:
                                try:
                                    element = await page.query_selector(selector)
                                    if element:
                                        # Check if this select has year options
                                        options = await page.query_selector_all(f'{selector} option')
                                        for option in options:
                                            option_text = await option.inner_text()
                                            option_value = await option.get_attribute('value')
                                            # Check if option contains the season year
                                            if str(season) in option_text or str(season) in str(option_value):
                                                logger.info(f"Found season selector: {selector}, setting to {season}")
                                                await page.select_option(selector, option_value)
                                                await page.wait_for_timeout(3000)  # Wait for data to reload
                                                season_set = True
                                                break
                                        if season_set:
                                            break
                                except Exception as e:
                                    logger.debug(f"Could not use season selector {selector}: {e}")
                                    continue

                            if not season_set:
                                logger.warning(f"Could not find season selector for {season}, using default page data")

                        except Exception as e:
                            logger.warning(f"Error setting season: {e}")

                    # Now set page size to show all umpires
                    try:
                        # Try to find and click page size dropdown/selector
                        page_size_selectors = [
                            'select[name="pageSize"]',
                            'select[aria-label*="page"]',
                            'select[aria-label*="rows"]',
                            'button:has-text("100")',
                            'button:has-text("200")',
                            'a:has-text("Show all")',
                            'button:has-text("All")',
                        ]

                        for selector in page_size_selectors:
                            try:
                                element = await page.query_selector(selector)
                                if element:
                                    logger.info(f"Found page size control: {selector}")
                                    if 'select' in selector:
                                        # Try to select the largest option
                                        options = await page.query_selector_all(f'{selector} option')
                                        if options:
                                            # Get the last option (usually largest)
                                            last_option_value = await options[-1].get_attribute('value')
                                            await page.select_option(selector, last_option_value)
                                            logger.info(f"Set page size to: {last_option_value}")
                                            await page.wait_for_timeout(2000)
                                            break
                                    else:
                                        await element.click()
                                        await page.wait_for_timeout(2000)
                                        break
                            except Exception as e:
                                logger.debug(f"Could not use selector {selector}: {e}")
                                continue

                    except Exception as e:
                        logger.debug(f"Could not modify page size: {e}")

                    # Take a screenshot for debugging (optional)
                    try:
                        await page.screenshot(path='/tmp/umpires_page.png')
                        logger.info("Saved screenshot to /tmp/umpires_page.png")
                    except Exception as e:
                        logger.debug(f"Could not save screenshot: {e}")

                    # Extract umpire data from all pages
                    all_umpires = []
                    page_num = 1

                    while True:
                        logger.info(f"Scraping page {page_num}...")

                        # Extract umpire data from current page
                        page_umpires = await self._parse_umpire_page(page)
                        all_umpires.extend(page_umpires)

                        logger.info(f"Found {len(page_umpires)} umpires on page {page_num} (total so far: {len(all_umpires)})")

                        # Check for next page button
                        next_button_found = False
                        next_selectors = [
                            'button:has-text("Next")',
                            'a:has-text("Next")',
                            'button[aria-label*="next" i]',
                            'a[aria-label*="next" i]',
                            'button.next',
                            'a.next',
                            'li.next a',
                            'li.next button',
                        ]

                        for selector in next_selectors:
                            try:
                                next_button = await page.query_selector(selector)
                                if next_button:
                                    # Check if button is disabled
                                    is_disabled = await next_button.get_attribute('disabled')
                                    aria_disabled = await next_button.get_attribute('aria-disabled')
                                    class_list = await next_button.get_attribute('class') or ''

                                    if is_disabled or aria_disabled == 'true' or 'disabled' in class_list:
                                        logger.info(f"Next button found but disabled - reached last page")
                                        break

                                    logger.info(f"Found next page button: {selector}, clicking...")
                                    await next_button.click()
                                    await page.wait_for_timeout(3000)  # Wait for next page to load
                                    next_button_found = True
                                    page_num += 1
                                    break
                            except Exception as e:
                                logger.debug(f"Could not use next selector {selector}: {e}")
                                continue

                        if not next_button_found:
                            logger.info("No more pages found")
                            break

                    umpires = all_umpires
                    logger.info(f"Successfully scraped {len(umpires)} total umpire records from {page_num} page(s)")

                    # Log the actual text length we're parsing
                    body_text = await page.locator('body').inner_text()
                    logger.info(f"Page text length: {len(body_text)} characters, lines: {len(body_text.split(chr(10)))}")

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Failed to scrape umpire data: {e}")

        return umpires

    async def _parse_umpire_page(self, page: Page) -> List[UmpireMetrics]:
        """Parse umpire data from the loaded page"""
        umpires = []

        try:
            # Wait for dynamic content to render
            await page.wait_for_timeout(2000)

            # Get the body text which contains the rendered data
            body_text = await page.locator('body').inner_text()

            # Parse the text-based table data
            lines = body_text.split('\n')

            # Find where umpire data starts (look for first umpire with tab-separated data)
            data_start_idx = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Look for umpire data row (has tabs and multiple numeric fields)
                if '\t' in stripped and len(stripped.split('\t')) > 10:
                    # Check if first part looks like a name (contains space and letters)
                    first_part = stripped.split('\t')[0]
                    if ' ' in first_part and any(c.isalpha() for c in first_part):
                        data_start_idx = i
                        break

            if data_start_idx == -1:
                logger.warning("Could not find umpire data start marker")
                return umpires

            # Process lines starting from first umpire
            for i in range(data_start_idx, len(lines)):
                line = lines[i].strip()

                # Skip empty lines or pagination
                if not line or line.startswith('1 to') or line.startswith('Page size:') or line.isdigit():
                    continue

                # Parse umpire data rows
                # Format: Name\tG\tPC\tCC\txCC\tCCAx\tAcc\txAcc\tAAx\tminAcc\tmaxAcc\tavgCon\tavgFav
                parts = line.split('\t')

                if len(parts) >= 7:  # Need at least name, G, and Acc
                    try:
                        name = parts[0].strip()

                        # Skip if not a valid name
                        if not name or name == 'Umpire' or len(name) < 3:
                            continue

                        # Column indices: 0=Name, 1=G, 2=PC, 3=CC, 4=xCC, 5=CCAx, 6=Acc, 7=xAcc, 8=AAx, 9=minAcc, 10=maxAcc, 11=avgCon, 12=avgFav
                        games = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 0
                        total_calls = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else 0
                        correct_calls = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip() else 0
                        expected_correct_calls = float(parts[4].strip()) if len(parts) > 4 and parts[4].strip() else 0.0
                        calls_above_expected = float(parts[5].strip()) if len(parts) > 5 and parts[5].strip() else 0.0
                        accuracy = float(parts[6].strip()) if len(parts) > 6 and parts[6].strip() else 0.0
                        expected_accuracy = float(parts[7].strip()) if len(parts) > 7 and parts[7].strip() else 0.0
                        accuracy_above_expected = float(parts[8].strip()) if len(parts) > 8 and parts[8].strip() else 0.0
                        min_accuracy = float(parts[9].strip()) if len(parts) > 9 and parts[9].strip() else 0.0
                        max_accuracy = float(parts[10].strip()) if len(parts) > 10 and parts[10].strip() else 0.0
                        consistency = float(parts[11].strip()) if len(parts) > 11 and parts[11].strip() else 0.0
                        favor_home = float(parts[12].strip()) if len(parts) > 12 and parts[12].strip() else 0.0

                        incorrect_calls = total_calls - correct_calls if total_calls > 0 else 0

                        # Calculate calls per game
                        calls_per_game = total_calls / games if games > 0 else 0.0

                        umpire = UmpireMetrics(
                            name=name,
                            games_umped=games,
                            accuracy_pct=accuracy,
                            consistency_pct=consistency,
                            favor_home=favor_home,
                            expected_accuracy=expected_accuracy,
                            expected_consistency=0.0,  # Not directly available, could derive from other metrics
                            correct_calls=correct_calls,
                            incorrect_calls=incorrect_calls,
                            total_calls=total_calls,
                            strike_pct=0.0,  # Not in this dataset
                            ball_pct=0.0,  # Not in this dataset
                            k_pct_above_avg=0.0,  # Not in this dataset
                            bb_pct_above_avg=0.0,  # Not in this dataset
                            home_plate_calls_per_game=calls_per_game,
                            last_updated=datetime.now()
                        )
                        umpires.append(umpire)

                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing line '{line}': {e}")
                        continue

            logger.info(f"Parsed {len(umpires)} umpires from page")

        except Exception as e:
            logger.error(f"Error parsing umpire page: {e}")

        return umpires

    async def _extract_from_scripts(self, page: Page) -> List[UmpireMetrics]:
        """Try to extract umpire data from embedded JSON in script tags"""
        umpires = []

        try:
            # Look for JSON data in script tags
            scripts = await page.query_selector_all('script')

            for script in scripts:
                content = await script.inner_text()

                # Look for JSON patterns that might contain umpire data
                # This regex looks for arrays of objects with umpire-like properties
                json_pattern = r'\{[^}]*"name"[^}]*"accuracy"[^}]*\}'
                matches = re.findall(json_pattern, content, re.IGNORECASE)

                if matches:
                    logger.info(f"Found {len(matches)} potential umpire data objects in scripts")
                    # This would need proper JSON parsing - simplified for now
                    break

        except Exception as e:
            logger.debug(f"Error extracting from scripts: {e}")

        return umpires

    def _parse_umpire_card(self, text: str) -> Optional[UmpireMetrics]:
        """Parse umpire data from card text"""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 2:
                name = lines[0]
                # Look for percentage patterns
                accuracy_match = re.search(r'(\d+\.?\d*)%', text)
                accuracy = float(accuracy_match.group(1)) if accuracy_match else 0.0

                # Look for games played
                games_match = re.search(r'(\d+)\s*games?', text, re.IGNORECASE)
                games = int(games_match.group(1)) if games_match else 0

                return UmpireMetrics(
                    name=name,
                    games_umped=games,
                    accuracy_pct=accuracy,
                    last_updated=datetime.now()
                )
        except Exception as e:
            logger.debug(f"Error parsing card text: {e}")

        return None

    async def _extract_number(self, element) -> int:
        """Extract integer from element"""
        try:
            text = await element.inner_text()
            # Remove commas and extract first number
            match = re.search(r'(\d+)', text.replace(',', ''))
            return int(match.group(1)) if match else 0
        except:
            return 0

    async def _extract_float(self, element) -> float:
        """Extract float from element (handles percentages)"""
        try:
            text = await element.inner_text()
            # Remove % sign and extract number
            match = re.search(r'(\d+\.?\d*)', text.replace('%', '').replace(',', ''))
            return float(match.group(1)) if match else 0.0
        except:
            return 0.0


async def update_umpire_scorecards(db_pool: asyncpg.Pool, season: Optional[int] = None):
    """
    Main function to update umpire data in database
    Scrapes umpscorecards.com using Playwright for accurate performance metrics

    Args:
        db_pool: Database connection pool
        season: Optional season year. If None, defaults to current season (2025)
    """

    scraper = UmpireScraper()

    # Default to current season if not specified
    if season is None:
        season = 2025
        logger.info(f"No season specified, defaulting to {season}")

    try:
        logger.info(f"Starting umpire scorecard data scrape for season {season}")

        # Scrape umpire data
        umpires = await scraper.scrape_umpire_data(season)

        if not umpires:
            logger.warning("No umpire data scraped - check if page structure has changed")
            return

        success_count = 0
        season_stats_count = 0

        for umpire in umpires:
            try:
                # Create or update umpire record (base/aggregate table)
                umpire_id = f"ump_{umpire.name.lower().replace(' ', '_').replace('.', '')}"

                await db_pool.execute("""
                    INSERT INTO umpires (
                        umpire_id, name, games_umped, accuracy_pct, consistency_pct,
                        favor_home, expected_accuracy, expected_consistency,
                        correct_calls, incorrect_calls, total_calls,
                        strike_pct, ball_pct, k_pct_above_avg, bb_pct_above_avg,
                        home_plate_calls_per_game, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW())
                    ON CONFLICT (umpire_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        games_umped = EXCLUDED.games_umped,
                        accuracy_pct = EXCLUDED.accuracy_pct,
                        consistency_pct = EXCLUDED.consistency_pct,
                        favor_home = EXCLUDED.favor_home,
                        expected_accuracy = EXCLUDED.expected_accuracy,
                        expected_consistency = EXCLUDED.expected_consistency,
                        correct_calls = EXCLUDED.correct_calls,
                        incorrect_calls = EXCLUDED.incorrect_calls,
                        total_calls = EXCLUDED.total_calls,
                        strike_pct = EXCLUDED.strike_pct,
                        ball_pct = EXCLUDED.ball_pct,
                        k_pct_above_avg = EXCLUDED.k_pct_above_avg,
                        bb_pct_above_avg = EXCLUDED.bb_pct_above_avg,
                        home_plate_calls_per_game = EXCLUDED.home_plate_calls_per_game,
                        updated_at = NOW()
                """, umpire_id, umpire.name, umpire.games_umped,
                    umpire.accuracy_pct, umpire.consistency_pct, umpire.favor_home,
                    umpire.expected_accuracy, umpire.expected_consistency,
                    umpire.correct_calls, umpire.incorrect_calls, umpire.total_calls,
                    umpire.strike_pct, umpire.ball_pct, umpire.k_pct_above_avg,
                    umpire.bb_pct_above_avg, umpire.home_plate_calls_per_game)

                success_count += 1

                # Also insert/update season-specific stats
                # Get the umpire UUID from the base table
                umpire_uuid = await db_pool.fetchval(
                    "SELECT id FROM umpires WHERE umpire_id = $1",
                    umpire_id
                )

                if umpire_uuid:
                    await db_pool.execute("""
                        INSERT INTO umpire_season_stats (
                            umpire_id, season, games_umped, accuracy_pct, consistency_pct,
                            favor_home, expected_accuracy, expected_consistency,
                            correct_calls, incorrect_calls, total_calls,
                            strike_pct, ball_pct, k_pct_above_avg, bb_pct_above_avg,
                            home_plate_calls_per_game
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                        ON CONFLICT (umpire_id, season) DO UPDATE
                        SET games_umped = EXCLUDED.games_umped,
                            accuracy_pct = EXCLUDED.accuracy_pct,
                            consistency_pct = EXCLUDED.consistency_pct,
                            favor_home = EXCLUDED.favor_home,
                            expected_accuracy = EXCLUDED.expected_accuracy,
                            expected_consistency = EXCLUDED.expected_consistency,
                            correct_calls = EXCLUDED.correct_calls,
                            incorrect_calls = EXCLUDED.incorrect_calls,
                            total_calls = EXCLUDED.total_calls,
                            strike_pct = EXCLUDED.strike_pct,
                            ball_pct = EXCLUDED.ball_pct,
                            k_pct_above_avg = EXCLUDED.k_pct_above_avg,
                            bb_pct_above_avg = EXCLUDED.bb_pct_above_avg,
                            home_plate_calls_per_game = EXCLUDED.home_plate_calls_per_game,
                            updated_at = NOW()
                    """, umpire_uuid, season, umpire.games_umped,
                        umpire.accuracy_pct, umpire.consistency_pct, umpire.favor_home,
                        umpire.expected_accuracy, umpire.expected_consistency,
                        umpire.correct_calls, umpire.incorrect_calls, umpire.total_calls,
                        umpire.strike_pct, umpire.ball_pct, umpire.k_pct_above_avg,
                        umpire.bb_pct_above_avg, umpire.home_plate_calls_per_game)

                    season_stats_count += 1

            except Exception as e:
                logger.error(f"Error updating umpire {umpire.name}: {e}")

        logger.info(f"Successfully updated {success_count} umpire scorecards and {season_stats_count} season stats for {season} from umpscorecards.com")

    except Exception as e:
        logger.error(f"Failed to update umpire scorecards: {e}")
        # Non-critical - game feeds will also populate umpire data


# Backward compatibility
async def update_umpire_scorecards_legacy(db_pool: asyncpg.Pool):
    """Legacy function for backward compatibility"""
    await update_umpire_scorecards(db_pool)
