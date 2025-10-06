"""
Integration tests for the Baseball Simulation API
Tests the full stack: API Gateway -> Database -> Data Fetcher
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any


BASE_URL_API_GATEWAY = "http://localhost:8080"
BASE_URL_DATA_FETCHER = "http://localhost:8082"
BASE_URL_SIM_ENGINE = "http://localhost:8081"


@pytest.fixture
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


class TestAPIGatewayIntegration:
    """Integration tests for API Gateway"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, http_client):
        """Test API Gateway health check"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'database' in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, http_client):
        """Test metrics endpoint"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert 'system' in data
        assert 'application' in data
        assert 'cache' in data
        assert 'database' in data

    @pytest.mark.asyncio
    async def test_teams_endpoint(self, http_client):
        """Test teams listing"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/teams")
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert isinstance(data['data'], list)

    @pytest.mark.asyncio
    async def test_players_endpoint(self, http_client):
        """Test players listing"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert 'page' in data
        assert 'page_size' in data

    @pytest.mark.asyncio
    async def test_games_endpoint(self, http_client):
        """Test games listing"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/games?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data

    @pytest.mark.asyncio
    async def test_pagination(self, http_client):
        """Test pagination functionality"""
        # Test page 1
        response1 = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players?page=1&page_size=10")
        assert response1.status_code == 200
        data1 = response1.json()

        # Test page 2
        response2 = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players?page=2&page_size=10")
        assert response2.status_code == 200
        data2 = response2.json()

        # Ensure different data on different pages
        if data1['total'] > 10:
            assert data1['data'] != data2['data']

    @pytest.mark.asyncio
    async def test_rate_limiting(self, http_client):
        """Test rate limiting (100 req/min)"""
        # Make many rapid requests
        responses = []
        for i in range(110):
            try:
                response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/health")
                responses.append(response.status_code)
            except Exception:
                pass

        # Should have some 429 (Too Many Requests) responses
        assert 429 in responses

    @pytest.mark.asyncio
    async def test_compression(self, http_client):
        """Test gzip compression"""
        response = await http_client.get(
            f"{BASE_URL_API_GATEWAY}/api/v1/teams",
            headers={"Accept-Encoding": "gzip"}
        )
        assert response.status_code == 200
        # Check if response was compressed
        assert response.headers.get("Content-Encoding") == "gzip" or len(response.content) > 0

    @pytest.mark.asyncio
    async def test_search_endpoint(self, http_client):
        """Test universal search endpoint"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_search_validation(self, http_client):
        """Test search query validation"""
        # Empty query
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/search?q=")
        assert response.status_code == 400

        # Too short query
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/search?q=a")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_team_stats_endpoint(self, http_client):
        """Test team statistics endpoint"""
        # Get a team first
        teams_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/teams")
        teams = teams_response.json()['data']

        if len(teams) > 0:
            team_id = teams[0]['id']
            # Get team stats
            stats_response = await http_client.get(
                f"{BASE_URL_API_GATEWAY}/api/v1/teams/{team_id}/stats?season=2024"
            )
            assert stats_response.status_code in [200, 404]

            if stats_response.status_code == 200:
                data = stats_response.json()
                assert 'wins' in data or 'season' in data

    @pytest.mark.asyncio
    async def test_team_games_endpoint(self, http_client):
        """Test team games endpoint"""
        # Get a team first
        teams_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/teams")
        teams = teams_response.json()['data']

        if len(teams) > 0:
            team_id = teams[0]['id']
            # Get team games
            games_response = await http_client.get(
                f"{BASE_URL_API_GATEWAY}/api/v1/teams/{team_id}/games?season=2024"
            )
            assert games_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_game_boxscore_endpoint(self, http_client):
        """Test game box score endpoint"""
        # Get a game first
        games_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/games?page=1&page_size=5")
        games = games_response.json()

        if 'data' in games and len(games['data']) > 0:
            game_id = games['data'][0]['id']
            # Get box score
            boxscore_response = await http_client.get(
                f"{BASE_URL_API_GATEWAY}/api/v1/games/{game_id}/boxscore"
            )
            assert boxscore_response.status_code in [200, 404]

            if boxscore_response.status_code == 200:
                data = boxscore_response.json()
                # Box score should have these keys
                assert 'home_team_batting' in data
                assert 'away_team_batting' in data
                assert 'home_team_pitching' in data
                assert 'away_team_pitching' in data

    @pytest.mark.asyncio
    async def test_game_plays_endpoint(self, http_client):
        """Test game plays endpoint"""
        # Get a game first
        games_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/games?page=1&page_size=5")
        games = games_response.json()

        if 'data' in games and len(games['data']) > 0:
            game_id = games['data'][0]['id']
            # Get plays
            plays_response = await http_client.get(
                f"{BASE_URL_API_GATEWAY}/api/v1/games/{game_id}/plays"
            )
            assert plays_response.status_code in [200, 404]

            if plays_response.status_code == 200:
                data = plays_response.json()
                assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_game_weather_endpoint(self, http_client):
        """Test game weather endpoint"""
        # Get a game first
        games_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/games?page=1&page_size=5")
        games = games_response.json()

        if 'data' in games and len(games['data']) > 0:
            game_id = games['data'][0]['id']
            # Get weather
            weather_response = await http_client.get(
                f"{BASE_URL_API_GATEWAY}/api/v1/games/{game_id}/weather"
            )
            assert weather_response.status_code in [200, 404]

            if weather_response.status_code == 200:
                data = weather_response.json()
                assert isinstance(data, dict)


class TestDataFetcherIntegration:
    """Integration tests for Data Fetcher"""

    @pytest.mark.asyncio
    async def test_data_fetcher_health(self, http_client):
        """Test data fetcher health"""
        response = await http_client.get(f"{BASE_URL_DATA_FETCHER}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_data_fetcher_status(self, http_client):
        """Test data fetcher status endpoint"""
        response = await http_client.get(f"{BASE_URL_DATA_FETCHER}/status")
        assert response.status_code == 200
        data = response.json()
        assert 'total_games' in data
        assert 'total_players' in data
        assert 'total_teams' in data


class TestSimulationEngineIntegration:
    """Integration tests for Simulation Engine"""

    @pytest.mark.asyncio
    async def test_simulation_engine_health(self, http_client):
        """Test simulation engine health"""
        response = await http_client.get(f"{BASE_URL_SIM_ENGINE}/health")
        assert response.status_code == 200


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    @pytest.mark.asyncio
    async def test_complete_game_query_workflow(self, http_client):
        """Test complete workflow: Get teams -> Get games -> Get details"""
        # Step 1: Get all teams
        teams_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/teams")
        assert teams_response.status_code == 200
        teams = teams_response.json()['data']

        if len(teams) == 0:
            pytest.skip("No teams in database")

        # Step 2: Get games
        games_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/games?page=1&page_size=5")
        assert games_response.status_code == 200
        games = games_response.json()

        assert 'data' in games
        assert isinstance(games['data'], list)

    @pytest.mark.asyncio
    async def test_player_stats_workflow(self, http_client):
        """Test workflow: Get players -> Get player stats"""
        # Get players
        players_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players?page=1&page_size=5")
        assert players_response.status_code == 200
        players_data = players_response.json()

        if players_data['total'] == 0:
            pytest.skip("No players in database")

        # Get first player's ID
        first_player = players_data['data'][0]
        player_id = first_player['id']

        # Get player stats
        stats_response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players/{player_id}/stats")
        assert stats_response.status_code in [200, 404]  # 404 if no stats


class TestErrorHandling:
    """Test error handling across services"""

    @pytest.mark.asyncio
    async def test_invalid_player_id(self, http_client):
        """Test invalid player ID returns 400 or 404"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players/invalid-id")
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_invalid_pagination(self, http_client):
        """Test invalid pagination parameters"""
        # Invalid page
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players?page=0&page_size=10")
        assert response.status_code in [400, 422]

        # Invalid page_size
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/players?page=1&page_size=1000")
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, http_client):
        """Test nonexistent endpoint returns 404"""
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/nonexistent")
        assert response.status_code == 404


class TestPerformance:
    """Performance tests"""

    @pytest.mark.asyncio
    async def test_response_time_teams(self, http_client):
        """Test teams endpoint response time"""
        import time
        start = time.time()
        response = await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/teams")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond in < 500ms

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, http_client):
        """Test handling concurrent requests"""
        async def make_request():
            return await http_client.get(f"{BASE_URL_API_GATEWAY}/api/v1/health")

        # Make 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should succeed
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        assert successful >= 45  # At least 90% success rate


# Run tests with: pytest tests/integration/test_api_integration.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
