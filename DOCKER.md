# Baseball Simulation - Docker Deployment

This document provides comprehensive instructions for deploying and managing the Baseball Simulation system using Docker and Docker Compose.

## Prerequisites

- Docker 20.10 or later
- Docker Compose 2.0 or later
- At least 4GB RAM available for containers
- At least 10GB free disk space

### Language Versions Used
- **Go**: 1.24 (latest)
- **Python**: 3.13 (latest)
- **Deno**: 2.1.4 (latest)
- **Node.js**: 22.x (LTS)
- **PostgreSQL**: 15-alpine
- **Redis**: 7-alpine

## Quick Start

### Development Environment

```bash
# Start development environment with hot reload
./deploy.sh dev

# Or manually
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Production Environment

```bash
# Start production environment with load balancing
./deploy.sh prod

# Or manually
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Available Services

### Development Mode
- **Frontend**: http://localhost:3000 (React app with hot reload)
- **API Gateway**: http://localhost:8080 (Go REST API)
- **Simulation Engine**: http://localhost:8081 (Go simulation service)
- **Data Fetcher**: http://localhost:8082 (Python FastAPI)
- **Database**: localhost:5432 (PostgreSQL)
- **PgAdmin**: http://localhost:5050 (Database management)
- **Redis**: localhost:6379 (Caching)
- **Prometheus**: http://localhost:9090 (Metrics)
- **Grafana**: http://localhost:3001 (Dashboards)
- **MailHog**: http://localhost:8025 (Email testing)

### Production Mode
- **Main Application**: http://localhost (Nginx load balancer)
- **API Endpoints**: http://localhost/api/v1/
- **PgAdmin**: http://localhost:5050
- **Monitoring**: http://localhost:9090 (Prometheus)
- **Dashboards**: http://localhost:3001 (Grafana)
- **Logs**: http://localhost:5601 (Kibana)

## Deployment Script Usage

The `deploy.sh` script provides convenient commands for managing the system:

```bash
# Available commands
./deploy.sh dev          # Start development environment
./deploy.sh prod         # Start production environment
./deploy.sh build        # Build all services
./deploy.sh stop         # Stop all services
./deploy.sh cleanup      # Clean up containers and volumes
./deploy.sh logs         # Show logs for all services
./deploy.sh logs api-gateway  # Show logs for specific service
./deploy.sh test         # Run system tests
./deploy.sh monitor      # Monitor service status and resources
./deploy.sh help         # Show help message
```

## Environment Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize as needed:

```bash
cp .env.example .env
```

Key configuration options:

```bash
# Database
DB_NAME=baseball_sim
DB_USER=baseball_user
DB_PASSWORD=baseball_pass

# Service Ports
API_GATEWAY_PORT=8080
SIM_ENGINE_PORT=8081
DATA_FETCHER_PORT=8082
FRONTEND_PORT=3000

# Simulation Settings
SIM_WORKERS=4
SIMULATION_RUNS=1000

# External APIs
MLB_API_BASE_URL=https://statsapi.mlb.com/api/v1
FETCH_INTERVAL=3600
```

### Production Secrets

For production deployments, ensure you update these critical values:

```bash
# Generate secure passwords
DB_PASSWORD=your-secure-database-password
REDIS_PASSWORD=your-secure-redis-password
JWT_SECRET=your-super-secret-jwt-key
SESSION_SECRET=your-super-secret-session-key

# Admin credentials
PGADMIN_PASSWORD=your-secure-admin-password
GRAFANA_PASSWORD=your-secure-grafana-password
```

## Service Architecture

### Microservices

1. **API Gateway** (Go)
   - Routes requests to appropriate services
   - Handles authentication and rate limiting
   - Provides unified REST API

2. **Simulation Engine** (Go)
   - Monte Carlo baseball game simulations
   - High-performance concurrent processing
   - Real-time simulation results

3. **Data Fetcher** (Python)
   - Fetches data from MLB Stats API
   - Data validation and consistency checks
   - Network resilience with circuit breakers

4. **Frontend** (React/Deno)
   - Interactive web interface
   - Real-time simulation visualization
   - Game selection and results display

### Infrastructure Services

1. **PostgreSQL** - Primary database with optimized schemas
2. **Redis** - Caching and session management
3. **Nginx** - Load balancing and reverse proxy (production)
4. **Prometheus** - Metrics collection
5. **Grafana** - Monitoring dashboards
6. **Kibana/ELK** - Log aggregation (production)

## Scaling and Performance

### Development Scaling

Development environment is optimized for fast iteration:
- Single replica per service
- Volume mounts for hot reload
- Debug mode enabled
- Minimal resource limits

### Production Scaling

Production environment includes:
- Multiple replicas for high availability
- Load balancing with Nginx
- Resource limits and reservations
- Health checks and restart policies
- Log aggregation with ELK stack

### Manual Scaling

Scale specific services:

```bash
# Scale API Gateway to 3 replicas
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale api-gateway=3

# Scale simulation engine to 4 replicas
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale sim-engine=4
```

## Monitoring and Observability

### Health Checks

All services include health checks:
- HTTP endpoints return service status
- Database connectivity verification
- Resource usage monitoring

### Metrics

Prometheus collects metrics from:
- Application performance metrics
- Database query performance
- System resource usage
- Custom business metrics

### Logs

Development: `docker-compose logs -f [service-name]`
Production: Centralized logging with ELK stack

### Dashboards

Grafana provides pre-configured dashboards for:
- System overview
- Database performance
- API request metrics
- Simulation performance
- Error rates and alerts

## Database Management

### Database Access

```bash
# Using PgAdmin (recommended)
# Visit http://localhost:5050
# Email: admin@baseball.com
# Password: admin

# Direct psql access
docker-compose exec database psql -U baseball_user -d baseball_sim

# Or use the deployment script
./deploy.sh db shell
```

### Data Persistence

Data is persisted in Docker volumes:
- `postgres_data` - Production database
- `postgres_dev_data` - Development database
- `redis_data` - Cache data
- `grafana_data` - Dashboard configurations

### Database Initialization and Management

The database is **automatically initialized** when you first start the system:

```bash
# Start system - database initializes automatically
./deploy.sh dev

# Or manually initialize database
./deploy.sh db init
```

### Database Schema and Seeding

- **Schema**: Automatically created from `database/database/init/01-scheme.sql`
- **Development Data**: Sample teams, players, and games loaded in dev mode
- **Migrations**: Run additional schema changes with `./deploy.sh db migrate`

### Backup and Restore

```bash
# Create backup with timestamp
./deploy.sh db backup

# Restore from backup file
./deploy.sh db restore backup_20241127_143022.sql

# Manual backup/restore
docker-compose exec database pg_dump -U baseball_user baseball_sim > backup.sql
docker-compose exec -T database psql -U baseball_user baseball_sim < backup.sql
```

### Database Reset

```bash
# Complete database reset (destroys all data)
./deploy.sh db reset
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check for port usage
   netstat -tlnp | grep :8080
   
   # Change ports in .env file
   API_GATEWAY_PORT=8090
   ```

2. **Build Failures**
   ```bash
   # Clean build cache
   docker-compose build --no-cache
   
   # Check logs
   docker-compose logs --no-color > debug.log
   ```

3. **Database Connection Issues**
   ```bash
   # Verify database is running
   docker-compose exec database pg_isready -U baseball_user
   
   # Check connection from service
   docker-compose exec api-gateway ping database
   ```

4. **Memory Issues**
   ```bash
   # Check Docker memory allocation
   docker system df
   
   # Clean up unused resources
   docker system prune -af
   ```

### Service Dependencies

Services start in order based on dependencies:
1. Database (PostgreSQL)
2. Redis
3. Data Fetcher
4. Simulation Engine
5. API Gateway
6. Frontend
7. Monitoring services

### Debug Mode

Enable debug logging:

```bash
# Set in .env file
DEBUG=true
LOG_LEVEL=debug

# Restart services
docker-compose restart
```

## Security Considerations

### Production Security

1. **Change Default Passwords**: Update all default passwords in production
2. **Network Security**: Use custom networks for service isolation
3. **Non-Root Users**: All services run as non-root users
4. **Resource Limits**: Set appropriate CPU and memory limits
5. **Health Checks**: Monitor service health and restart on failure

### SSL/TLS

For production HTTPS:

1. Place SSL certificates in `nginx/ssl/`
2. Update nginx configuration for SSL
3. Redirect HTTP to HTTPS

### Secrets Management

Use Docker secrets for sensitive data:

```bash
echo "secret-password" | docker secret create db_password -
```

## Development Workflow

### Code Changes

Development environment supports hot reload:
- Go services: Manual restart required
- Python services: Auto-reload enabled
- Frontend: Hot module replacement (HMR)

### Testing

```bash
# Run all tests
./deploy.sh test

# Run specific service tests
docker-compose exec api-gateway go test ./...
docker-compose exec data-fetcher python -m pytest
```

### Debugging

```bash
# Access service shell
docker-compose exec api-gateway sh

# View real-time logs
docker-compose logs -f --tail=100 api-gateway

# Monitor resource usage
docker stats
```

## Maintenance

### Updates

```bash
# Update base images
docker-compose pull

# Rebuild services
docker-compose build --pull

# Restart with new images
docker-compose up -d
```

### Cleanup

```bash
# Remove unused containers and images
./deploy.sh cleanup

# Remove all data (DESTRUCTIVE)
docker-compose down -v
docker system prune -af
```

## Support

For additional support:
1. Check service logs: `docker-compose logs [service-name]`
2. Verify service health: `docker-compose ps`
3. Monitor resource usage: `docker stats`
4. Review configuration: `docker-compose config`

## Performance Tuning

### Database Optimization

Production PostgreSQL is configured with:
- Increased shared buffers
- Optimized work memory
- Enhanced connection pooling
- Query performance monitoring

### Application Optimization

- Connection pooling for all services
- Redis caching for frequently accessed data
- Horizontal scaling with load balancing
- Resource limits to prevent resource starvation

### Monitoring Performance

Use Grafana dashboards to monitor:
- Response times
- Database query performance
- Memory and CPU usage
- Error rates and success metrics