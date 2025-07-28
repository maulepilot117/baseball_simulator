# Baseball Simulation k3s Deployment

This directory contains Kubernetes manifests for deploying the Baseball Simulation application on k3s.

## Prerequisites

1. **k3s installed and running**:
   ```bash
   curl -sfL https://get.k3s.io | sh -
   ```

2. **kubectl configured** (k3s installs this automatically at `/usr/local/bin/kubectl`)

3. **Docker** for building images

## Quick Deployment

Run the automated deployment script:

```bash
./deploy-k3s.sh
```

This script will:
1. Build all Docker images with appropriate tags
2. Import images into k3s
3. Deploy all services in the correct order
4. Wait for services to be ready

## Manual Deployment

If you prefer to deploy manually:

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy PostgreSQL
kubectl apply -f postgres/
kubectl wait --for=condition=ready pod -l app=postgres -n baseball-sim --timeout=300s

# Deploy backend services
kubectl apply -f sim-engine/
kubectl apply -f data-fetcher/
kubectl apply -f api-gateway/

# Deploy frontend
kubectl apply -f frontend/
```

## Access the Application

- **Frontend**: http://localhost:30080
- **API Gateway** (via port-forward): 
  ```bash
  kubectl port-forward svc/api-gateway-service 8080:8080 -n baseball-sim
  ```

## Monitoring

Check deployment status:
```bash
kubectl get pods -n baseball-sim
kubectl get services -n baseball-sim
```

View logs:
```bash
kubectl logs -l app=api-gateway -n baseball-sim
kubectl logs -l app=sim-engine -n baseball-sim -f
kubectl logs -l app=data-fetcher -n baseball-sim -f
kubectl logs -l app=frontend -n baseball-sim
```

## Configuration

### Database
- **Credentials**: baseball_admin / baseball_password
- **Database**: baseball_db
- **Storage**: 10Gi persistent volume (local-path storage class)

### Services
- **API Gateway**: 2 replicas, 8080
- **Simulation Engine**: 2 replicas, 8081
- **Data Fetcher**: 1 replica, 8082
- **Frontend**: 2 replicas, 80
- **PostgreSQL**: 1 replica, 5432

### Resource Limits
All services include appropriate resource requests and limits for local k3s deployment.

## Cleanup

To remove the entire deployment:
```bash
kubectl delete namespace baseball-sim
```