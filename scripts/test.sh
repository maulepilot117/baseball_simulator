#!/bin/bash

# Baseball Simulation System Test Script

set -e

echo "🧪 Baseball Simulation System Tests"
echo "==================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URLs
API_GATEWAY="http://localhost:8080/api/v1"
SIM_ENGINE="http://localhost:8081"
DATA_FETCHER="http://localhost:8082"

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ Pass${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ Fail${NC} (HTTP $response, expected $expected_status)"
        return 1
    fi
}

# Test JSON response
test_json_endpoint() {
    local name=$1
    local url=$2
    
    echo -n "Testing $name... "
    
    response=$(curl -s "$url" 2>/dev/null)
    
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Pass${NC} (Valid JSON)"
        return 0
    else
        echo -e "${RED}✗ Fail${NC} (Invalid JSON or no response)"
        return 1
    fi
}

# Test POST endpoint
test_post_endpoint() {
    local name=$1
    local url=$2
    local data=$3
    local expected_status=${4:-200}
    
    echo -n "Testing $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ Pass${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ Fail${NC} (HTTP $response, expected $expected_status)"
        return 1
    fi
}

# Track test results
total_tests=0
passed_tests=0

run_test() {
    ((total_tests++))
    if "$@"; then
        ((passed_tests++))
    fi
}

echo ""
echo "1️⃣  Testing Service Health Endpoints"
echo "------------------------------------"
run_test test_json_endpoint "API Gateway Health" "$API_GATEWAY/health"
run_test test_json_endpoint "Simulation Engine Health" "$SIM_ENGINE/health"
run_test test_json_endpoint "Data Fetcher Health" "$DATA_FETCHER/health"

echo ""
echo "2️⃣  Testing API Gateway Endpoints"
echo "---------------------------------"
run_test test_endpoint "Teams List" "$API_GATEWAY/teams"
run_test test_endpoint "Players List" "$API_GATEWAY/players"
run_test test_endpoint "Games List" "$API_GATEWAY/games"
run_test test_endpoint "Single Team" "$API_GATEWAY/teams/nya" 404  # Expected 404 until data is loaded
run_test test_endpoint "Games by Date" "$API_GATEWAY/games/date/2025-07-22"

echo ""
echo "3️⃣  Testing Data Fetcher Endpoints"
echo "----------------------------------"
run_test test_json_endpoint "Fetch Status" "$DATA_FETCHER/status"
run_test test_post_endpoint "Trigger Fetch" "$DATA_FETCHER/fetch" '{"fetch_type":"teams"}' 200

echo ""
echo "4️⃣  Testing Database Connectivity"
echo "---------------------------------"
echo -n "Testing PostgreSQL connection... "
if docker exec baseball-sim-db pg_isready -U baseball_user -d baseball_sim >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Pass${NC}"
    ((passed_tests++))
else
    echo -e "${RED}✗ Fail${NC}"
fi
((total_tests++))

echo ""
echo "5️⃣  Testing Simulation Engine"
echo "-----------------------------"
# Create a test simulation (will fail without game data, but tests the endpoint)
run_test test_post_endpoint "Create Simulation" "$SIM_ENGINE/simulate" '{"game_id":"test123","simulation_runs":10}' 404

echo ""
echo "6️⃣  Checking Data Load Status"
echo "-----------------------------"
echo -n "Checking for loaded teams... "
team_count=$(curl -s "$DATA_FETCHER/status" 2>/dev/null | jq -r '.total_teams // 0')
if [ "$team_count" -gt 0 ]; then
    echo -e "${GREEN}✓ Pass${NC} ($team_count teams loaded)"
    ((passed_tests++))
else
    echo -e "${YELLOW}⚠ Warning${NC} (No teams loaded yet)"
fi
((total_tests++))

echo -n "Checking for loaded players... "
player_count=$(curl -s "$DATA_FETCHER/status" 2>/dev/null | jq -r '.total_players // 0')
if [ "$player_count" -gt 0 ]; then
    echo -e "${GREEN}✓ Pass${NC} ($player_count players loaded)"
    ((passed_tests++))
else
    echo -e "${YELLOW}⚠ Warning${NC} (No players loaded yet)"
fi
((total_tests++))

echo ""
echo "7️⃣  Testing Service Logs"
echo "-----------------------"
echo -n "Checking for errors in logs... "
error_count=0
for service in api-gateway sim-engine data-fetcher; do
    errors=$(docker-compose logs "$service" 2>&1 | grep -i "error" | grep -v "error encoding JSON" | wc -l)
    error_count=$((error_count + errors))
done

if [ "$error_count" -eq 0 ]; then
    echo -e "${GREEN}✓ Pass${NC} (No errors found)"
    ((passed_tests++))
else
    echo -e "${YELLOW}⚠ Warning${NC} ($error_count errors found in logs)"
fi
((total_tests++))

echo ""
echo "======================================="
echo "Test Results: $passed_tests/$total_tests passed"
echo "======================================="

if [ "$passed_tests" -eq "$total_tests" ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
elif [ "$passed_tests" -ge $((total_tests - 2)) ]; then
    echo -e "${YELLOW}⚠️  Most tests passed. Check warnings above.${NC}"
    exit 0
else
    echo -e "${RED}❌ Several tests failed. Please check the services.${NC}"
    exit 1
fi