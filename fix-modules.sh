#!/bin/bash

echo "Fixing Go module dependencies..."

# Fix API Gateway modules
echo "Fixing API Gateway..."
cd /Users/Chris.White/Documents/code-projects/baseball-simulation/api-gateway
go mod tidy
echo "API Gateway modules fixed."

# Fix Sim Engine modules  
echo "Fixing Sim Engine..."
cd /Users/Chris.White/Documents/code-projects/baseball-simulation/sim-engine
go mod tidy
echo "Sim Engine modules fixed."

echo "All Go modules fixed."