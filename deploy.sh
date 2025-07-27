#!/bin/bash

# Baseball Simulation Deployment Script
# This script handles building and deploying the containerized baseball simulation system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p nginx/ssl
    mkdir -p elk
    mkdir -p monitoring/grafana/datasources
    mkdir -p monitoring/grafana/dashboards
    mkdir -p logs
    
    print_success "Directories created"
}

# Function to generate basic nginx configuration
create_nginx_config() {
    print_status "Creating nginx configuration..."
    
    mkdir -p nginx
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api-gateway:8080;
    }
    
    upstream frontend_backend {
        server frontend:3000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location / {
            proxy_pass http://frontend_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
    
    print_success "Nginx configuration created"
}

# Function to build all services
build_services() {
    print_status "Building all services..."
    
    # Build each service individually to catch any build errors
    print_status "Building API Gateway..."
    docker-compose build api-gateway
    
    print_status "Building Simulation Engine..."
    docker-compose build sim-engine
    
    print_status "Building Data Fetcher..."
    docker-compose build data-fetcher
    
    print_status "Building Frontend..."
    docker-compose build frontend
    
    print_success "All services built successfully"
}

# Function to run development environment
run_development() {
    print_status "Starting development environment..."
    
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    
    print_success "Development environment started"
    print_status "Services available at:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - API Gateway: http://localhost:8080"
    echo "  - Simulation Engine: http://localhost:8081"
    echo "  - Data Fetcher: http://localhost:8082"
    echo "  - PgAdmin: http://localhost:5050"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3001"
    echo "  - MailHog: http://localhost:8025"
}

# Function to run production environment
run_production() {
    print_status "Starting production environment..."
    
    # Create nginx config for production
    create_nginx_config
    
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    
    print_success "Production environment started"
    print_status "Services available at:"
    echo "  - Main Application: http://localhost"
    echo "  - PgAdmin: http://localhost:5050"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3001"
    echo "  - Kibana: http://localhost:5601"
}

# Function to stop all services
stop_services() {
    print_status "Stopping all services..."
    
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down 2>/dev/null || true
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
    docker-compose down 2>/dev/null || true
    
    print_success "All services stopped"
}

# Function to clean up everything
cleanup() {
    print_status "Cleaning up containers, networks, and volumes..."
    
    stop_services
    
    # Remove all containers
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v --remove-orphans 2>/dev/null || true
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v --remove-orphans 2>/dev/null || true
    
    # Remove built images
    docker rmi $(docker images | grep baseball | awk '{print $3}') 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

# Function to run tests
run_tests() {
    print_status "Running system tests..."
    
    # Ensure services are running
    docker-compose up -d database
    sleep 10
    
    # Run tests for each service
    print_status "Testing API Gateway..."
    docker-compose exec api-gateway go test ./... || print_warning "API Gateway tests failed"
    
    print_status "Testing Simulation Engine..."
    docker-compose exec sim-engine go test ./... || print_warning "Simulation Engine tests failed"
    
    print_status "Testing Data Fetcher..."
    docker-compose exec data-fetcher python -m pytest || print_warning "Data Fetcher tests failed"
    
    print_success "Tests completed"
}

# Function to manage database
manage_database() {
    local action=$1
    
    case $action in
        "init"|"initialize")
            print_status "Initializing database..."
            docker-compose up -d database
            sleep 10
            
            # Wait for database to be ready
            print_status "Waiting for database to be ready..."
            while ! docker-compose exec database pg_isready -U baseball_user -d baseball_sim; do
                sleep 2
            done
            
            print_success "Database initialized and ready"
            ;;
        "backup")
            print_status "Creating database backup..."
            timestamp=$(date +%Y%m%d_%H%M%S)
            docker-compose exec database pg_dump -U baseball_user baseball_sim > "backup_${timestamp}.sql"
            print_success "Backup created: backup_${timestamp}.sql"
            ;;
        "restore")
            local backup_file=$2
            if [ -z "$backup_file" ]; then
                print_error "Please specify backup file: ./deploy.sh db restore backup_file.sql"
                return 1
            fi
            
            if [ ! -f "$backup_file" ]; then
                print_error "Backup file not found: $backup_file"
                return 1
            fi
            
            print_status "Restoring database from $backup_file..."
            docker-compose exec -T database psql -U baseball_user baseball_sim < "$backup_file"
            print_success "Database restored from $backup_file"
            ;;
        "migrate")
            print_status "Running database migrations..."
            # This would run migration scripts in order
            for migration in database/migrations/*.sql; do
                if [ -f "$migration" ]; then
                    print_status "Running migration: $(basename $migration)"
                    docker-compose exec -T database psql -U baseball_user baseball_sim < "$migration"
                fi
            done
            print_success "Migrations completed"
            ;;
        "reset")
            print_warning "This will completely reset the database. Are you sure? (y/N)"
            read -r confirmation
            if [ "$confirmation" = "y" ] || [ "$confirmation" = "Y" ]; then
                print_status "Resetting database..."
                docker-compose down -v
                docker volume rm baseball-simulation_postgres_data 2>/dev/null || true
                docker volume rm baseball-simulation_postgres_dev_data 2>/dev/null || true
                docker volume rm baseball-simulation_postgres_prod_data 2>/dev/null || true
                print_success "Database reset complete"
            else
                print_status "Database reset cancelled"
            fi
            ;;
        "shell")
            print_status "Opening database shell..."
            docker-compose exec database psql -U baseball_user baseball_sim
            ;;
        *)
            print_error "Unknown database action: $action"
            echo "Available actions:"
            echo "  init     - Initialize database"
            echo "  backup   - Create database backup"
            echo "  restore  - Restore from backup file"
            echo "  migrate  - Run pending migrations"
            echo "  reset    - Reset database (destroys all data)"
            echo "  shell    - Open database shell"
            ;;
    esac
}

# Function to monitor services
monitor() {
    print_status "Monitoring services..."
    
    while true; do
        clear
        echo "=== Baseball Simulation System Status ==="
        echo
        docker-compose ps
        echo
        echo "=== Resource Usage ==="
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
        echo
        echo "Press Ctrl+C to exit monitoring"
        sleep 5
    done
}

# Function to display help
show_help() {
    echo "Baseball Simulation Deployment Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Application Commands:"
    echo "  dev       Start development environment"
    echo "  prod      Start production environment"
    echo "  build     Build all services"
    echo "  stop      Stop all services"
    echo "  cleanup   Clean up containers, networks, and volumes"
    echo "  logs      Show logs (optionally for specific service)"
    echo "  test      Run system tests"
    echo "  monitor   Monitor service status and resource usage"
    echo
    echo "Database Commands:"
    echo "  db init            Initialize database"
    echo "  db backup          Create database backup"
    echo "  db restore <file>  Restore from backup file"
    echo "  db migrate         Run pending migrations"
    echo "  db reset           Reset database (destroys all data)"
    echo "  db shell           Open database shell"
    echo
    echo "General:"
    echo "  help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 dev                        # Start development environment"
    echo "  $0 logs api-gateway           # Show logs for API Gateway service"
    echo "  $0 db backup                  # Create database backup"
    echo "  $0 db restore backup.sql      # Restore from backup"
    echo "  $0 cleanup                    # Clean up everything"
}

# Main script logic
main() {
    local command=${1:-help}
    
    case $command in
        "dev"|"development")
            check_docker
            check_docker_compose
            create_directories
            build_services
            run_development
            ;;
        "prod"|"production")
            check_docker
            check_docker_compose
            create_directories
            build_services
            run_production
            ;;
        "build")
            check_docker
            check_docker_compose
            build_services
            ;;
        "stop")
            stop_services
            ;;
        "cleanup")
            cleanup
            ;;
        "logs")
            show_logs $2
            ;;
        "test")
            run_tests
            ;;
        "db"|"database")
            manage_database $2 $3
            ;;
        "monitor")
            monitor
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"