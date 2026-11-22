# NagaraAI — Codebase Reference

Complete file-by-file description of every file and folder in the project: its purpose, what it exports, its dependencies, which other files depend on it, and how it fits into the overall application workflow.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Application Workflow](#3-application-workflow)
4. [Root Files](#4-root-files)
5. [Backend — `backend/`](#5-backend--backend)
   - [Configuration & Bootstrap](#51-configuration--bootstrap)
   - [Data Layer](#52-data-layer)
   - [Business Logic](#53-business-logic)
   - [API Routes](#54-api-routes)
   - [Tests](#55-tests)
6. [Frontend — `frontend/`](#6-frontend--frontend)
   - [Entry Points](#61-entry-points)
   - [API Client](#62-api-client)
   - [Auth Context](#63-auth-context)
   - [Pages](#64-pages)
   - [Components](#65-components)
7. [Kubernetes — `k8s/`](#7-kubernetes--k8s)
   - [Cluster Config](#71-cluster-config)
   - [Secrets](#72-secrets)
   - [PostgreSQL](#73-postgresql)
   - [Backend](#74-backend)
   - [Frontend](#75-frontend)
   - [Ingress](#76-ingress)
8. [Dependency Graph](#8-dependency-graph)
9. [Environment Variables Reference](#9-environment-variables-reference)
10. [Database Schema](#10-database-schema)

---

## 1. Project Overview

**NagaraAI** is a full-stack civic issue management platform for Bengaluru. Citizens report problems (potholes, garbage, flooding), which are automatically classified by IBM watsonx.ai (or a local rule-based fallback). Ward officers, field officers, and commissioners track, dispatch, and analyse resolution in real time through a role-adaptive single-page application.

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Recharts, Leaflet, Axios |
| Backend API | FastAPI 0.111, Python 3.12 |
| ORM | SQLAlchemy 2.0, Alembic 1.13 |
| Database | PostgreSQL 16 (Docker) / SQLite (tests) |
| AI | IBM watsonx.ai Granite-13B + rule-based fallback |
| Auth | JWT (python-jose + bcrypt via passlib) |
| Infrastructure | Docker Compose 3.9 |
| Testing | pytest, pytest-asyncio, aiosqlite |

---

## 2. Repository Layout

```
nagaraai/
├── docker-compose.yml          # Orchestrates all 4 services (db, backend, frontend, test)
├── README.md                   # Quick-start guide
├── CODEBASE.md                 # ← this file
│
├── backend/
│   ├── Dockerfile              # Production backend image (uvicorn)
│   ├── Dockerfile.test         # Test runner image (pytest, SQLite)
│   ├── pytest.ini              # pytest config — testpaths + asyncio_mode
│   ├── requirements.txt        # Python runtime + test dependencies
│   ├── seed.py                 # One-time DB population script
│   ├── .env.example            # Template for secrets
│   ├── .env                    # Local secrets (gitignored)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app factory + CORS
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── database.py         # SQLAlchemy engine + session
│   │   ├── models.py           # ORM models + enums
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── auth.py             # JWT + password hashing + guards
│   │   ├── watsonx.py          # AI classifier (watsonx + local fallback)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py         # POST /api/auth/register|login, GET /me
│   │       ├── complaints.py   # CRUD /api/complaints/
│   │       ├── wards.py        # GET /api/wards/
│   │       └── analytics.py    # GET /api/analytics/*
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py              # pytest fixtures + test helpers
│       ├── test_health.py           # /health + OpenAPI smoke tests
│       ├── test_auth.py             # Register / Login / /me tests
│       ├── test_complaints.py       # Full complaint lifecycle tests
│       ├── test_wards_analytics.py  # Wards + analytics endpoint tests
│       └── test_watsonx.py          # AI classifier unit tests
│
├── frontend/
│   ├── Dockerfile              # Dev-server image (npm start, CRA)
│   ├── Dockerfile.k8s          # Production multi-stage image (Node build → Nginx)
│   ├── package.json            # npm dependencies + scripts
│   └── src/
│       ├── index.js            # React DOM entry point
│       ├── index.css           # Global CSS variables + base styles
│       ├── App.js              # Router root + auth-gated routes
│       ├── api.js              # Axios instance + interceptors
│       ├── context/
│       │   └── AuthContext.js  # Auth state (user, login, logout)
│       ├── pages/
│       │   ├── Login.js        # Login form page
│       │   ├── Register.js     # Registration form page
│       │   ├── Dashboard.js    # City analytics + charts
│       │   ├── Complaints.js   # Issue list + filters + actions
│       │   └── WardMap.js      # Leaflet choropleth risk map
│       └── components/
│           ├── AppShell.js         # Authenticated layout wrapper + sub-router
│           ├── Sidebar.js          # Role-adaptive nav + user chip
│           ├── ReportModal.js      # Citizen complaint submission form
│           └── ComplaintDetail.js  # Complaint detail panel + status updates
│
└── k8s/                        # Kubernetes manifests (minikube / kind / skaffold)
    ├── namespace.yaml           # nagaraai namespace definition
    ├── kind-config.yaml         # kind cluster with ingress port mappings
    ├── skaffold.yaml            # Skaffold dev-loop config
    ├── README.md                # Kubernetes deployment guide
    ├── secrets/
    │   └── secrets.yaml         # Base64-encoded DB creds + JWT secret
    ├── postgres/
    │   ├── pvc.yaml             # 1 Gi PersistentVolumeClaim
    │   ├── deployment.yaml      # postgres:16-alpine pod + readiness probe
    │   └── service.yaml         # ClusterIP postgres-svc:5432
    ├── backend/
    │   ├── deployment.yaml      # FastAPI pod + initContainer + health probes
    │   └── service.yaml         # ClusterIP backend-svc:8000
    ├── frontend/
    │   ├── deployment.yaml      # Nginx pod + ConfigMap nginx proxy config
    │   └── service.yaml         # NodePort frontend-svc:3000 → host:30080
    └── ingress/
        └── ingress.yaml         # nginx-ingress: /api → backend, / → frontend
```

---

## 3. Application Workflow

### Request lifecycle — filing a complaint

```
Browser (Citizen)
  └─→ ReportModal.js          POST /api/complaints/
        └─→ api.js            attaches Bearer token
              └─→ FastAPI backend
                    ├─→ auth.py::get_current_user()   validates JWT
                    ├─→ watsonx.py::classify_with_watsonx()
                    │         ├─ if WATSONX_API_KEY set → IBM Granite-13B
                    │         └─ else → classify_complaint_local()
                    ├─→ models.Complaint  (created in DB)
                    └─→ schemas.ComplaintOut  (returned to browser)
```

### Auth lifecycle

```
Login.js  POST /api/auth/login
  └─→ routes/auth.py::login()
        └─→ auth.py::verify_password() + create_access_token()
              └─→ Token { access_token, user }
                    └─→ AuthContext.js::login()
                          └─→ localStorage["token"] + localStorage["user"]
                                └─→ api.js interceptor auto-injects header
```

### Role-based view scoping

| Role | Complaint list scope | Sidebar label |
|---|---|---|
| `citizen` | Only their own reports | "My Reports" |
| `field_officer` | Only assigned to them | "My Tasks" |
| `ward_officer` | All in their ward | "Ward Issues" |
| `commissioner` | All city-wide | "All Issues" |

---

## 4. Root Files

---

### `docker-compose.yml`

**Purpose:** Defines and connects all four services (db, backend, frontend, test).
**Used by:** `docker compose up`, CI pipelines.

| Service | Image / Build | Ports | Key env vars | Depends on |
|---|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | — |
| `backend` | `./backend/Dockerfile` | 8000 | `DATABASE_URL`, `SECRET_KEY`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID` | `db` (healthy) |
| `frontend` | `./frontend/Dockerfile` | 3000 | `REACT_APP_API_URL` | `backend` |
| `test` | `./backend/Dockerfile.test` | — | `DATABASE_URL=sqlite:///./test.db`, `SECRET_KEY=test-secret-key` | — (profile: `test`) |

The `test` service uses Docker profile `test` — only started with:
```bash
docker compose --profile test up test
```
The `db` service uses a named volume `pgdata` for data persistence across container restarts.

---

### `README.md`

**Purpose:** Quick-start guide, project structure overview, demo logins, API reference table, tech-stack summary. The human-readable entry point for new developers.

---

## 5. Backend — `backend/`

---

### 5.1 Configuration & Bootstrap

---

#### `backend/Dockerfile`

**Purpose:** Builds the production Python image for the backend service.
**Base image:** `python:3.12-slim`
**Steps:**
1. Sets `WORKDIR /app`
2. Copies and installs `requirements.txt` (layer-cached)
3. Copies source code
4. Exposes port `8000`
5. Default `CMD`: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

> In `docker-compose.yml` the CMD is **overridden** to add `--reload` for hot-reloading during development.

**Depends on:** `requirements.txt`, `app/`
**Used by:** `docker-compose.yml` → `backend` service, `k8s/backend/deployment.yaml`

---

#### `backend/Dockerfile.test`

**Purpose:** Dedicated image for running the pytest test suite inside Docker. Bakes in SQLite environment variables so no external database is needed.
**Base image:** `python:3.12-slim`
**Key differences from `Dockerfile`:**
- Sets `ENV DATABASE_URL=sqlite:///./test.db` and `ENV SECRET_KEY=test-secret-key` at build time
- `CMD ["pytest", "-v", "--tb=short"]` — runs tests immediately on container start

**Run the test suite:**
```bash
# Using the docker-compose test service (profile)
docker compose --profile test run --rm test

# Or build and run standalone
docker build -f backend/Dockerfile.test -t nagaraai-test ./backend
docker run --rm nagaraai-test
```

**Depends on:** `requirements.txt`, `app/`, `tests/`
**Used by:** `docker-compose.yml` → `test` service

---

#### `backend/pytest.ini`

**Purpose:** Configures pytest for the project. Two settings:

```ini
[pytest]
testpaths = tests        # only look in the tests/ directory
asyncio_mode = auto      # treat all async test functions as asyncio without @pytest.mark.asyncio
```

The `asyncio_mode = auto` is required by `pytest-asyncio 0.23+` to auto-collect async tests in `test_watsonx.py`.

**Used by:** `pytest` CLI, `Dockerfile.test`

---

#### `backend/requirements.txt`

**Purpose:** Pins all Python runtime and test dependencies.

| Package | Version | Role |
|---|---|---|
| `fastapi` | 0.111.0 | Web framework |
| `uvicorn[standard]` | 0.29.0 | ASGI server |
| `sqlalchemy` | 2.0.30 | ORM + query builder |
| `alembic` | 1.13.1 | Database migrations |
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver |
| `pydantic` | 2.7.1 | Data validation / serialisation |
| `pydantic-settings` | 2.2.1 | Settings from `.env` |
| `python-jose[cryptography]` | 3.3.0 | JWT encode/decode |
| `passlib[bcrypt]` | 1.7.4 | Password hashing |
| `python-multipart` | 0.0.9 | Form data parsing (FastAPI) |
| `httpx` | 0.27.0 | Async HTTP client for watsonx |
| `python-dotenv` | 1.0.1 | `.env` file loading |
| `pytest` | 8.2.2 | Test runner |
| `pytest-asyncio` | 0.23.7 | Async test support |
| `aiosqlite` | 0.20.0 | Async SQLite driver for tests |

**Used by:** `Dockerfile` (COPY + pip install), all Python source files.

---

#### `backend/.env.example`

**Purpose:** Documents all required environment variables with safe placeholder values. Committed to version control. Never contains real secrets.

**Copy to `.env` before running:** `cp backend/.env.example backend/.env`

**Variables defined:**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection string |
| `SECRET_KEY` | JWT signing secret — **must be changed in production** |
| `ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL (default: `1440` = 24 h) |
| `WATSONX_API_KEY` | IBM Cloud API key — leave blank to use local classifier |
| `WATSONX_PROJECT_ID` | watsonx project ID |
| `WATSONX_URL` | watsonx endpoint (default: `us-south`) |

**Depended on by:** `app/config.py`

---

#### `backend/app/config.py`

**Purpose:** Single source of truth for all runtime configuration. Reads from environment variables (and `.env` file via `python-dotenv`).  
**Exports:** `settings` — a singleton `Settings` instance available app-wide.

```python
settings.DATABASE_URL           # str
settings.SECRET_KEY             # str
settings.ALGORITHM              # str  (default: "HS256")
settings.ACCESS_TOKEN_EXPIRE_MINUTES  # int (default: 1440)
settings.WATSONX_API_KEY        # str  (empty = fallback mode)
settings.WATSONX_PROJECT_ID     # str
settings.WATSONX_URL            # str
```

**Dependencies:** `pydantic-settings`  
**Used by:** `app/database.py`, `app/auth.py`, `app/watsonx.py`

---

#### `backend/app/database.py`

**Purpose:** Creates the SQLAlchemy engine and session factory. Provides the `get_db()` dependency injected into every route that needs a database session.  
**Exports:**
- `engine` — SQLAlchemy `Engine` (used by `Base.metadata.create_all`)
- `SessionLocal` — `sessionmaker` factory
- `Base` — `declarative_base()` that all ORM models inherit from
- `get_db()` — FastAPI dependency; yields a DB session and closes it after the request

**Dependencies:** `app/config.py` (for `DATABASE_URL`)  
**Used by:** `app/main.py`, `app/models.py`, `app/auth.py`, all route files, `seed.py`, `tests/conftest.py`

---

#### `backend/app/main.py`

**Purpose:** FastAPI application factory. Creates the `app` object, registers CORS middleware, mounts all routers, and auto-creates database tables on startup.  
**Exports:** `app` — the FastAPI application (referenced by uvicorn as `app.main:app`)

**What it does on import:**
1. `Base.metadata.create_all(bind=engine)` — creates all ORM tables if they don't exist
2. Adds `CORSMiddleware` with `allow_origins=["*"]` (suitable for development)
3. Registers four routers: `auth`, `complaints`, `wards`, `analytics`
4. Registers `GET /health` — returns `{"status": "ok", "service": "NagaraAI"}`

**Dependencies:** `app/database.py`, `app/routes/auth.py`, `app/routes/complaints.py`, `app/routes/wards.py`, `app/routes/analytics.py`  
**Used by:** `uvicorn` process, `tests/conftest.py` (via `TestClient`)

---

### 5.2 Data Layer

---

#### `backend/app/models.py`

**Purpose:** Defines the full PostgreSQL schema as SQLAlchemy ORM classes. This is the single source of truth for the database structure.

**Enums:**

| Enum | Values |
|---|---|
| `UserRole` | `citizen`, `field_officer`, `ward_officer`, `commissioner` |
| `IssueCategory` | `garbage_black_spot`, `cd_waste`, `waterlogging`, `drain_blockage`, `groundwater`, `other` |
| `IssuePriority` | `low`, `medium`, `high`, `critical` |
| `IssueStatus` | `open`, `assigned`, `in_progress`, `resolved`, `closed`, `escalated` |

**Tables / ORM classes:**

| Class | Table | Key columns | Relationships |
|---|---|---|---|
| `User` | `users` | `id`, `name`, `email`, `hashed_password`, `role`, `ward_id`, `is_active` | `ward` (Ward), `complaints` (reporter), `assigned_complaints` (assignee) |
| `Ward` | `wards` | `id`, `name`, `zone`, `population`, `flood_risk_score`, `cleanliness_score` | `users`, `complaints`, `contractors` |
| `Contractor` | `contractors` | `id`, `name`, `ward_id`, `compliance_score`, `total_assigned`, `total_resolved` | `ward`, `complaints` |
| `Complaint` | `complaints` | `id`, `ticket_id`, `title`, `category`, `priority`, `status`, `latitude`, `longitude`, `ai_classification`, `ai_confidence`, `ai_summary`, `reporter_id`, `assignee_id`, `ward_id`, `contractor_id`, `sla_deadline`, `resolved_at`, `citizen_rating` | `reporter`, `assignee`, `ward`, `contractor`, `updates` |
| `ComplaintUpdate` | `complaint_updates` | `id`, `complaint_id`, `updated_by`, `status`, `note` | `complaint` |

**Dependencies:** `app/database.py` (for `Base`)  
**Used by:** `app/schemas.py`, `app/auth.py`, all route files, `seed.py`, `tests/`

---

#### `backend/app/schemas.py`

**Purpose:** Pydantic models for request validation and response serialisation. Keeps ORM models separate from the API contract.

**Schema groups:**

| Schema | Direction | Used by |
|---|---|---|
| `UserCreate` | request (register) | `routes/auth.py` |
| `UserLogin` | request (login) | `routes/auth.py` |
| `UserOut` | response | `routes/auth.py`, `Token` |
| `Token` | response (login) | `routes/auth.py` |
| `WardOut` | response | `routes/wards.py` |
| `ContractorOut` | response | (analytics, internal) |
| `ComplaintCreate` | request (create complaint) | `routes/complaints.py` |
| `ComplaintUpdate` | request (patch complaint) | `routes/complaints.py` |
| `ComplaintRating` | request (rate complaint) | `routes/complaints.py` |
| `ComplaintUpdateOut` | response (embedded in `ComplaintOut`) | `routes/complaints.py` |
| `ComplaintOut` | response | `routes/complaints.py` |
| `CityStats` | response | `routes/analytics.py` |
| `WardStats` | response | `routes/wards.py` |

**Dependencies:** `app/models.py` (imports enums), `pydantic`  
**Used by:** all route files

---

#### `backend/seed.py`

**Purpose:** One-time database population script. Creates demo wards, contractors, and four role-based users. Safe to re-run (idempotent — checks for existing records before inserting).

**What it inserts:**

| Type | Count | Details |
|---|---|---|
| Wards | 8 | Jayanagar, Malleswaram, Whitefield, Koramangala, Hebbal, BTM Layout, Yelahanka, Marathahalli — with realistic flood/cleanliness scores |
| Contractors | 5 | CleanBengaluru Pvt Ltd, SwachhCity Services, GreenWaste Solutions, BBMP Direct Team A, EcoManage Corp |
| Users | 4 | citizen@demo.com, field@demo.com, ward@demo.com, commissioner@demo.com — all password `demo1234` |

**Run command:**
```bash
# Docker
docker compose exec backend python seed.py

# Manual
python seed.py   # from backend/ with venv active
```

**Dependencies:** `app/database.py`, `app/models.py`, `app/auth.py` (for `hash_password`)  
**Used by:** developer/CI setup only — not imported by any application code

---

### 5.3 Business Logic

---

#### `backend/app/auth.py`

**Purpose:** All authentication and authorisation logic. Provides reusable FastAPI dependencies for route protection.

**Exports:**

| Symbol | Type | Purpose |
|---|---|---|
| `hash_password(password)` | function | bcrypt-hashes a plain-text password |
| `verify_password(plain, hashed)` | function | verifies a plain password against a bcrypt hash |
| `create_access_token(data, expires_delta)` | function | creates a signed JWT with `sub` (user id) and `role` claims |
| `get_current_user(token, db)` | FastAPI dependency | decodes JWT, looks up user in DB, raises 401 if invalid |
| `require_role(*roles)` | dependency factory | returns a dependency that raises 403 if user's role is not in `roles` |
| `pwd_context` | CryptContext | passlib bcrypt context |
| `oauth2_scheme` | OAuth2PasswordBearer | extracts `Authorization: Bearer <token>` header |

**Dependencies:** `app/config.py` (SECRET_KEY, ALGORITHM), `app/models.py`, `app/database.py`, `python-jose`, `passlib`  
**Used by:** `routes/auth.py`, `routes/complaints.py`, `routes/analytics.py`, `seed.py`

---

#### `backend/app/watsonx.py`

**Purpose:** AI classification engine. Routes complaint text through IBM watsonx.ai (Granite-13B) when credentials are present, otherwise uses a deterministic rule-based fallback. This is the only file that makes external HTTP calls.

**Exports:**

| Symbol | Type | Purpose |
|---|---|---|
| `CATEGORY_KEYWORDS` | dict | keyword → category mapping used by local classifier |
| `SLA_HOURS` | dict | priority → SLA deadline in hours (`critical=4`, `high=24`, `medium=72`, `low=168`) |
| `classify_complaint_local(title, description)` | function | synchronous rule-based classifier; always returns a valid result dict |
| `classify_with_watsonx(title, description)` | async function | tries watsonx first; falls back to local on any error or missing credentials |

**Return dict shape:**
```python
{
  "category": str,     # one of IssueCategory values
  "priority": str,     # one of IssuePriority values
  "confidence": float, # 0.0–1.0
  "summary": str,      # one-sentence description
}
```

**watsonx flow:**
1. POST to `https://iam.cloud.ibm.com/identity/token` to exchange API key for IAM token
2. POST to `{WATSONX_URL}/ml/v1/text/generation` with `ibm/granite-13b-instruct-v2`
3. Parse JSON from generated text with regex
4. On any exception → silently fall back to local classifier

**Dependencies:** `app/config.py`, `httpx`  
**Used by:** `routes/complaints.py`  
**Tested by:** `tests/test_watsonx.py`

---

### 5.4 API Routes

All routers are mounted in `app/main.py`. Every endpoint (except `/health` and `/api/wards/`) requires a valid JWT.

---

#### `backend/app/routes/auth.py`

**Prefix:** `/api/auth`  
**Purpose:** User registration, login, and profile retrieval.

| Method | Path | Auth | Request | Response | Description |
|---|---|---|---|---|---|
| `POST` | `/register` | None | `UserCreate` | `UserOut` (201) | Creates a new user; rejects duplicate emails |
| `POST` | `/login` | None | `UserLogin` | `Token` | Validates credentials; returns JWT + user object |
| `GET` | `/me` | Required | — | `UserOut` | Returns the currently authenticated user |

**Dependencies:** `app/database.py`, `app/models.py`, `app/schemas.py`, `app/auth.py`

---

#### `backend/app/routes/complaints.py`

**Prefix:** `/api/complaints`  
**Purpose:** Full complaint lifecycle — creation with AI triage, role-scoped listing, status updates, and citizen ratings.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/` | Required | Creates complaint; calls `classify_with_watsonx`, auto-assigns SLA, auto-assigns best contractor |
| `GET` | `/` | Required | Lists complaints scoped by role (citizen=own, field=assigned, ward=ward, commissioner=all); supports `?status=`, `?category=`, `?ward_id=`, `?limit=`, `?offset=` |
| `GET` | `/{id}` | Required | Gets a single complaint by ID |
| `PATCH` | `/{id}` | Required | Updates status/priority/assignee/contractor; logs `ComplaintUpdate` on status change; recalculates contractor compliance on `resolved` |
| `POST` | `/{id}/rate` | Required | Citizen submits 1–5 star rating |

**Side effects on status change to `resolved`:**
- Sets `complaint.resolved_at`
- Increments `contractor.total_resolved`
- Recalculates `contractor.compliance_score = (total_resolved / total_assigned) * 100`

**Dependencies:** `app/database.py`, `app/models.py`, `app/schemas.py`, `app/auth.py`, `app/watsonx.py`

---

#### `backend/app/routes/wards.py`

**Prefix:** `/api/wards`  
**Purpose:** Provides ward data for dropdowns and map rendering. No authentication required (public data).

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `GET` | `/` | None | `list[WardOut]` | All wards with risk scores |
| `GET` | `/{ward_id}/stats` | None | `WardStats` | Open/resolved counts + risk scores for a ward |

**Dependencies:** `app/database.py`, `app/models.py`, `app/schemas.py`

---

#### `backend/app/routes/analytics.py`

**Prefix:** `/api/analytics`  
**Purpose:** Aggregated city-level metrics for the Dashboard and commissioner view. All endpoints require authentication.

| Method | Path | Response | Description |
|---|---|---|---|
| `GET` | `/city` | `CityStats` | Total complaints, open count, resolved today, avg resolution hours, top category, high-risk wards (flood_risk ≥ 7.0) |
| `GET` | `/ward-heatmap` | `list[dict]` | Per-ward open complaints + flood/cleanliness scores for the bar chart |
| `GET` | `/contractors` | `list[dict]` | Contractor leaderboard sorted by `compliance_score` descending, includes computed `resolution_rate` |

**Dependencies:** `app/database.py`, `app/models.py`, `app/schemas.py`, `app/auth.py`

---

#### `backend/app/routes/__init__.py`

**Purpose:** Empty package marker. Makes `app/routes/` a Python package so relative imports work.

---

#### `backend/app/__init__.py`

**Purpose:** Empty package marker. Makes `app/` a Python package.

---

### 5.5 Tests

The test suite uses **SQLite in-memory** (via `aiosqlite`) instead of PostgreSQL, so no database server is needed to run tests.

---

#### `backend/tests/conftest.py`

**Purpose:** Shared pytest fixtures and helper functions. The authoritative test infrastructure file.

**What it sets up:**
- Patches `DATABASE_URL` to `sqlite:///./test.db` before anything else imports `app.database`
- Creates a `TestingSessionLocal` and overrides `get_db` via `app.dependency_overrides`
- Creates all tables once per session (`create_tables` fixture, `scope="session"`, `autouse=True`)
- Drops all tables and deletes `test.db` after the session ends

**Fixtures:**

| Fixture | Scope | Purpose |
|---|---|---|
| `create_tables` | session, autouse | Creates + tears down all SQLite tables |
| `db` | function | Provides a raw DB session |
| `client` | session | FastAPI `TestClient` with overridden DB |

**Helper functions (importable by test modules):**

| Function | Purpose |
|---|---|
| `register_user(client, email, password, name, role)` | POST /api/auth/register |
| `login_user(client, email, password)` | POST /api/auth/login |
| `auth_headers(client, email, password)` | Returns `{"Authorization": "Bearer <token>"}` |

**Dependencies:** `app/database.py`, `app/main.py`, `pytest`, `sqlalchemy`, `fastapi.testclient`  
**Used by:** all test files

---

#### `backend/tests/test_health.py`

**Purpose:** Smoke tests for the app bootstrap and OpenAPI schema.  
**Tests:** `/health` returns 200 + correct body, `/docs` is accessible, `/openapi.json` contains expected paths.  
**Covers:** `app/main.py`

---

#### `backend/tests/test_auth.py`

**Purpose:** Full register/login/`/me` lifecycle tests.  
**Tests:** successful registration, duplicate email rejection, role assignment, missing fields (422), login success/wrong-password/unknown-email, JWT format validation, authenticated vs unauthenticated `/me`.  
**Covers:** `routes/auth.py`, `app/auth.py`

---

#### `backend/tests/test_complaints.py`

**Purpose:** Full complaint lifecycle tests. All `classify_with_watsonx` calls are patched with `AsyncMock` returning a fixed `AI_RESULT` dict so no network calls are made.  
**Tests:** create (success, unauthenticated, missing title, unique ticket IDs), list (role scoping, pagination), get (existing, 404), update (status, resolve, resolved_at set, 404), rate (success, out-of-range 400).  
**Covers:** `routes/complaints.py`, `app/watsonx.py` (mocked)

---

#### `backend/tests/test_wards_analytics.py`

**Purpose:** Tests for ward and analytics endpoints. Inserts a real ward directly into the SQLite DB via fixture.  
**Tests:** `GET /api/wards/` returns seeded ward, ward stats structure, city stats requires auth, city stats shape, all counts non-negative, ward-heatmap includes seeded ward, contractor leaderboard is a list.  
**Covers:** `routes/wards.py`, `routes/analytics.py`

---

#### `backend/tests/test_watsonx.py`

**Purpose:** Unit tests for the AI classifier in complete isolation (no HTTP calls, no DB).  
**Tests:**
- `TestLocalClassifier` (13 tests): keyword → category mapping for all 5 categories, `other` fallback, priority keywords (critical/high/low/medium default), summary content, confidence cap at 1.0, required keys present
- `TestSLAHours` (5 tests): SLA values and coverage
- `TestWatsonxDispatcher` (2 async tests): falls back to local when no credentials; falls back on network error (httpx patched)

**Covers:** `app/watsonx.py`

---

#### `backend/tests/__init__.py`

**Purpose:** Empty package marker. Makes `tests/` a Python package (required for `from tests.conftest import ...`).

---

## 6. Frontend — `frontend/`

---

#### `backend/.env` *(gitignored)*

**Purpose:** Local runtime secrets. Created by copying `.env.example`. Never committed.
**Used by:** `app/config.py` via `pydantic-settings` `env_file = ".env"`

---

### `frontend/Dockerfile`

**Purpose:** Builds the **development** React image. Runs the Create React App dev server with hot-reload.
**Base image:** `node:20-alpine`
**Steps:** installs deps (`npm install`), copies source, exposes 3000, runs `npm start`.

> This image is for `docker compose` local development **only**. Do not use it for Kubernetes or production — use `Dockerfile.k8s` instead.

**Used by:** `docker-compose.yml` → `frontend` service

---

### `frontend/Dockerfile.k8s`

**Purpose:** Multi-stage **production** image used by the Kubernetes manifests. Produces a minimal nginx-based image serving the compiled React bundle.

**Stage 1 — `builder` (`node:20-alpine`):**
1. `npm install --frozen-lockfile` — reproducible install
2. `npm run build` — compiles React to `build/` (static HTML/JS/CSS)

**Stage 2 — `nginx:1.27-alpine`:**
1. Removes default nginx config (`/etc/nginx/conf.d/default.conf`) — the real config is injected via a Kubernetes ConfigMap at runtime
2. Copies `build/` to `/usr/share/nginx/html`
3. Exposes port `3000`

**Key design:** `REACT_APP_API_URL` is intentionally unset during build so the app uses relative `/api` URLs. The nginx ConfigMap in `k8s/frontend/deployment.yaml` proxies `/api/*` to `backend-svc:8000`.

**Depends on:** `package.json`, `src/`
**Used by:** `k8s/frontend/deployment.yaml`, `k8s/skaffold.yaml`

---

### `frontend/package.json`

**Purpose:** Declares npm dependencies, scripts, and browser targets.

**Key dependencies:**

| Package | Purpose |
|---|---|
| `react` + `react-dom` | UI framework |
| `react-router-dom` | Client-side routing |
| `axios` | HTTP client |
| `leaflet` + `react-leaflet` | Interactive map |
| `recharts` | Bar/Pie charts on Dashboard |
| `react-hot-toast` | Toast notifications |
| `lucide-react` | Icon set |
| `react-scripts` | CRA build toolchain |

**Scripts:**
- `npm start` — development server on port 3000 with hot-reload
- `npm run build` — production static build to `frontend/build/`

**Proxy:** `"proxy": "http://localhost:8000"` — all `/api/*` requests from the dev server are proxied to the backend, so CORS is not an issue in development.

---

### 6.1 Entry Points

---

#### `frontend/src/index.js`

**Purpose:** React DOM entry point. Mounts `<App />` into `#root` in `public/index.html`.  
**Used by:** webpack (via CRA), nothing else imports it.

---

#### `frontend/src/index.css`

**Purpose:** Global CSS — custom properties (colour tokens, spacing), base resets, layout classes (`.app-shell`, `.sidebar`, `.main-content`, `.stat-card`, `.card`, `.table-wrap`, `.spinner`), and responsive utilities.  
**Used by:** `index.js` (single global import)

---

#### `frontend/src/App.js`

**Purpose:** Root React component. Wraps the entire app in `BrowserRouter`, `AuthProvider`, and the `Toaster`. Defines the top-level route guard:

- `/login` → `<Login />` (redirects to `/` if already logged in)
- `/register` → `<Register />` (redirects to `/` if already logged in)
- `/*` → `<AppShell />` (itself redirects to `/login` if not authenticated)

**Dependencies:** `react-router-dom`, `react-hot-toast`, `context/AuthContext`, `components/AppShell`, `pages/Login`, `pages/Register`  
**Used by:** `index.js`

---

### 6.2 API Client

---

#### `frontend/src/api.js`

**Purpose:** Single Axios instance used by all pages and components. Centralises the base URL and auth token injection.

**Configuration:**
- `baseURL: '/api'` — all calls are relative (e.g., `api.get('/complaints/')` → `GET /api/complaints/`)
- **Request interceptor:** reads `localStorage["token"]` and sets `Authorization: Bearer <token>` on every request
- **Response interceptor:** on `401 Unauthorized`, clears localStorage and redirects to `/login`

**Dependencies:** `axios`  
**Used by:** `pages/Dashboard.js`, `pages/Complaints.js`, `pages/WardMap.js`, `pages/Login.js`, `pages/Register.js`, `components/ReportModal.js`, `components/ComplaintDetail.js`

---

### 6.3 Auth Context

---

#### `frontend/src/context/AuthContext.js`

**Purpose:** Global React context for authentication state. Persists across page refreshes via `localStorage`.

**Exports:**
- `AuthProvider` — wraps the app; provides `{ user, login, logout }` to all descendants
- `useAuth()` — hook to consume the context

**State:**
- `user` — parsed `UserOut` object (or `null`); initialised from `localStorage["user"]`

**Methods:**
- `login(userData, token)` — saves to localStorage + updates state
- `logout()` — clears localStorage + sets `user = null`

**Used by:** `App.js`, `components/AppShell.js`, `components/Sidebar.js`, `pages/Dashboard.js`

---

### 6.4 Pages

---

#### `frontend/src/pages/Login.js`

**Purpose:** Login form. On success, calls `AuthContext.login()` and navigates to `/`.  
**API call:** `POST /api/auth/login` via `api.js`  
**Dependencies:** `api.js`, `context/AuthContext`, `react-router-dom`, `react-hot-toast`

---

#### `frontend/src/pages/Register.js`

**Purpose:** Registration form with role and ward selection.  
**API calls:** `GET /api/wards/` (to populate ward dropdown), `POST /api/auth/register`  
**Dependencies:** `api.js`, `react-router-dom`, `react-hot-toast`

---

#### `frontend/src/pages/Dashboard.js`

**Purpose:** City analytics overview. Displays 6 KPI stat cards, a grouped bar chart (ward risk + open complaints), a pie chart (issue category breakdown), and a contractor compliance leaderboard table.

**API calls (parallel `Promise.all`):**
- `GET /api/analytics/city` → `CityStats`
- `GET /api/analytics/ward-heatmap` → ward risk array
- `GET /api/analytics/contractors` → contractor leaderboard

**Dependencies:** `api.js`, `context/AuthContext`, `recharts`  
**Child components:** `StatCard` (inline)

---

#### `frontend/src/pages/Complaints.js`

**Purpose:** Issue list with filters, sorting, and action buttons. Citizens see "Report New Issue" button that opens `ReportModal`. Officers see status update and assign controls. Clicking a row opens `ComplaintDetail`.

**API calls:** `GET /api/complaints/` (with filter params), `PATCH /api/complaints/{id}`  
**Dependencies:** `api.js`, `context/AuthContext`, `components/ReportModal`, `components/ComplaintDetail`, `react-hot-toast`

---

#### `frontend/src/pages/WardMap.js`

**Purpose:** Leaflet choropleth map of Bengaluru wards. Colour-codes wards by flood risk score. Clicking a ward shows a popup with open complaint count and cleanliness score.

**API calls:** `GET /api/analytics/ward-heatmap`  
**Dependencies:** `api.js`, `leaflet`, `react-leaflet`

> Uses hardcoded GeoJSON polygon coordinates for the 8 seeded Bengaluru wards.

---

### 6.5 Components

---

#### `frontend/src/components/AppShell.js`

**Purpose:** Authenticated layout wrapper. Renders `<Sidebar />` on the left and a `<div className="main-content">` on the right. Contains the page-level topbar (page title + "Powered by IBM watsonx.ai" badge) and the inner `<Routes>` for the three main pages.  
Redirects to `/login` if `user` is null.

**Inner routes:**
- `/` → `Dashboard`
- `/complaints` → `Complaints`
- `/map` → `WardMap`
- `*` → redirect to `/`

**Dependencies:** `context/AuthContext`, `components/Sidebar`, `pages/Dashboard`, `pages/Complaints`, `pages/WardMap`  
**Used by:** `App.js`

---

#### `frontend/src/components/Sidebar.js`

**Purpose:** Left navigation sidebar. Renders role-specific nav items (each role gets a different label for the same routes). Shows user avatar (first letter of name), full name, role badge, and a logout button.

**Role → nav label mapping:**
- `citizen`: Dashboard, My Reports, Ward Map
- `field_officer`: Dashboard, My Tasks, Ward Map
- `ward_officer`: Dashboard, Ward Issues, Ward Map
- `commissioner`: City Dashboard, All Issues, City Map

**Dependencies:** `context/AuthContext`, `react-router-dom`  
**Used by:** `components/AppShell.js`

---

#### `frontend/src/components/ReportModal.js`

**Purpose:** Modal dialog for citizens to file a new complaint. Fields: title, description, category (dropdown), address, latitude/longitude, image URL, ward selection.  
On submit, calls `POST /api/complaints/` and shows the AI-generated classification result in a toast.

**Dependencies:** `api.js`, `react-hot-toast`  
**Used by:** `pages/Complaints.js`

---

#### `frontend/src/components/ComplaintDetail.js`

**Purpose:** Side panel / modal showing full complaint details including AI classification metadata, SLA deadline countdown, status history (`updates[]`), and (for officers) status update controls and assignee selection.

**API calls:** `PATCH /api/complaints/{id}` (status update), `POST /api/complaints/{id}/rate` (citizen rating)  
**Dependencies:** `api.js`, `context/AuthContext`, `react-hot-toast`  
**Used by:** `pages/Complaints.js`

---

## 7. Kubernetes — `k8s/`

The `k8s/` directory contains everything needed to deploy NagaraAI on a local Kubernetes cluster (minikube or kind). All manifests target the `nagaraai` namespace.

**Deployment order (applied sequentially):**
```
namespace → secrets → postgres (pvc → deployment → service) → backend → frontend → ingress
```

---

### 7.1 Cluster Config

---

#### `k8s/namespace.yaml`

**Purpose:** Creates the `nagaraai` Kubernetes namespace. All other resources live inside this namespace.
**Apply first** — every other manifest references `namespace: nagaraai`.

---

#### `k8s/kind-config.yaml`

**Purpose:** kind cluster configuration for local Kubernetes development. Configures a single control-plane node with:
- `node-labels: "ingress-ready=true"` — required by the nginx ingress controller
- Three `extraPortMappings`: host port `80` → container `80` (ingress HTTP), host `443` → container `443` (HTTPS), host `30080` → container `30080` (direct NodePort access)

**Used by:** `kind create cluster --name nagaraai --config k8s/kind-config.yaml`

---

#### `k8s/skaffold.yaml`

**Purpose:** Skaffold v2 configuration for an automated build-deploy-watch dev loop. Builds both images, applies all manifests in the correct order, and port-forwards `localhost:3000` → frontend and `localhost:8000` → backend.

**Build artifacts:**

| Image | Context | Dockerfile |
|---|---|---|
| `nagaraai-backend` | `./backend` | `Dockerfile` |
| `nagaraai-frontend` | `./frontend` | `Dockerfile.k8s` (production build) |

**`local.push: false`** — images are built directly into minikube's Docker daemon (no registry needed).

**Usage:**
```bash
# minikube
eval $(minikube docker-env) && skaffold dev --filename k8s/skaffold.yaml

# kind
skaffold dev --filename k8s/skaffold.yaml --default-repo ""
```

---

#### `k8s/README.md`

**Purpose:** Step-by-step Kubernetes deployment guide covering minikube (Option A), kind (Option B), and Skaffold (Option C). Includes useful `kubectl` commands, seed data instructions, secrets rotation, teardown, and an ASCII cluster architecture diagram.

---

### 7.2 Secrets

---

#### `k8s/secrets/secrets.yaml`

**Purpose:** Kubernetes `Secret` resource (`nagaraai-secrets`) holding all sensitive values as base64-encoded strings.

| Key | Decoded value | Used by |
|---|---|---|
| `POSTGRES_USER` | `nagaraai` | postgres pod env |
| `POSTGRES_PASSWORD` | `nagaraai123` | postgres pod env |
| `POSTGRES_DB` | `nagaraai_db` | postgres pod env |
| `DATABASE_URL` | `postgresql://nagaraai:nagaraai123@postgres-svc:5432/nagaraai_db` | backend pod env |
| `SECRET_KEY` | `change-me-in-local-dev` | backend pod env — **must be changed for any real deployment** |
| `WATSONX_API_KEY` | `""` | backend pod env — set your IBM Cloud key to enable AI classification |
| `WATSONX_PROJECT_ID` | `""` | backend pod env |

> Note: the `DATABASE_URL` hostname is `postgres-svc` (the Kubernetes Service name), not `localhost` or `db`.

**To update a secret value:**
```bash
echo -n "new-value" | base64    # get encoded string
# edit secrets.yaml, then:
kubectl apply -f k8s/secrets/secrets.yaml
kubectl -n nagaraai rollout restart deployment/backend
```

---

### 7.3 PostgreSQL

---

#### `k8s/postgres/pvc.yaml`

**Purpose:** 1 Gi `PersistentVolumeClaim` (`postgres-pvc`, `ReadWriteOnce`) for database storage. Uses the cluster's default `StorageClass` (works on both minikube and kind without modification).

**Mounted at:** `/var/lib/postgresql/data` inside the postgres pod.

---

#### `k8s/postgres/deployment.yaml`

**Purpose:** Runs `postgres:16-alpine` as a single-replica Deployment with `strategy: Recreate` (prevents two writers accessing the PVC simultaneously).

**Key config:**
- Credentials injected from `nagaraai-secrets` via `secretKeyRef`
- **readinessProbe:** `pg_isready -U nagaraai -d nagaraai_db` — backend initContainer waits for this
- **livenessProbe:** same command, 30 s initial delay
- Resource limits: `500m` CPU, `512Mi` memory

---

#### `k8s/postgres/service.yaml`

**Purpose:** ClusterIP Service `postgres-svc` exposing port `5432`. Internal DNS name `postgres-svc.nagaraai.svc.cluster.local` is what `DATABASE_URL` in secrets resolves to.

---

### 7.4 Backend

---

#### `k8s/backend/deployment.yaml`

**Purpose:** Runs the FastAPI backend as a single-replica Deployment.

**Key config:**
- **initContainer** (`busybox:1.36`): polls `nc -z postgres-svc 5432` every 2 s until Postgres accepts connections — prevents the backend from crashing before the DB is ready
- `imagePullPolicy: IfNotPresent` — uses the locally loaded image (minikube/kind)
- All env vars (`DATABASE_URL`, `SECRET_KEY`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`) injected from `nagaraai-secrets`
- **readinessProbe:** `GET /health` on port 8000, 10 s initial delay
- **livenessProbe:** `GET /health`, 30 s initial delay
- Resource limits: `500m` CPU, `512Mi` memory

---

#### `k8s/backend/service.yaml`

**Purpose:** ClusterIP Service `backend-svc` exposing port `8000`. Referenced by the frontend nginx proxy config and the ingress rule.

---

### 7.5 Frontend

---

#### `k8s/frontend/deployment.yaml`

**Purpose:** Contains two Kubernetes resources in a single file:

**1 — ConfigMap `frontend-nginx-conf`:** Provides the nginx `default.conf` mounted into the pod. Configures nginx to:
- Listen on port `3000`
- Serve the React static build from `/usr/share/nginx/html`
- Proxy `location /api/` → `http://backend-svc:8000` (passes through all API calls)
- `location /` with `try_files $uri $uri/ /index.html` — enables React client-side routing

**2 — Deployment `frontend`:** Runs `nagaraai-frontend:latest` (built from `Dockerfile.k8s`).
- ConfigMap volume mounted at `/etc/nginx/conf.d/default.conf`
- **readinessProbe:** `GET /` on port 3000
- Resource limits: `200m` CPU, `256Mi` memory

---

#### `k8s/frontend/service.yaml`

**Purpose:** NodePort Service `frontend-svc` exposing port `3000` with `nodePort: 30080`.

- Access via ingress: `http://localhost` (port 80 via nginx-ingress)
- Direct access (no tunnel): `http://localhost:30080`

---

### 7.6 Ingress

---

#### `k8s/ingress/ingress.yaml`

**Purpose:** nginx Ingress resource routing all external traffic to the correct service based on path prefix.

| Path | Type | Backend Service | Description |
|---|---|---|---|
| `/api` | Prefix | `backend-svc:8000` | All API calls go directly to FastAPI |
| `/` | Prefix | `frontend-svc:3000` | Everything else goes to the React frontend |

**Annotations:**
- `proxy-read-timeout: "60"` and `proxy-send-timeout: "60"` — allows for slow watsonx.ai API calls

**Ingress class:** `nginx` — requires the nginx ingress controller installed in the cluster.

---

## 8. Dependency Graph

```
docker-compose.yml
  ├── backend/Dockerfile ──────────────────────────────────────────┐
  │     └── requirements.txt                                       │
  │           └── app/                                             │
  │                 ├── config.py ← .env / environment vars        │
  │                 ├── database.py ← config.py                    │
  │                 ├── models.py ← database.py                    │
  │                 ├── schemas.py ← models.py                     │
  │                 ├── auth.py ← config.py, database.py, models   │
  │                 ├── watsonx.py ← config.py                     │
  │                 ├── main.py ← database.py, routes/*            │
  │                 └── routes/
  │                       ├── auth.py ← database, models, schemas, auth
  │                       ├── complaints.py ← database, models, schemas, auth, watsonx
  │                       ├── wards.py ← database, models, schemas
  │                       └── analytics.py ← database, models, schemas, auth
  │
  ├── backend/Dockerfile.test ────────────────────────────────────┐
  │     └── (same requirements.txt + tests/)                      │
  │           └── tests/conftest.py ← app/main.py, app/database   │
  │
  ├── frontend/Dockerfile (dev server) ─────────────────────────── ┐
  │     └── package.json                                           │
  │           └── src/                                             │
  │                 ├── index.js → App.js                          │
  │                 ├── App.js → AuthContext, AppShell, Login, Register
  │                 ├── api.js (used by all pages + components)    │
  │                 ├── context/AuthContext.js                     │
  │                 ├── pages/
  │                 │     ├── Login.js ← api, AuthContext          │
  │                 │     ├── Register.js ← api                    │
  │                 │     ├── Dashboard.js ← api, AuthContext      │
  │                 │     ├── Complaints.js ← api, AuthContext, ReportModal, ComplaintDetail
  │                 │     └── WardMap.js ← api                     │
  │                 └── components/
  │                       ├── AppShell.js ← AuthContext, Sidebar, pages/*
  │                       ├── Sidebar.js ← AuthContext             │
  │                       ├── ReportModal.js ← api                 │
  │                       └── ComplaintDetail.js ← api, AuthContext│
  │
  ├── frontend/Dockerfile.k8s (production) ────────────────────────┐
  │     └── same src/ → npm run build → nginx static serve         │
  │           └── k8s/frontend/deployment.yaml (ConfigMap nginx conf)
  │
  ├── db (postgres:16-alpine) ─────────────────────────────────────┐
  │     └── pgdata volume (docker) / postgres-pvc (k8s)            │
  │
  └── k8s/
        ├── secrets/secrets.yaml ← all env vars (base64)
        ├── postgres/ ← pvc + deployment + service
        ├── backend/  ← deployment (initContainer) + service
        ├── frontend/ ← deployment (ConfigMap nginx) + service
        └── ingress/  ← nginx ingress rules
```

---

## 9. Environment Variables Reference

| Variable | Service | Required | Default | Purpose |
|---|---|---|---|---|
| `DATABASE_URL` | backend | Yes | `postgresql://nagaraai:nagaraai123@localhost:5432/nagaraai_db` | SQLAlchemy connection string |
| `SECRET_KEY` | backend | **Yes — change in prod** | `dev-secret-key` | JWT signing secret |
| `ALGORITHM` | backend | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | No | `1440` | Token TTL (minutes) |
| `WATSONX_API_KEY` | backend | No | `""` | IBM Cloud API key — empty → local fallback |
| `WATSONX_PROJECT_ID` | backend | No | `""` | watsonx project ID |
| `WATSONX_URL` | backend | No | `https://us-south.ml.cloud.ibm.com` | watsonx regional endpoint |
| `REACT_APP_API_URL` | frontend | No | (unused at runtime) | Informational; proxy in package.json handles routing |
| `POSTGRES_USER` | db | Yes (Docker) | `nagaraai` | PostgreSQL superuser |
| `POSTGRES_PASSWORD` | db | Yes (Docker) | `nagaraai123` | PostgreSQL password |
| `POSTGRES_DB` | db | Yes (Docker) | `nagaraai_db` | PostgreSQL database name |

---

## 10. Database Schema

```
users
  id PK, name, email (unique), phone (unique), hashed_password,
  role ENUM, ward_id FK→wards.id, is_active, created_at

wards
  id PK, name, zone, population,
  flood_risk_score FLOAT, cleanliness_score FLOAT

contractors
  id PK, name, contact, ward_id FK→wards.id,
  compliance_score FLOAT, total_assigned INT, total_resolved INT, created_at

complaints
  id PK, ticket_id (unique), title, description, category ENUM, priority ENUM, status ENUM,
  latitude, longitude, address, image_url,
  ai_classification, ai_confidence, ai_summary,
  reporter_id FK→users.id, assignee_id FK→users.id,
  ward_id FK→wards.id, contractor_id FK→contractors.id,
  sla_deadline, resolved_at, citizen_rating INT(1–5), created_at, updated_at

complaint_updates
  id PK, complaint_id FK→complaints.id, updated_by FK→users.id,
  status ENUM, note TEXT, created_at
```

**Foreign key summary:**

```
users.ward_id              → wards.id
complaints.reporter_id     → users.id
complaints.assignee_id     → users.id
complaints.ward_id         → wards.id
complaints.contractor_id   → contractors.id
contractors.ward_id        → wards.id
complaint_updates.complaint_id → complaints.id
complaint_updates.updated_by   → users.id
```
