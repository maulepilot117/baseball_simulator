# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Build
- **Initial setup**: `./scripts/setup.sh` - Sets up the entire development environment with Docker containers
- **Build all services**: `docker-compose build`
- **Start all services**: `docker-compose up -d`
- **View logs**: `docker-compose logs -f [service-name]`
- **Stop services**: `docker-compose down`

### Testing
- **Run system tests**: `./scripts/test.sh` - Comprehensive test suite that validates all service endpoints
- **Go module tests**: 
  - API Gateway: `cd api-gateway && go test ./...`
  - Simulation Engine: `cd sim-engine && go test ./...`
- **Python tests**: `cd data-fetcher && python -m pytest`
- **Test position-specific endpoints**: `cd data-fetcher && python tests/test_position_endpoints.py`

### Code Quality
- **Python linting**: `cd data-fetcher && flake8 .`
- **Python formatting**: `cd data-fetcher && black .`
- **Go formatting**: `cd api-gateway && go fmt ./...` or `cd sim-engine && go fmt ./...`
- **Go vet**: `cd api-gateway && go vet ./...` or `cd sim-engine && go vet ./...`
- **Go module tidy**: `go mod tidy` (run in respective Go service directories)

### Kubernetes Deployment
- **Quick k3s deployment**: `./k8s/deploy-k3s.sh` - Automated deployment to k3s cluster
- **Manual k8s deployment**: Apply manifests in order from `k8s/` directory

## Architecture Overview

This is a microservices-based baseball simulation system with the following components:

### Service Architecture
1. **API Gateway** (Go, port 8080) - HTTP REST API that routes requests to appropriate services
2. **Simulation Engine** (Go, port 8081) - Monte Carlo simulation engine for game predictions
3. **Data Fetcher** (Python/FastAPI, port 8082) - Fetches and processes MLB data from official APIs
4. **PostgreSQL Database** (port 5432) - Optimized for time-series baseball data with partitioned tables
5. **Frontend** (React/Deno, port 3000) - Web interface for game selection and result visualization

### Data Flow
- Data Fetcher pulls from MLB Stats API and stores in PostgreSQL
- API Gateway provides unified REST interface for frontend
- Simulation Engine performs Monte Carlo analysis (1000+ runs) using historical data
- Frontend displays simulation results and probability distributions

### Database Design
- Partitioned tables for optimal time-series performance
- JSON columns for flexible statistics storage
- Materialized views for common query patterns
- Optimized connection pooling across services

### Key Technologies
- **Go 1.25**: Gorilla Mux for routing, pgx for PostgreSQL connectivity
- **Python 3.13**: FastAPI for async HTTP, asyncpg for database access
- **Deno 2.1**: Modern TypeScript/JavaScript runtime for frontend
- **Node.js 22**: LTS version for build tools and compatibility
- **Docker**: Containerized services with docker-compose orchestration
- **PostgreSQL 15**: Tuned for high-performance analytics workloads

## Service Endpoints

### API Gateway (http://localhost:8080/api/v1)
- `GET /health` - Service health check
- `GET /search?q={query}` - Search across all entities (players, teams, games, umpires)
- `GET /teams` - List all teams
- `GET /teams/{id}` - Get specific team details
- `GET /teams/{id}/stats?season={year}` - Get team statistics (W-L record, runs scored/allowed)
- `GET /teams/{id}/games?season={year}` - Get team's games with pagination
- `GET /players` - List all players (supports filters: team, position, status, name)
- `GET /players/{id}` - Get specific player details
- `GET /players/{id}/stats` - Get player statistics
- `GET /games` - List games (supports filters: season, team, status, date)
- `GET /games/{id}` - Get specific game details
- `GET /games/date/{date}` - Games by date
- `GET /umpires` - List all umpires
- `GET /umpires/{id}` - Get specific umpire details
- `GET /umpires/{id}/stats` - Get umpire statistics
- `GET /simulations` - List past simulations
- `GET /simulations/{id}` - Get specific simulation result

### Simulation Engine (http://localhost:8081)
- `POST /simulate` - Create new simulation run
- `GET /simulation/{id}/status` - Check simulation progress
- `GET /simulation/{id}/result` - Get completed simulation results
- `GET /health` - Service health check

### Data Fetcher (http://localhost:8082)
- `GET /health` - Service health check
- `GET /status` - Data fetch status and counts
- `POST /fetch` - Trigger manual data fetch
- `GET /teams` - List all MLB teams
- `GET /players/{team_id}` - Get roster for specific team
- `GET /player/{player_id}/stats/{season}` - Get player statistics
- `GET /leaderboards/{season}` - Statistical leaderboards

## Position-Specific Analytics

### Catcher Metrics Endpoints
- `GET /player/{player_id}/catcher-metrics/{season}` - Advanced catcher metrics including:
  - Framing runs, blocking runs, arm runs
  - Pop time, exchange time
  - CS above average, total catcher runs

### Outfielder Metrics Endpoints  
- `GET /player/{player_id}/outfielder-metrics/{season}?position={LF|CF|RF}` - Outfielder metrics including:
  - Range runs, arm runs, jump rating
  - Route efficiency, sprint speed
  - First step time, total outfielder runs

### Position Leaderboards
- `GET /catcher-leaderboards/{season}?stat_name={metric}&limit={n}` - Catcher performance rankings
- `GET /outfielder-leaderboards/{season}?position={pos}&stat_name={metric}&limit={n}` - Outfielder rankings

Available stat_name values:
- Catchers: FRAMING_RUNS, BLOCKING_RUNS, ARM_RUNS, POP_TIME_SECONDS, TOTAL_CATCHER_RUNS
- Outfielders: RANGE_RUNS, ARM_RUNS, JUMP_RATING, ROUTE_EFFICIENCY, TOTAL_OUTFIELDER_RUNS

## Development Workflow

1. **Environment Setup**: Run `./scripts/setup.sh` to initialize the entire development environment
2. **Service Development**: Each service can be developed independently using Docker
3. **Database Access**: PgAdmin available at http://localhost:5050 (admin@baseball.com / admin)
4. **Testing**: Use `./scripts/test.sh` for comprehensive endpoint validation
5. **Monitoring**: Check service logs with `docker-compose logs -f [service-name]`

## Configuration

Services are configured via environment variables defined in `.env` file (created by setup script):
- Database connection details
- Service ports
- Simulation parameters (runs, workers)
- Data fetching intervals

## Database Schema

The database includes optimized tables for:
- Teams, players, and stadium information
- Games with detailed play-by-play data
- Pitch-level data for simulation accuracy
- Player statistics and performance metrics
- Simulation runs and aggregated results
- Advanced fielding metrics (UZR, DRS, positional adjustments)
- Position-specific statistics for catchers and outfielders
- Umpire performance data and scorecards

### Key Database Migrations
Run migrations in order:
1. `database/migrations/01_fix_schema_issues.sql`
2. `database/migrations/02_add_missing_tables.sql`
3. `database/migrations/003-fix_missing_columns.sql`
4. `database/migrations/004-position-specific-stats.sql`

## Enhanced System Features

### Network Resilience & Circuit Breakers
- **Circuit Breaker Protection**: Automatic failure detection and recovery for external APIs
- **Rate Limiting**: Configurable request rate limits to prevent API abuse
- **Exponential Backoff**: Smart retry logic with increasing delays
- **Fallback Mechanisms**: Graceful degradation when services are unavailable

### Data Consistency Validation
- **Real-time Validation**: Comprehensive data validation before database insertion
- **Consistency Checks**: Cross-validation between related data sources
- **Automated Reports**: Daily validation reports with severity levels
- **Auto-fix Capabilities**: Automatic correction of common data issues

### Performance Monitoring & Alerting
- **Real-time Metrics**: System CPU, memory, disk, and network monitoring
- **Database Monitoring**: Connection pool, query performance, table sizes
- **Custom Alerts**: Configurable thresholds for performance metrics
- **Historical Tracking**: 24-hour metric retention with statistical analysis

### Enhanced Input Validation
- **Security Sanitization**: SQL injection and XSS protection
- **Baseball-specific Rules**: Position, season, statistical boundary validation
- **Type Safety**: Automatic type conversion with bounds checking
- **Detailed Error Messages**: Actionable validation feedback

## Administrative API Endpoints

### System Monitoring
- `GET /admin/performance-dashboard` - Real-time performance metrics
- `GET /admin/circuit-breaker-status` - Circuit breaker states and statistics
- `POST /admin/reset-circuit-breaker/{breaker_name}` - Manual circuit breaker reset

### Data Quality
- `GET /admin/validation-reports?limit=10` - Recent validation reports
- `POST /admin/validate-data/{season}` - Trigger manual data validation
- `POST /fetch/historical-stats` - Fetch statistics for multiple seasons

## Error Handling & Resilience

### Circuit Breaker States
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service failing, requests blocked with immediate error
- **HALF_OPEN**: Testing recovery, limited requests allowed

### Alert Levels
- **INFO**: Informational metrics and status updates
- **WARNING**: Performance degradation or unusual patterns  
- **CRITICAL**: System failures requiring immediate attention

### Data Validation Severity
- **WARNING**: Data anomalies that don't prevent processing
- **ERROR**: Data issues that could affect calculations
- **CRITICAL**: Data corruption requiring immediate intervention

## Common Error Codes
- `404`: Resource not found
- `400`: Invalid request parameters
- `409`: Conflict (e.g., fetch already running)
- `429`: Rate limit exceeded
- `500`: Internal server error
- `503`: Service temporarily unavailable

## Performance Characteristics
- **Response Time**: <100ms for individual stats, <500ms for leaderboards
- **Throughput**: Handles 1000+ concurrent requests
- **Data Freshness**: Updated every 24 hours during season
- **Cache Efficiency**: 95%+ cache hit rate for static data
- **Simulation Speed**: ~10-30 seconds for 1000-run Monte Carlo simulation