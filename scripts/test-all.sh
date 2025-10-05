#!/bin/bash
# Run all test suites for the Baseball Simulation system

set -e  # Exit on error

echo "🧪 Baseball Simulation - Running All Tests"
echo "==========================================="
echo ""

# Colors for output
GREEN='\033[0.32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# API Gateway Tests
echo -e "${BLUE}1. Running API Gateway Tests (Go)${NC}"
echo "-------------------------------------------"
cd /Users/Chris.White/Documents/code-projects/baseball-simulation/api-gateway
if go test -v ./...; then
    echo -e "${GREEN}✓ API Gateway tests passed${NC}"
else
    echo "✗ API Gateway tests failed"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Data Fetcher Tests
echo -e "${BLUE}2. Running Data Fetcher Tests (Python)${NC}"
echo "-------------------------------------------"
cd /Users/Chris.White/Documents/code-projects/baseball-simulation/data-fetcher
if pytest -v --tb=short; then
    echo -e "${GREEN}✓ Data Fetcher tests passed${NC}"
else
    echo "✗ Data Fetcher tests failed"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Integration Tests
echo -e "${BLUE}3. Running Integration Tests${NC}"
echo "-------------------------------------------"
cd /Users/Chris.White/Documents/code-projects/baseball-simulation

# Check if services are running
if ! curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Services not running. Skipping integration tests."
    echo "   Run 'docker-compose up -d' to start services."
else
    if pytest tests/integration/ -v --asyncio-mode=auto --tb=short 2>/dev/null; then
        echo -e "${GREEN}✓ Integration tests passed${NC}"
    else
        echo "✗ Integration tests failed (or no tests found)"
        FAILURES=$((FAILURES + 1))
    fi
fi
echo ""

# Summary
echo "==========================================="
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo "❌ $FAILURES test suite(s) failed"
    exit 1
fi
