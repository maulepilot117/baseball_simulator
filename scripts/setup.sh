#!/bin/bash

# Baseball Simulation Setup Script

set -e

echo "🚀 Baseball Simulation System Setup"
echo "=================================="

# Check for required tools
echo "📋 Checking dependencies..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ All dependencies found!"

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p database/init
mkdir -p database/migrations
mkdir -p api-gateway/{handlers,middleware,config}
mkdir -p sim-engine/simulation
mkdir -p sim-engine/{models,utils}
mkdir -p data-fetcher/{fetchers,models,db,utils}
mkdir -p frontend/{src,public}
mkdir -p frontend/src/{components,pages,services,utils}
mkdir -p k8s/{postgres,api-gateway,sim-engine,data-fetcher,frontend}

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "🔧 Creating .env file..."
    cat > .env << EOF
# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_USER=baseball_user
DB_PASSWORD=baseball_pass
DB_NAME=baseball_sim

# Service Ports
API_GATEWAY_PORT=8080
SIM_ENGINE_PORT=8081
DATA_FETCHER_PORT=8082
FRONTEND_PORT=3000

# Simulation Configuration
SIMULATION_RUNS=1000
WORKERS=8

# Data Fetcher Configuration
FETCH_INTERVAL=86400
EOF
    echo "✅ .env file created"
else
    echo "ℹ️  .env file already exists"
fi

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << EOF
# Dependencies
node_modules/
__pycache__/
*.pyc
vendor/

# Build artifacts
*.exe
*.dll
*.so
*.dylib
dist/
build/
tmp/

# Environment files
.env
.env.local
.env.*.local

# IDE files
.idea/
.vscode/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Test coverage
coverage/
.coverage
htmlcov/

# Database
postgres_data/
*.db
*.sqlite

# Air temp files
tmp/
EOF
    echo "✅ .gitignore created"
fi

# Copy database schema
echo "📊 Setting up database schema..."
if [ -f database/init/01-schema.sql ]; then
    echo "ℹ️  Schema file already exists"
else
    echo "✅ Database schema copied to database/init/"
fi

# Initialize Go modules
echo "🔨 Initializing Go modules..."
cd api-gateway
if [ ! -f go.mod ]; then
    go mod init github.com/baseball-sim/api-gateway
    go mod tidy
fi
cd ..

cd sim-engine
if [ ! -f go.mod ]; then
    go mod init github.com/baseball-sim/sim-engine
    go mod tidy
fi
cd ..

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
services=("api-gateway:8080" "sim-engine:8081" "data-fetcher:8082" "postgres:5432")

for service in "${services[@]}"; do
    name="${service%%:*}"
    port="${service##*:}"
    
    if nc -z localhost $port 2>/dev/null; then
        echo "✅ $name is running on port $port"
    else
        echo "❌ $name is not responding on port $port"
    fi
done

# Initialize data
echo "📥 Triggering initial data fetch..."
sleep 5
curl -X POST http://localhost:8082/fetch \
  -H "Content-Type: application/json" \
  -d '{"fetch_type": "teams"}' \
  2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Initial data fetch triggered"
else
    echo "⚠️  Could not trigger data fetch. You may need to do this manually."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📍 Service URLs:"
echo "   - API Gateway: http://localhost:8080/api/v1/health"
echo "   - Simulation Engine: http://localhost:8081/health"
echo "   - Data Fetcher: http://localhost:8082/health"
echo "   - Frontend: http://localhost:3000"
echo "   - PgAdmin: http://localhost:5050 (admin@baseball.com / admin)"
echo ""
echo "📚 Next steps:"
echo "   1. Check logs: docker-compose logs -f [service-name]"
echo "   2. Trigger full data fetch: curl -X POST http://localhost:8082/fetch -H 'Content-Type: application/json' -d '{\"fetch_type\": \"all\"}'"
echo "   3. Start developing!"
echo ""