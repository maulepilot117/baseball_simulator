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

### Code Quality
- **Python linting**: `cd data-fetcher && flake8 .`
- **Python formatting**: `cd data-fetcher && black .`
- **Go formatting**: `cd api-gateway && go fmt ./...` or `cd sim-engine && go fmt ./...`
- **Go module tidy**: `go mod tidy` (run in respective Go service directories)

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
- **Go**: Gorilla Mux for routing, pgx for PostgreSQL connectivity
- **Python**: FastAPI for async HTTP, asyncpg for database access
- **Docker**: Containerized services with docker-compose orchestration
- **PostgreSQL**: Tuned for high-performance analytics workloads

## Service Endpoints

### API Gateway (http://localhost:8080/api/v1)
- `GET /health` - Service health check
- `GET /teams` - List all teams
- `GET /players` - List all players
- `GET /games` - List games
- `GET /games/date/{date}` - Games by date

### Simulation Engine (http://localhost:8081)
- `POST /simulate` - Create new simulation run
- `GET /simulation/{id}/status` - Check simulation progress
- `GET /simulation/{id}/result` - Get completed simulation results

### Data Fetcher (http://localhost:8082)
- `GET /health` - Service health check
- `GET /status` - Data fetch status and counts
- `POST /fetch` - Trigger manual data fetch

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

## Position-Specific Advanced Statistics

The system now includes specialized metrics for catchers and outfielders:

### Catcher Metrics
- **Pitch Framing**: FRAMING_RUNS - Runs saved/lost through pitch framing
- **Blocking**: BLOCKING_RUNS - Runs prevented through blocking pitches in dirt
- **Arm Strength**: ARM_RUNS - Runs saved through throwing out baserunners
- **Overall**: TOTAL_CATCHER_RUNS - Combined defensive value

### Outfielder Metrics  
- **Range**: RANGE_RUNS - Runs saved through superior range and coverage
- **Arm Strength**: ARM_RUNS - Runs saved through assist opportunities
- **Jump Rating**: First-step quickness on 20-80 scouting scale
- **Route Efficiency**: Optimal path-taking on fly balls
- **Overall**: TOTAL_OUTFIELD_RUNS - Combined defensive value

## API Endpoints

### Position-Specific Statistics
- `GET /player/{player_id}/catcher-metrics/{season}` - Catcher advanced metrics
- `GET /player/{player_id}/outfielder-metrics/{season}?position=CF` - Outfielder metrics
- `POST /calculate-position-stats/{season}` - Trigger position-specific calculations

### Leaderboards
- `GET /catcher-leaderboards/{season}?stat_name=FRAMING_RUNS&limit=25` - Catcher rankings
- `GET /outfielder-leaderboards/{season}?position=CF&stat_name=RANGE_RUNS&limit=25` - OF rankings
- `GET /leaderboards/{season}?stats_type=batting&stat_name=wRC+&limit=50` - General leaderboards
- `GET /fielding-leaderboards/{season}?position=SS&stat_name=UZR&limit=50` - Fielding rankings

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