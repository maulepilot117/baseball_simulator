"""
Test script for position-specific endpoints
Tests catcher and outfielder metrics and leaderboards endpoints
"""
import asyncio
import pytest
import httpx
from typing import Dict, Any


class TestPositionEndpoints:
    """Test class for position-specific API endpoints"""

    def __init__(self, base_url: str = "http://localhost:8082"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def test_catcher_metrics_endpoint(self):
        """Test catcher metrics endpoint"""
        print("\n=== Testing Catcher Metrics Endpoint ===")

        # Test valid catcher
        response = await self.client.get("/player/abc123/catcher-metrics/2023")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Catcher metrics retrieved: {data['player_name']}")
            print(f"  Framing runs: {data['metrics']['framing_runs']}")
            print(f"  Blocking runs: {data['metrics']['blocking_runs']}")
            print(f"  Total catcher runs: {data['metrics']['total_catcher_runs']}")
        elif response.status_code == 404:
            print("⚠ No catcher data found (expected if database is empty)")
        else:
            print(f"✗ Unexpected error: {response.status_code} - {response.text}")

    async def test_outfielder_metrics_endpoint(self):
        """Test outfielder metrics endpoint"""
        print("\n=== Testing Outfielder Metrics Endpoint ===")

        # Test valid outfielder
        response = await self.client.get("/player/def456/outfielder-metrics/2023?position=CF")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Outfielder metrics retrieved: {data['player_name']}")
            print(f"  Range runs: {data['metrics']['range_runs']}")
            print(f"  Arm runs: {data['metrics']['arm_runs']}")
            print(f"  Total outfielder runs: {data['metrics']['total_outfielder_runs']}")
        elif response.status_code == 404:
            print("⚠ No outfielder data found (expected if database is empty)")
        else:
            print(f"✗ Unexpected error: {response.status_code} - {response.text}")

    async def test_catcher_leaderboards_endpoint(self):
        """Test catcher leaderboards endpoint"""
        print("\n=== Testing Catcher Leaderboards Endpoint ===")

        response = await self.client.get("/catcher-leaderboards/2023?stat_name=FRAMING_RUNS&limit=5")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Catcher leaderboard retrieved: {data['count']} players")
            if data['count'] > 0:
                top_catcher = data['leaderboard'][0]
                print(f"  #1: {top_catcher['name']} - {top_catcher['framing_runs']} framing runs")
        elif response.status_code == 404:
            print("⚠ No catcher leaderboard data found (expected if database is empty)")
        else:
            print(f"✗ Unexpected error: {response.status_code} - {response.text}")

    async def test_outfielder_leaderboards_endpoint(self):
        """Test outfielder leaderboards endpoint"""
        print("\n=== Testing Outfielder Leaderboards Endpoint ===")

        response = await self.client.get("/outfielder-leaderboards/2023?position=CF&stat_name=RANGE_RUNS&limit=5")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Outfielder leaderboard retrieved: {data['count']} players")
            if data['count'] > 0:
                top_outfielder = data['leaderboard'][0]
                print(f"  #1: {top_outfielder['name']} - {top_outfielder['range_runs']} range runs")
        elif response.status_code == 404:
            print("⚠ No outfielder leaderboard data found (expected if database is empty)")
        else:
            print(f"✗ Unexpected error: {response.status_code} - {response.text}")

    async def test_error_cases(self):
        """Test error cases"""
        print("\n=== Testing Error Cases ===")

        # Test non-existent player
        response = await self.client.get("/player/nonexistent/catcher-metrics/2023")
        if response.status_code == 404:
            print("✓ Correctly handled non-existent player")
        else:
            print(f"✗ Wrong error code for non-existent player: {response.status_code}")

        # Test wrong position for player
        response = await self.client.get("/player/xyz789/outfielder-metrics/2023?position=CF")
        if response.status_code == 400:
            print("✓ Correctly rejected wrong position request")
        elif response.status_code == 404:
            print("⚠ Player not found (expected if no test data)")
        else:
            print(f"? Unexpected response for wrong position: {response.status_code}")

    async def test_service_health(self):
        """Test basic service health"""
        print("\n=== Testing Service Health ===")

        response = await self.client.get("/health")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Service is healthy: {data}")
        else:
            print(f"✗ Service health check failed: {response.status_code}")
            return False

        return True

    async def run_all_tests(self):
        """Run all endpoint tests"""
        print("🧪 Starting Position-Specific Endpoints Tests")
        print("=" * 50)

        # Test service health first
        if not await self.test_service_health():
            print("❌ Service is not healthy, stopping tests")
            return

        # Run all endpoint tests
        await self.test_catcher_metrics_endpoint()
        await self.test_outfielder_metrics_endpoint()
        await self.test_catcher_leaderboards_endpoint()
        await self.test_outfielder_leaderboards_endpoint()
        await self.test_error_cases()

        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("\nNote: 404 errors are expected if no data exists in the database.")
        print("Run data fetching first to populate test data.")


async def main():
    """Main test runner"""
    async with TestPositionEndpoints() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
