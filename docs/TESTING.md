# Testing Framework Documentation

## Overview

This document outlines the comprehensive testing strategy for the Baseball Simulation system, including unit tests, integration tests, performance tests, and CI/CD automation.

---

## Test Architecture

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── api-gateway/        # Go unit tests
│   ├── data-fetcher/       # Python unit tests
│   └── sim-engine/         # Go simulation tests
├── integration/            # Integration tests across services
│   └── test_api_integration.py
├── e2e/                    # End-to-end tests
│   └── test_complete_workflows.py
└── performance/            # Performance and load tests
    └── test_benchmarks.py
```

---

## Unit Tests

### API Gateway (Go)

**Location**: `api-gateway/*_test.go`

**Run Tests**:
```bash
cd api-gateway
go test -v ./...
```

**Run with Coverage**:
```bash
go test -v -cover -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

**Run Benchmarks**:
```bash
go test -bench=. -benchmem ./...
```

**Test Files**:
- `helpers_test.go` - Input validation, sanitization, helpers
- `cache_test.go` - Query cache and rate limiter
- `handlers_test.go` (future) - HTTP handler tests with mocks

**Example Test**:
```go
func TestValidateSeasonParam(t *testing.T) {
    tests := []struct {
        name    string
        season  int
        wantErr bool
    }{
        {"valid current season", 2024, false},
        {"too old", 1800, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := validateSeasonParam(tt.season)
            if tt.wantErr {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
            }
        })
    }
}
```

---

### Data Fetcher (Python)

**Location**: `data-fetcher/tests/test_*.py`

**Run Tests**:
```bash
cd data-fetcher
pytest -v
```

**Run with Coverage**:
```bash
pytest --cov=. --cov-report=html
```

**Test Files**:
- `test_stats_calculator.py` - Statistics calculation logic
- `test_position_endpoints.py` - Position-specific API endpoints
- `test_mlb_api.py` (future) - MLB API integration

**Example Test**:
```python
def test_batting_average_calculation():
    stats = {'hits': 150, 'at_bats': 500}
    result = calculate_batting_stats(stats)
    assert result['ba'] == pytest.approx(0.300, 0.001)
```

---

### Simulation Engine (Go)

**Location**: `sim-engine/*_test.go`

**Run Tests**:
```bash
cd sim-engine
go test -v ./...
```

**Test Coverage**:
- Monte Carlo simulation logic
- Probability calculations
- Game outcome distribution
- Player performance modeling

---

## Integration Tests

**Location**: `tests/integration/test_api_integration.py`

**Run Tests**:
```bash
# Ensure all services are running
docker-compose up -d

# Run integration tests
pytest tests/integration/ -v --asyncio-mode=auto
```

**Test Categories**:

### 1. API Gateway Integration
- Health checks
- Metrics endpoint
- CRUD operations
- Pagination
- Rate limiting
- Compression

### 2. Data Fetcher Integration
- Health checks
- Data fetch status
- Stats calculations
- Position-specific endpoints

### 3. Simulation Engine Integration
- Simulation creation
- Status tracking
- Result retrieval
- WebSocket connections

### 4. End-to-End Workflows
- Complete game query workflow
- Player stats workflow
- Simulation workflow

### 5. Error Handling
- Invalid inputs
- Missing resources
- Rate limit exceeded
- Database errors

---

## Performance Tests

**Location**: `tests/performance/`

### Response Time Tests

```python
@pytest.mark.asyncio
async def test_response_time_teams(http_client):
    start = time.time()
    response = await http_client.get(f"{BASE_URL}/api/v1/teams")
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed < 0.5  # < 500ms
```

### Concurrent Load Tests

```python
@pytest.mark.asyncio
async def test_concurrent_requests(http_client):
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)

    successful = sum(1 for r in responses if r.status_code == 200)
    assert successful >= 95  # 95% success rate
```

### Benchmarks

```bash
# Go benchmarks
cd api-gateway
go test -bench=BenchmarkQueryCache -benchmem

# Expected results:
BenchmarkQueryCacheGet-8     10000000    150 ns/op    32 B/op    1 allocs/op
```

---

## Test Data Management

### Test Database

**Create Test Database**:
```bash
# Create test-specific database
docker exec baseball-db psql -U baseball_user -c "CREATE DATABASE baseball_sim_test;"

# Run migrations
docker exec baseball-db psql -U baseball_user -d baseball_sim_test -f /docker-entrypoint-initdb.d/schema.sql
```

### Test Fixtures

**Python Fixtures** (`conftest.py`):
```python
@pytest.fixture
async def db_pool():
    pool = await asyncpg.create_pool(...)
    yield pool
    await pool.close()

@pytest.fixture
def sample_team():
    return {
        'id': 'test-team-uuid',
        'name': 'Test Yankees',
        'abbreviation': 'TYY'
    }
```

---

## Mocking and Stubbing

### Database Mocks (Go)

```go
import "github.com/pashagolub/pgxmock/v4"

mock, _ := pgxmock.NewPool()
rows := pgxmock.NewRows([]string{"id", "name"}).
    AddRow("uuid-1", "Yankees")

mock.ExpectQuery("SELECT (.+) FROM teams").WillReturnRows(rows)
```

### HTTP Mocks (Python)

```python
import httpx
from respx import MockRouter

@respx.mock
async def test_mlb_api():
    respx.get("https://statsapi.mlb.com/api/v1/teams").mock(
        return_value=httpx.Response(200, json={"teams": []})
    )
```

---

## Continuous Integration

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test-api-gateway:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.24'
      - name: Run tests
        run: |
          cd api-gateway
          go test -v -cover ./...

  test-data-fetcher:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          cd data-fetcher
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd data-fetcher
          pytest -v --cov=.

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run integration tests
        run: pytest tests/integration/ -v
```

---

## Test Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| API Gateway | 75% | 85% |
| Data Fetcher | 60% | 80% |
| Simulation Engine | 50% | 75% |
| Integration | 70% | 90% |

---

## Running All Tests

### Quick Test Suite
```bash
# Run all unit tests
./scripts/test-all.sh
```

### Full Test Suite
```bash
# Start all services
docker-compose up -d

# Run unit tests
cd api-gateway && go test -v ./...
cd data-fetcher && pytest -v

# Run integration tests
pytest tests/integration/ -v

# Generate coverage reports
./scripts/coverage-report.sh
```

---

## Test Best Practices

### 1. **Test Isolation**
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. **Clear Test Names**
```go
// Good
func TestValidateSeasonParam_TooOld_ReturnsError(t *testing.T)

// Bad
func TestValidate1(t *testing.T)
```

### 3. **Arrange-Act-Assert Pattern**
```python
def test_calculate_batting_average():
    # Arrange
    stats = {'hits': 150, 'at_bats': 500}

    # Act
    result = calculate_batting_stats(stats)

    # Assert
    assert result['ba'] == pytest.approx(0.300)
```

### 4. **Test Edge Cases**
- Null/empty inputs
- Zero values
- Maximum values
- Invalid formats

### 5. **Performance Tests**
- Set realistic thresholds
- Test under load
- Monitor resource usage

---

## Debugging Tests

### Go Tests
```bash
# Run specific test
go test -v -run TestValidateSeasonParam

# Debug with delve
dlv test -- -test.run TestValidateSeasonParam
```

### Python Tests
```bash
# Run specific test
pytest tests/test_stats_calculator.py::TestBattingStatsCalculator::test_batting_average_calculation -v

# Debug with pdb
pytest --pdb
```

---

## Test Utilities

### Helper Scripts

**`scripts/test-all.sh`**:
```bash
#!/bin/bash
set -e

echo "Running API Gateway tests..."
cd api-gateway && go test -v ./...

echo "Running Data Fetcher tests..."
cd data-fetcher && pytest -v

echo "Running Integration tests..."
pytest tests/integration/ -v

echo "All tests passed! ✅"
```

**`scripts/coverage-report.sh`**:
```bash
#!/bin/bash
set -e

# Go coverage
cd api-gateway
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out -o coverage.html

# Python coverage
cd data-fetcher
pytest --cov=. --cov-report=html

echo "Coverage reports generated!"
echo "Go: api-gateway/coverage.html"
echo "Python: data-fetcher/htmlcov/index.html"
```

---

## Troubleshooting

### Common Issues

**1. "Database connection refused"**
```bash
# Ensure database is running
docker-compose ps database

# Check connection
docker exec baseball-db psql -U baseball_user -c "SELECT 1;"
```

**2. "Import errors in Python tests"**
```bash
# Install test dependencies
pip install -r requirements.txt
pytest --collect-only  # Verify tests are discovered
```

**3. "Go test timeout"**
```bash
# Increase timeout
go test -timeout 30s -v ./...
```

---

## Resources

- [Go Testing Package](https://pkg.go.dev/testing)
- [pytest Documentation](https://docs.pytest.org/)
- [testify Assertions](https://github.com/stretchr/testify)
- [httpx Testing](https://www.python-httpx.org/advanced/#testing)

---

**Last Updated**: 2025-10-05
**Maintained By**: Development Team
