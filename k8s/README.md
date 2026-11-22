# NagaraAI — Kubernetes Deployment Guide

Deploy the full NagaraAI stack (PostgreSQL + FastAPI backend + React frontend) on a local **minikube** or **kind** cluster with zero cloud dependencies.

---

## Folder structure

```
k8s/
├── namespace.yaml          # nagaraai namespace
├── kind-config.yaml        # kind cluster config (port mappings + ingress labels)
├── skaffold.yaml           # one-command build + deploy loop
├── secrets/
│   └── secrets.yaml        # DB credentials + JWT secret (base64-encoded)
├── postgres/
│   ├── pvc.yaml            # 1 Gi PersistentVolumeClaim
│   ├── deployment.yaml     # postgres:16-alpine with readiness probe
│   └── service.yaml        # ClusterIP  postgres-svc:5432
├── backend/
│   ├── deployment.yaml     # FastAPI + initContainer that waits for Postgres
│   └── service.yaml        # ClusterIP  backend-svc:8000
├── frontend/
│   ├── deployment.yaml     # Nginx + ConfigMap that proxies /api → backend
│   └── service.yaml        # NodePort  frontend-svc:3000 → host:30080
└── ingress/
    └── ingress.yaml        # nginx-ingress: /api → backend, / → frontend
```

The file `frontend/Dockerfile.k8s` is a **multi-stage production build** (Node build → Nginx serve). It is separate from `frontend/Dockerfile` which runs the CRA dev server and is only used for `docker compose`.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| kubectl | 1.28+ | https://kubernetes.io/docs/tasks/tools/ |
| minikube **or** kind | latest | https://minikube.sigs.k8s.io / https://kind.sigs.k8s.io |
| skaffold *(optional)* | v2+ | https://skaffold.dev/docs/install/ |

---

## Option A — minikube

### 1. Start the cluster

```bash
minikube start --cpus=4 --memory=4096
minikube addons enable ingress
```

### 2. Build images inside minikube's Docker daemon

```bash
eval $(minikube docker-env)          # Windows: minikube docker-env | Invoke-Expression
docker build -t nagaraai-backend:latest ./backend
docker build -f frontend/Dockerfile.k8s -t nagaraai-frontend:latest ./frontend
```

### 3. Apply all manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/secrets.yaml
kubectl apply -f k8s/postgres/pvc.yaml
kubectl apply -f k8s/postgres/deployment.yaml
kubectl apply -f k8s/postgres/service.yaml
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/backend/service.yaml
kubectl apply -f k8s/frontend/deployment.yaml
kubectl apply -f k8s/frontend/service.yaml
kubectl apply -f k8s/ingress/ingress.yaml
```

### 4. Wait for pods to become ready

```bash
kubectl -n nagaraai get pods -w
# All three pods (postgres, backend, frontend) must show  Running  1/1
```

### 5. Access the app

```bash
# Option 1 – via ingress
minikube tunnel          # run in a separate terminal; keeps tunnel open
open http://localhost    # app at port 80

# Option 2 – direct NodePort (no tunnel needed)
minikube service frontend-svc -n nagaraai --url
```

---

## Option B — kind

### 1. Create the cluster with pre-configured port mappings

```bash
kind create cluster --name nagaraai --config k8s/kind-config.yaml
```

### 2. Install the ingress controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait until the controller is ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### 3. Load images into the kind cluster

```bash
docker build -t nagaraai-backend:latest ./backend
docker build -f frontend/Dockerfile.k8s -t nagaraai-frontend:latest ./frontend

kind load docker-image nagaraai-backend:latest --name nagaraai
kind load docker-image nagaraai-frontend:latest --name nagaraai
```

### 4. Apply manifests (same as minikube step 3)

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/secrets.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress/
```

### 5. Access the app

```bash
# Ingress is exposed on host port 80 (configured in kind-config.yaml)
open http://localhost

# Direct NodePort — the frontend service also exposes host port 30080
open http://localhost:30080
```

---

## Option C — Skaffold (automated dev loop)

Skaffold rebuilds images and re-deploys automatically when source files change.

```bash
# minikube
eval $(minikube docker-env)
skaffold dev --filename k8s/skaffold.yaml

# kind
skaffold dev --filename k8s/skaffold.yaml --default-repo ""
```

Skaffold will:
1. Build both Docker images
2. Apply all manifests in the right order
3. Stream pod logs to your terminal
4. Port-forward `localhost:3000` → frontend and `localhost:8000` → backend
5. Watch for file changes and redeploy automatically

---

## Useful kubectl commands

```bash
# Watch all pods
kubectl -n nagaraai get pods -w

# Check backend logs
kubectl -n nagaraai logs -l app=backend -f

# Check frontend logs
kubectl -n nagaraai logs -l app=frontend -f

# Describe a crashing pod
kubectl -n nagaraai describe pod <pod-name>

# Open an interactive shell in the backend pod
kubectl -n nagaraai exec -it deploy/backend -- /bin/sh

# Forward backend port for direct API testing (Swagger at http://localhost:8000/docs)
kubectl -n nagaraai port-forward svc/backend-svc 8000:8000
```

---

## Seed data

After the backend pod is running, seed the database with Bengaluru wards and test users:

```bash
kubectl -n nagaraai exec -it deploy/backend -- python seed.py
```

---

## Customising secrets

The default secrets in `k8s/secrets/secrets.yaml` are for local development only.
To change any value:

```bash
# Encode the new value
echo -n "my-new-secret-key" | base64

# Update the yaml, then apply
kubectl apply -f k8s/secrets/secrets.yaml
kubectl -n nagaraai rollout restart deployment/backend
```

---

## Teardown

```bash
# Delete all nagaraai resources (keeps the cluster)
kubectl delete namespace nagaraai

# Delete the entire cluster
minikube delete          # or:  kind delete cluster --name nagaraai
```

---

## Architecture inside the cluster

```
                 ┌────────────────────────────────────────────┐
                 │                 nagaraai namespace          │
                 │                                             │
  HTTP :80  ───► │  nginx-ingress                             │
                 │    /api/* ──────────► backend-svc:8000     │
                 │    /*     ──────────► frontend-svc:3000    │
  NodePort :30080│                            │               │
  ──────────────►│  frontend pod              │               │
                 │  (nginx + React build)     │               │
                 │    /api/* proxy ───────────┘               │
                 │                                             │
                 │  backend pod (FastAPI)                     │
                 │    ──────────────► postgres-svc:5432       │
                 │                        │                   │
                 │  postgres pod          │                   │
                 │  (PVC: 1Gi) ◄──────────┘                   │
                 └────────────────────────────────────────────┘
```
