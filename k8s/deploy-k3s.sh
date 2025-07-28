#!/bin/bash

# Deploy Baseball Simulation to k3s
set -e

echo "🏗️  Building Docker images for k3s..."

# Build images with k3s-compatible tags
echo "Building API Gateway..."
cd api-gateway && docker build -t baseball-sim/api-gateway:latest .

echo "Building Simulation Engine..."
cd ../sim-engine && docker build -t baseball-sim/sim-engine:latest .

echo "Building Data Fetcher..."
cd ../data-fetcher && docker build -t baseball-sim/data-fetcher:latest .

echo "Building Frontend..."
cd ../frontend && docker build -t baseball-sim/frontend:latest .

cd ..

# Import images into k3s
echo "🚢 Importing images into k3s..."
k3s ctr images import <(docker save baseball-sim/api-gateway:latest)
k3s ctr images import <(docker save baseball-sim/sim-engine:latest)
k3s ctr images import <(docker save baseball-sim/data-fetcher:latest)
k3s ctr images import <(docker save baseball-sim/frontend:latest)

echo "📋 Deploying to k3s..."

# Apply manifests in correct order
kubectl apply -f k8s/namespace.yaml

# PostgreSQL
kubectl apply -f k8s/postgres/postgres-secret.yaml
kubectl apply -f k8s/postgres/postgres-configmap.yaml
kubectl apply -f k8s/postgres/postgres-pvc.yaml
kubectl apply -f k8s/postgres/postgres-deployment.yaml
kubectl apply -f k8s/postgres/postgres-service.yaml

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n baseball-sim --timeout=300s

# Backend services
kubectl apply -f k8s/sim-engine/sim-engine-deployment.yaml
kubectl apply -f k8s/sim-engine/sim-engine-service.yaml

kubectl apply -f k8s/data-fetcher/data-fetcher-deployment.yaml
kubectl apply -f k8s/data-fetcher/data-fetcher-service.yaml

kubectl apply -f k8s/api-gateway/api-gateway-deployment.yaml
kubectl apply -f k8s/api-gateway/api-gateway-service.yaml

# Wait for backend services
echo "⏳ Waiting for backend services to be ready..."
kubectl wait --for=condition=ready pod -l app=sim-engine -n baseball-sim --timeout=300s
kubectl wait --for=condition=ready pod -l app=data-fetcher -n baseball-sim --timeout=300s
kubectl wait --for=condition=ready pod -l app=api-gateway -n baseball-sim --timeout=300s

# Frontend
kubectl apply -f k8s/frontend/frontend-deployment.yaml
kubectl apply -f k8s/frontend/frontend-service.yaml

# Wait for frontend
echo "⏳ Waiting for frontend to be ready..."
kubectl wait --for=condition=ready pod -l app=frontend -n baseball-sim --timeout=300s

echo "✅ Deployment complete!"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost:30080"
echo "   API Gateway: kubectl port-forward svc/api-gateway-service 8080:8080 -n baseball-sim"
echo ""
echo "🔍 Check status:"
echo "   kubectl get pods -n baseball-sim"
echo "   kubectl get services -n baseball-sim"
echo ""
echo "📋 View logs:"
echo "   kubectl logs -l app=api-gateway -n baseball-sim"
echo "   kubectl logs -l app=sim-engine -n baseball-sim"
echo "   kubectl logs -l app=data-fetcher -n baseball-sim"
echo "   kubectl logs -l app=frontend -n baseball-sim"