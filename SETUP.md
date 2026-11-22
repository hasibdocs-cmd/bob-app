# NagaraAI — Complete Setup & Operations Guide

## Stack

| Component | Technology | Port |
|-----------|-----------|------|
| Frontend  | React 18 (CRA dev-server) | 3000 |
| Backend   | FastAPI + Uvicorn (auto-reload) | 8000 |
| Database  | PostgreSQL 16 | 5432 |

---

## Prerequisites

- **Docker Desktop** (Windows/Mac/Linux) — https://www.docker.com/products/docker-desktop
- Docker Desktop must be **running** before any command below.

---

## Quick Start (Docker Compose)

### 1 — Clone / open the project

```bash
cd nagaraai
```

### 2 — Start all services

```bash
docker compose up -d
```

First run builds images and pulls postgres (~2 min). Subsequent starts use cached layers (~10 s).

### 3 — Seed the database

Run once after the first `up`:

```bash
docker compose exec backend python seed.py
```

Output confirms:
```
✅ Database seeded successfully.
Demo logins:
  Citizen:        citizen@demo.com / demo1234
  Field Officer:  field@demo.com   / demo1234
  Ward Officer:   ward@demo.com    / demo1234
  Commissioner:   commissioner@demo.com / demo1234
```

### 4 — Open the app

| URL | What it is |
|-----|-----------|
| http://localhost:3000 | React frontend |
| http://localhost:8000/docs | FastAPI Swagger UI |
| http://localhost:8000/health | Health check |

---

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Citizen | `citizen@demo.com` | `demo1234` |
| Field Officer | `field@demo.com` | `demo1234` |
| Ward Officer | `ward@demo.com` | `demo1234` |
| Commissioner | `commissioner@demo.com` | `demo1234` |

Click the quick-fill buttons on the Login page, or type the credentials manually.

---

## Run the Test Suite

```bash
# Build the test image (once)
docker build -f backend/Dockerfile.test -t nagaraai-test ./backend

# Run all 57 tests
docker run --rm nagaraai-test
```

Expected output:
```
======================= 57 passed, 54 warnings in 3.82s ========================
```

---

## Common Operations

### Stop everything
```bash
docker compose down
```

### Stop and wipe the database (full reset)
```bash
docker compose down -v
```

### Rebuild after a code change
```bash
# Backend only
docker compose up -d --build backend

# Frontend only
docker compose up -d --build frontend

# Both
docker compose up -d --build
```

### View live logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

### Open a shell inside a container
```bash
docker compose exec backend /bin/bash
docker compose exec db psql -U nagaraai -d nagaraai_db
```

---

## Environment Variables

All backend settings live in `backend/.env` (gitignored). Defaults come from `backend/app/config.py`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://nagaraai:nagaraai123@db:5432/nagaraai_db` | Postgres connection |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 h) | Token lifetime |
| `WATSONX_API_KEY` | *(empty)* | IBM watsonx.ai key — leave blank to use local rule-based classifier |
| `WATSONX_PROJECT_ID` | *(empty)* | IBM watsonx project ID |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | watsonx endpoint |

To enable the AI classifier, create `backend/.env`:
```
WATSONX_API_KEY=your-key-here
WATSONX_PROJECT_ID=your-project-id
```
Then restart: `docker compose up -d backend`

---

## Kubernetes (minikube / kind)

See `k8s/README.md` for the full guide. Quick summary:

```bash
# minikube
minikube start --cpus=4 --memory=4096
minikube addons enable ingress
eval $(minikube docker-env)
docker build -t nagaraai-backend:latest ./backend
docker build -f frontend/Dockerfile.k8s -t nagaraai-frontend:latest ./frontend
kubectl apply -f k8s/namespace.yaml -f k8s/secrets/ -f k8s/postgres/ \
              -f k8s/backend/ -f k8s/frontend/ -f k8s/ingress/
kubectl -n nagaraai exec -it deploy/backend -- python seed.py
minikube tunnel   # → http://localhost
```

---

## Architecture

```
Browser
  │
  ▼  :3000
┌──────────────┐
│   Frontend   │  React SPA (CRA dev-server)
│  nginx proxy │  /api/* → backend:8000  (via setupProxy.js)
└──────┬───────┘
       │  :8000
       ▼
┌──────────────┐
│   Backend    │  FastAPI + Uvicorn
│              │  JWT auth  •  AI classification (watsonx / local)
└──────┬───────┘
       │  :5432
       ▼
┌──────────────┐
│  PostgreSQL  │  persistent volume (pgdata)
└──────────────┘
```

---

## Known Issues Fixed

| Issue | Cause | Fix |
|-------|-------|-----|
| `Invalid email or password` on login | `package.json` proxy pointed to `localhost:8000` which resolves to the frontend container itself inside Docker | Added `src/setupProxy.js` using `REACT_APP_PROXY_TARGET=http://backend:8000` |
| `pydantic-settings` ValidationError on startup | Old `class Config` inner class not supported in pydantic-settings v2 | Migrated to `model_config = SettingsConfigDict(extra="ignore")` |
| `bcrypt` error when hashing passwords | `passlib 1.7.4` incompatible with `bcrypt ≥ 4.1` | Pinned `bcrypt==4.0.1` in `requirements.txt` |
| `docker compose` warning on every command | Obsolete `version: '3.9'` key | Removed from `docker-compose.yml` |
