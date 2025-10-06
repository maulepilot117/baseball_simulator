"""
Game Details Fetcher
Fetches box scores, play-by-play, and weather data for games
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
import httpx
import asyncpg

logger = logging.getLogger(__name__)

# Stadium dome/roof information
STADIUM_ROOF_INFO = {
    "Angel Stadium": {"roof_type": "open"},
    "Chase Field": {"roof_type": "retractable"},
    "Citi Field": {"roof_type": "open"},
    "Citizens Bank Park": {"roof_type": "open"},
    "Comerica Park": {"roof_type": "open"},
    "Coors Field": {"roof_type": "open", "elevation": 5200},
    "Dodger Stadium": {"roof_type": "open"},
    "Fenway Park": {"roof_type": "open"},
    "Globe Life Field": {"roof_type": "retractable"},
    "Great American Ball Park": {"roof_type": "open"},
    "Guaranteed Rate Field": {"roof_type": "open"},
    "Kauffman Stadium": {"roof_type": "open"},
    "loanDepot park": {"roof_type": "retractable"},
    "Minute Maid Park": {"roof_type": "retractable"},
    "Nationals Park": {"roof_type": "open"},
    "Oakland Coliseum": {"roof_type": "open"},
    "Oracle Park": {"roof_type": "open"},
    "Oriole Park at Camden Yards": {"roof_type": "open"},
    "PNC Park": {"roof_type": "open"},
    "Petco Park": {"roof_type": "open"},
    "Progressive Field": {"roof_type": "open"},
    "Rogers Centre": {"roof_type": "retractable"},
    "T-Mobile Park": {"roof_type": "retractable"},
    "Target Field": {"roof_type": "open"},
    "Tropicana Field": {"roof_type": "dome"},
    "Truist Park": {"roof_type": "open"},
    "Wrigley Field": {"roof_type": "open"},
    "Yankee Stadium": {"roof_type": "open"},
    "American Family Field": {"roof_type": "retractable"},
    "Busch Stadium": {"roof_type": "open"},
}


class GameDetailsFetcher:
    """Fetches detailed game information including box scores and play-by-play"""

    def __init__(self, db_pool: asyncpg.Pool, client: httpx.AsyncClient):
        self.db_pool = db_pool
        self.client = client
        self.base_url = "https://statsapi.mlb.com/api/v1.1"

    async def fetch_game_details(self, game_id: str, game_uuid: UUID) -> bool:
        """
        Fetch complete game details including box score, play-by-play, and weather

        Args:
            game_id: MLB game ID (e.g., "662074")
            game_uuid: Internal database UUID for the game

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Fetching details for game {game_id}")

            # Fetch game data with box score and play-by-play
            url = f"{self.base_url}/game/{game_id}/feed/live"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Extract components
            game_data = data.get("gameData", {})
            live_data = data.get("liveData", {})

            # Update weather data
            await self._update_weather(game_uuid, game_data)

            # Save box scores
            await self._save_box_scores(game_uuid, live_data.get("boxscore", {}))

            # Save play-by-play
            await self._save_plays(game_uuid, live_data.get("plays", {}))

            logger.info(f"Successfully fetched details for game {game_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to fetch details for game {game_id}: {e}")
            return False

    async def _update_weather(self, game_uuid: UUID, game_data: Dict):
        """Update weather information for a game"""
        try:
            weather = game_data.get("weather", {})
            venue = game_data.get("venue", {})
            venue_name = venue.get("name", "")

            # Get roof/dome info
            roof_info = STADIUM_ROOF_INFO.get(venue_name, {"roof_type": "open"})
            is_dome = roof_info["roof_type"] == "dome"
            is_retractable = roof_info["roof_type"] == "retractable"

            # For domes or retractable roofs, normalize weather
            if is_dome:
                weather_data = {
                    "temp": 72,
                    "condition": "Dome",
                    "wind": "0 mph",
                    "humidity": None,
                    "is_dome": True,
                    "roof_closed": True
                }
            elif is_retractable:
                # Check if roof is closed
                roof_closed = weather.get("temp", "") == "Roof Closed" or "roof" in weather.get("condition", "").lower()
                if roof_closed:
                    weather_data = {
                        "temp": 72,
                        "condition": "Roof Closed",
                        "wind": "0 mph",
                        "humidity": None,
                        "is_dome": False,
                        "roof_closed": True
                    }
                else:
                    weather_data = {
                        "temp": weather.get("temp"),
                        "condition": weather.get("condition"),
                        "wind": weather.get("wind"),
                        "humidity": None,
                        "is_dome": False,
                        "roof_closed": False
                    }
            else:
                # Open stadium - use actual weather
                weather_data = {
                    "temp": weather.get("temp"),
                    "condition": weather.get("condition"),
                    "wind": weather.get("wind"),
                    "humidity": None,
                    "is_dome": False,
                    "roof_closed": False
                }

            await self.db_pool.execute(
                """
                UPDATE games
                SET weather_data = $1::jsonb
                WHERE id = $2
                """,
                json.dumps(weather_data),
                game_uuid
            )

        except Exception as e:
            logger.error(f"Failed to update weather for game {game_uuid}: {e}")

    async def _save_box_scores(self, game_uuid: UUID, boxscore: Dict):
        """Save batting and pitching box scores"""
        try:
            teams = boxscore.get("teams", {})
            logger.debug(f"Processing box scores for game {game_uuid}")

            for team_type in ["away", "home"]:
                team_data = teams.get(team_type, {})
                players_data = team_data.get("players", {})
                team_info = team_data.get("team", {})
                team_id = team_info.get("id")

                logger.debug(f"Processing {team_type} team with ID {team_id}, found {len(players_data)} players")

                # Get internal team UUID
                team_uuid = await self._get_team_uuid(team_id)
                if not team_uuid:
                    logger.warning(f"Team UUID not found for team_id {team_id}")
                    continue

                batting_saved = 0
                pitching_saved = 0
                for player_key, player_data in players_data.items():
                    person = player_data.get("person", {})
                    player_id = person.get("id")

                    # Get internal player UUID
                    player_uuid = await self._get_player_uuid(player_id)
                    if not player_uuid:
                        logger.debug(f"Player UUID not found for player_id {player_id}")
                        continue

                    # Save batting stats if present
                    batting = player_data.get("stats", {}).get("batting", {})
                    if batting:
                        await self._save_batting_box_score(game_uuid, player_uuid, team_uuid, batting, player_data)
                        batting_saved += 1

                    # Save pitching stats if present
                    pitching = player_data.get("stats", {}).get("pitching", {})
                    if pitching:
                        await self._save_pitching_box_score(game_uuid, player_uuid, team_uuid, pitching)
                        pitching_saved += 1

                logger.info(f"Saved {batting_saved} batting and {pitching_saved} pitching records for {team_type} team")

        except Exception as e:
            logger.error(f"Failed to save box scores for game {game_uuid}: {e}")

    async def _save_batting_box_score(self, game_uuid: UUID, player_uuid: UUID, team_uuid: UUID,
                                       batting: Dict, player_data: Dict):
        """Save individual batting box score"""
        try:
            # Convert batting order from string to int (API returns '100', '200', etc. for 1st, 2nd, etc.)
            batting_order_str = player_data.get("battingOrder")
            batting_order = int(batting_order_str) // 100 if batting_order_str else None

            await self.db_pool.execute(
                """
                INSERT INTO game_box_score_batting
                (game_id, player_id, team_id, batting_order, position, at_bats, runs, hits, rbis,
                 walks, strikeouts, doubles, triples, home_runs, stolen_bases, caught_stealing, left_on_base)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (game_id, player_id) DO UPDATE SET
                    at_bats = EXCLUDED.at_bats,
                    runs = EXCLUDED.runs,
                    hits = EXCLUDED.hits,
                    rbis = EXCLUDED.rbis,
                    walks = EXCLUDED.walks,
                    strikeouts = EXCLUDED.strikeouts,
                    doubles = EXCLUDED.doubles,
                    triples = EXCLUDED.triples,
                    home_runs = EXCLUDED.home_runs,
                    stolen_bases = EXCLUDED.stolen_bases,
                    caught_stealing = EXCLUDED.caught_stealing,
                    left_on_base = EXCLUDED.left_on_base
                """,
                game_uuid, player_uuid, team_uuid,
                batting_order,
                player_data.get("position", {}).get("abbreviation"),
                batting.get("atBats", 0),
                batting.get("runs", 0),
                batting.get("hits", 0),
                batting.get("rbi", 0),
                batting.get("baseOnBalls", 0),
                batting.get("strikeOuts", 0),
                batting.get("doubles", 0),
                batting.get("triples", 0),
                batting.get("homeRuns", 0),
                batting.get("stolenBases", 0),
                batting.get("caughtStealing", 0),
                batting.get("leftOnBase", 0)
            )
        except Exception as e:
            logger.error(f"Failed to save batting box score: {e}")

    async def _save_pitching_box_score(self, game_uuid: UUID, player_uuid: UUID, team_uuid: UUID, pitching: Dict):
        """Save individual pitching box score"""
        try:
            await self.db_pool.execute(
                """
                INSERT INTO game_box_score_pitching
                (game_id, player_id, team_id, innings_pitched, hits_allowed, runs_allowed, earned_runs,
                 walks_allowed, strikeouts, home_runs_allowed, pitches_thrown, strikes, win, loss, save, hold, blown_save)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (game_id, player_id) DO UPDATE SET
                    innings_pitched = EXCLUDED.innings_pitched,
                    hits_allowed = EXCLUDED.hits_allowed,
                    runs_allowed = EXCLUDED.runs_allowed,
                    earned_runs = EXCLUDED.earned_runs,
                    walks_allowed = EXCLUDED.walks_allowed,
                    strikeouts = EXCLUDED.strikeouts,
                    home_runs_allowed = EXCLUDED.home_runs_allowed,
                    pitches_thrown = EXCLUDED.pitches_thrown,
                    strikes = EXCLUDED.strikes,
                    win = EXCLUDED.win,
                    loss = EXCLUDED.loss,
                    save = EXCLUDED.save,
                    hold = EXCLUDED.hold,
                    blown_save = EXCLUDED.blown_save
                """,
                game_uuid, player_uuid, team_uuid,
                float(pitching.get("inningsPitched", "0.0")),
                pitching.get("hits", 0),
                pitching.get("runs", 0),
                pitching.get("earnedRuns", 0),
                pitching.get("baseOnBalls", 0),
                pitching.get("strikeOuts", 0),
                pitching.get("homeRuns", 0),
                pitching.get("numberOfPitches", 0),
                pitching.get("strikes", 0),
                pitching.get("wins", 0) > 0,
                pitching.get("losses", 0) > 0,
                pitching.get("saves", 0) > 0,
                pitching.get("holds", 0) > 0,
                pitching.get("blownSaves", 0) > 0
            )
        except Exception as e:
            logger.error(f"Failed to save pitching box score: {e}")

    async def _save_plays(self, game_uuid: UUID, plays_data: Dict):
        """Save play-by-play data"""
        try:
            all_plays = plays_data.get("allPlays", [])

            for play in all_plays:
                about = play.get("about", {})
                result = play.get("result", {})
                matchup = play.get("matchup", {})

                # Get player UUIDs
                batter_id = matchup.get("batter", {}).get("id")
                pitcher_id = matchup.get("pitcher", {}).get("id")

                batter_uuid = await self._get_player_uuid(batter_id) if batter_id else None
                pitcher_uuid = await self._get_player_uuid(pitcher_id) if pitcher_id else None

                # Get base runner information
                runners_on = {}
                runners_after = {}
                for runner in play.get("runners", []):
                    start_base = runner.get("movement", {}).get("start")
                    end_base = runner.get("movement", {}).get("end")
                    if start_base:
                        runners_on[start_base] = runner.get("details", {}).get("runner", {}).get("id")
                    if end_base:
                        runners_after[end_base] = runner.get("details", {}).get("runner", {}).get("id")

                await self.db_pool.execute(
                    """
                    INSERT INTO game_plays
                    (game_id, play_id, inning, inning_half, outs, balls, strikes, batter_id, pitcher_id,
                     event_type, description, rbi, runs_scored, runners_on, runners_after, home_score, away_score)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb, $15::jsonb, $16, $17)
                    ON CONFLICT (game_id, play_id) DO NOTHING
                    """,
                    game_uuid,
                    str(play.get("atBatIndex", "")),
                    about.get("inning", 0),
                    about.get("halfInning", "top"),
                    about.get("outs", 0),
                    matchup.get("postOnFirst", {}).get("balls", 0) if matchup.get("postOnFirst") else None,
                    matchup.get("postOnFirst", {}).get("strikes", 0) if matchup.get("postOnFirst") else None,
                    batter_uuid,
                    pitcher_uuid,
                    result.get("event"),
                    result.get("description"),
                    result.get("rbi", 0),
                    len([r for r in play.get("runners", []) if r.get("movement", {}).get("end") == "score"]),
                    json.dumps(runners_on),
                    json.dumps(runners_after),
                    about.get("homeScore", 0),
                    about.get("awayScore", 0)
                )

        except Exception as e:
            logger.error(f"Failed to save plays for game {game_uuid}: {e}")

    async def _get_team_uuid(self, mlb_team_id: int) -> Optional[UUID]:
        """Get internal team UUID from MLB team ID"""
        try:
            # First fetch the team from MLB API to get abbreviation
            url = f"https://statsapi.mlb.com/api/v1/teams/{mlb_team_id}"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            team = data.get("teams", [{}])[0]
            team_abbrev = team.get("abbreviation", "").lower()

            if not team_abbrev:
                logger.warning(f"No abbreviation found for MLB team ID {mlb_team_id}")
                return None

            # Look up UUID from database using abbreviation
            row = await self.db_pool.fetchrow(
                "SELECT id FROM teams WHERE team_id = $1",
                team_abbrev
            )
            return row["id"] if row else None
        except Exception as e:
            logger.error(f"Error getting team UUID for MLB team ID {mlb_team_id}: {e}")
            return None

    async def _get_player_uuid(self, mlb_player_id: int) -> Optional[UUID]:
        """Get internal player UUID from MLB player ID"""
        try:
            # Player IDs in database have "mlb_" prefix
            player_id_str = f"mlb_{mlb_player_id}"
            row = await self.db_pool.fetchrow(
                "SELECT id FROM players WHERE player_id = $1",
                player_id_str
            )
            return row["id"] if row else None
        except Exception as e:
            logger.debug(f"Error getting player UUID for MLB player ID {mlb_player_id}: {e}")
            return None


async def fetch_all_game_details(db_pool: asyncpg.Pool, limit: Optional[int] = None):
    """
    Fetch details for all games that don't have box scores yet

    Args:
        db_pool: Database connection pool
        limit: Optional limit on number of games to process
    """
    logger.info("Starting to fetch game details...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        fetcher = GameDetailsFetcher(db_pool, client)

        # Get games that need details
        query = """
            SELECT g.id, g.game_id
            FROM games g
            LEFT JOIN game_box_score_batting b ON g.id = b.game_id
            WHERE g.status = 'Final'
            AND b.id IS NULL
            ORDER BY g.game_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        rows = await db_pool.fetch(query)
        logger.info(f"Found {len(rows)} games needing details")

        success_count = 0
        for row in rows:
            if await fetcher.fetch_game_details(row["game_id"], row["id"]):
                success_count += 1
            await asyncio.sleep(0.5)  # Rate limiting

        logger.info(f"Successfully fetched details for {success_count}/{len(rows)} games")
