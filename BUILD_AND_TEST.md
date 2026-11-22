# NagaraAI — Build & Test Guide

Step-by-step instructions for building, running, and testing every layer of the NagaraAI stack.  
Covers Docker Compose (recommended), standalone Docker, and manual local execution.

> **AI tag:** Every step that involves IBM watsonx.ai classification — directly or through the test suite — is marked **`[AI]`**.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Layout Cheat-Sheet](#2-repository-layout-cheat-sheet)
3. [Environment Variables](#3-environment-variables)
4. [Build — Docker Compose (Full Stack)](#4-build--docker-compose-full-stack)
5. [Build — Standalone Docker (Backend Only)](#5-build--standalone-docker-backend-only)
6. [Build — Manual Local (No Docker)](#6-build--manual-local-no-docker)
7. [Test Suite — Docker (Recommended)](#7-test-suite--docker-recommended)
8. [Test Suite — Manual Local](#8-test-suite--manual-local)
9. [Test File Reference](#9-test-file-reference)
10. [AI Classification in Tests](#10-ai-classification-in-tests)
11. [Enabling Live IBM watsonx.ai](#11-enabling-live-ibm-watsonxai)
12. [Verifying Channel Webhooks](#12-verifying-channel-webhooks)
13. [CI Workflow Reference](#13-ci-workflow-reference)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

### Docker path (recommended — zero local installs needed)

| Tool | Min version | Install |
|---|---|---|
| Docker Desktop | 4.x | https://www.docker.com/products/docker-desktop |

> **Windows note:** Docker Desktop installs to  
> `C:\Users\<you>\AppData\Local\Programs\DockerDesktop\resources\bin\`  
> If `docker` is not in your PATH, prefix every command with the full binary path, or add the directory to PATH:
> ```powershell
> $env:PATH = "C:\Users\$env:USERNAME\AppData\Local\Programs\DockerDesktop\resources\bin;" + $env:PATH
> ```

### Manual path (Python + Node)

| Tool | Min version | Purpose |
|---|---|---|
| Python | 3.12+ | Backend runtime |
| pip | 24+ | Dependency install |
| Node.js | 20+ | Frontend dev server |
| npm | 10+ | Frontend package manager |
| PostgreSQL | 15+ | Production database |

---

## 2. Repository Layout Cheat-Sheet

```
nagaraai/
├── backend/
│   ├── Dockerfile            ← production image
│   ├── Dockerfile.test       ← test-runner image
│   ├── pytest.ini            ← pytest config
│   ├── requirements.txt      ← Python deps (runtime + test)
│   ├── .env.example          ← copy → .env, fill in secrets
│   ├── seed.py               ← demo data loader
│   ├── app/
│   │   ├── main.py           ← FastAPI entry point
│   │   ├── config.py         ← all env vars (pydantic-settings)
│   │   ├── watsonx.py        ← [AI] IBM Granite-13B + local fallback
│   │   ├── channels/         ← 7 channel adapters + dispatcher
│   │   └── routes/           ← 5 API routers
│   └── tests/
│       ├── conftest.py       ← SQLite fixtures, TestClient
│       ├── test_health.py     (4 tests)
│       ├── test_auth.py       (12 tests)
│       ├── test_complaints.py (19 tests)   [AI]
│       ├── test_wards_analytics.py (8 tests)
│       ├── test_watsonx.py    (14 tests)   [AI]
│       └── test_channels.py   (18 tests)   [AI]
├── frontend/
│   ├── Dockerfile            ← CRA dev-server
│   ├── Dockerfile.k8s        ← multi-stage prod (Node → Nginx)
│   └── src/
├── docker-compose.yml        ← db + backend + frontend + test
├── BUILD_AND_TEST.md         ← this file
└── CODEBASE.md               ← full file reference
```

---

## 3. Environment Variables

### 3.1 Minimum required (no channels, no AI)

The app works with **zero credentials** — watsonx.ai falls back to a local rule-based classifier, and all channel adapters skip outbound sends gracefully.

Create `backend/.env` from the example:
```bash
cp backend/.env.example backend/.env
```

The defaults already work for local development:
```
DATABASE_URL=postgresql://nagaraai:nagaraai123@localhost:5432/nagaraai_db
SECRET_KEY=dev-secret-key
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
```

### 3.2 Enable IBM watsonx.ai  `[AI]`

```bash
# backend/.env
WATSONX_API_KEY=your-ibm-cloud-api-key
WATSONX_PROJECT_ID=your-watsonx-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com   # default; change for other regions
```

When set, every complaint classification call and every channel intake message routes through `ibm/granite-13b-instruct-v2`. Without them, `classify_complaint_local()` is used (keyword match, deterministic, works offline).

### 3.3 Enable channels (optional)

Add any subset. Channels with missing credentials log a warning and skip — the rest of the app keeps working.

```bash
# Twilio (WhatsApp / SMS / Voice)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+14155238886
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_VERIFY_SIGNATURE=false   # set true in production

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDxxxxxxxx
TELEGRAM_WEBHOOK_SECRET=random-32-char-string

# SMTP email
SMTP_USER=nagaraai@gmail.com
SMTP_PASSWORD=app-password-here
SMTP_FROM=nagaraai@gmail.com

# Meta (Facebook / Instagram)
META_APP_SECRET=your-meta-app-secret
META_VERIFY_TOKEN=nagaraai-verify
META_PAGE_ACCESS_TOKEN=EAAxxxxx
META_IG_ACCESS_TOKEN=EAAxxxxx

# Twitter/X
TWITTER_API_KEY=xxxxx
TWITTER_API_SECRET=xxxxx
TWITTER_ACCESS_TOKEN=xxxxx
TWITTER_ACCESS_SECRET=xxxxx

# App public URL (Twilio voice transcription callback)
APP_BASE_URL=https://your-public-domain.com
```

---

## 4. Build — Docker Compose (Full Stack)

This is the **recommended path**. One command starts the database, backend, and frontend — all wired together.

### Step 1 — Clone and enter the project

```bash
git clone <repo-url> nagaraai
cd nagaraai
```

### Step 2 — Build all images

```bash
docker compose build
```

**What happens internally:**

| Service | Dockerfile | Build steps |
|---|---|---|
| `db` | `postgres:16-alpine` | Pre-built — no build step |
| `backend` | `backend/Dockerfile` | 1. `FROM python:3.12-slim` → 2. `pip install -r requirements.txt` → 3. `COPY app/` |
| `frontend` | `frontend/Dockerfile` | 1. `FROM node:20-alpine` → 2. `npm install` → 3. `npm start` |

The first build downloads all Python and Node packages (~500 MB). Subsequent builds are layer-cached and complete in seconds.

### Step 3 — Start all services

```bash
docker compose up
```

You will see three log streams prefixed `[db]`, `[backend]`, `[frontend]`.

**Startup sequence (enforced by `depends_on`):**
```
db starts
  └─ healthcheck: pg_isready -U nagaraai -d nagaraai_db (every 5 s, up to 10 retries)
        └─ backend starts (only after db is healthy)
              └─ uvicorn app.main:app --reload → creates all tables on import
                    └─ frontend starts (depends_on: backend)
```

### Step 4 — Seed demo data

In a second terminal:
```bash
docker compose exec backend python seed.py
```

This inserts 8 wards, 5 contractors, 4 demo users, and 6 sample complaints. Safe to re-run.

### Step 5 — Verify

| URL | Expected |
|---|---|
| http://localhost:3000 | React login page |
| http://localhost:8000/health | `{"status":"ok","service":"NagaraAI"}` |
| http://localhost:8000/docs | Swagger UI with all 25 endpoints |

### Step 6 — Stop

```bash
docker compose down          # stops containers, keeps pgdata volume
docker compose down -v       # stops + deletes pgdata (clean slate)
```

---

## 5. Build — Standalone Docker (Backend Only)

Use this when you only need the API (e.g. CI, testing, or connecting to an external DB).

### Build the production image

```bash
docker build -f backend/Dockerfile -t nagaraai-backend:latest ./backend
```

**Dockerfile walkthrough (`backend/Dockerfile`):**
```dockerfile
FROM python:3.12-slim          # ~125 MB minimal Debian image

WORKDIR /app

COPY requirements.txt .        # copied first for layer caching
RUN pip install --no-cache-dir -r requirements.txt  # ~350 MB installed

COPY . .                       # source code (invalidates layer only on code change)

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Run the backend image

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://nagaraai:nagaraai123@host.docker.internal:5432/nagaraai_db" \
  -e SECRET_KEY="dev-secret-key" \
  nagaraai-backend:latest
```

Replace `host.docker.internal` with your Postgres host as appropriate.

### Build the test image

```bash
docker build -f backend/Dockerfile.test -t nagaraai-test:latest ./backend
```

**Dockerfile.test walkthrough:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Baked-in env — no Postgres needed; SQLite is used automatically
ENV DATABASE_URL=sqlite:///./test.db
ENV SECRET_KEY=test-secret-key
ENV WATSONX_API_KEY=        # empty → local AI fallback [AI]
ENV WATSONX_PROJECT_ID=

CMD ["pytest", "-v", "--tb=short"]   # runs on container start
```

---

## 6. Build — Manual Local (No Docker)

### Backend

```bash
cd nagaraai/backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # macOS / Linux

# Install all dependencies (runtime + test)
pip install -r requirements.txt

# Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
# Edit .env — set DATABASE_URL to your local Postgres

# Create tables + seed demo data
python seed.py

# Start the development server
uvicorn app.main:app --reload --port 8000
```

**What `uvicorn app.main:app` does:**
1. Imports `app/main.py`
2. `main.py` runs `Base.metadata.create_all(bind=engine)` → creates all tables in Postgres
3. Registers all five routers (`auth`, `complaints`, `wards`, `analytics`, `channels`)
4. Listens on `0.0.0.0:8000`, hot-reloads on file change (`--reload`)

### Frontend

```bash
cd nagaraai/frontend
npm install
npm start
```

The CRA dev server starts on **http://localhost:3000** and proxies all `/api/*` calls to `http://localhost:8000` via `src/setupProxy.js`.

> **Why `setupProxy.js` and not `package.json "proxy"`?**  
> The `package.json "proxy"` field resolves `localhost` relative to the container running the frontend. In Docker Compose, `localhost` inside the frontend container is itself — not the backend. `setupProxy.js` reads `REACT_APP_PROXY_TARGET` which is set to `http://backend:8000` in the Docker environment, correctly resolving the backend by its service name.

---

## 7. Test Suite — Docker (Recommended)

No Python, no Postgres, no credentials required. Tests run entirely inside a container against an in-memory SQLite database.

### Step 1 — Build the test image

```bash
docker build -f backend/Dockerfile.test -t nagaraai-test:latest ./backend
```

You should see output ending with:
```
Successfully built <sha>
Successfully tagged nagaraai-test:latest
```

### Step 2 — Run all tests

```bash
docker run --rm nagaraai-test:latest
```

### Expected output

```
============================= test session starts ==============================
platform linux -- Python 3.12.x, pytest-8.2.2, pluggy-1.7.0
rootdir: /app
configfile: pytest.ini
testpaths: tests
asyncio: mode=Mode.AUTO
collecting ... collected 75 items

tests/test_auth.py::TestRegister::test_register_success PASSED           [  1%]
tests/test_auth.py::TestRegister::test_register_duplicate_email PASSED   [  2%]
...
tests/test_channels.py::TestDispatcher::test_dispatch_persists_inbound_message PASSED [ 17%]
...
tests/test_watsonx.py::TestWatsonxDispatcher::test_falls_back_on_network_error PASSED [100%]

=============================== warnings summary ===============================
...
======================= 75 passed, 68 warnings in 4.67s ========================
```

**75 passed. 0 failed. 0 errors.**

### Step 3 — Run a single test file

```bash
docker run --rm nagaraai-test:latest pytest tests/test_channels.py -v
```

### Step 4 — Run a single test by name

```bash
docker run --rm nagaraai-test:latest pytest tests/test_watsonx.py::TestLocalClassifier::test_garbage_keyword -v
```

### Step 5 — Run with coverage (optional)

```bash
# Install coverage inside the container at runtime
docker run --rm nagaraai-test:latest \
  sh -c "pip install pytest-cov -q && pytest --cov=app --cov-report=term-missing"
```

### Using docker compose test profile

```bash
# Build and run via docker compose
docker compose --profile test run --rm test
```

This uses the `test` service defined in `docker-compose.yml`:
```yaml
test:
  build:
    context: ./backend
    dockerfile: Dockerfile.test
  environment:
    DATABASE_URL: sqlite:///./test.db
    SECRET_KEY: test-secret-key
    WATSONX_API_KEY: ""       # [AI] empty = local fallback
    WATSONX_PROJECT_ID: ""
  profiles:
    - test
```

---

## 8. Test Suite — Manual Local

If you have Python installed locally and want faster iteration (no Docker build on every change):

```bash
cd nagaraai/backend

# Activate virtual environment (if not already active)
venv\Scripts\activate

# Run all tests
pytest -v

# Run with short traceback
pytest -v --tb=short

# Run one test class
pytest tests/test_channels.py::TestDispatcher -v

# Run tests matching a keyword
pytest -k "watsonx" -v

# Run with output (print statements visible)
pytest -v -s

# Run and stop at first failure
pytest -x
```

The `pytest.ini` file configures discovery automatically:
```ini
[pytest]
testpaths = tests         # only look in backend/tests/
asyncio_mode = auto       # async def test_* run as coroutines automatically
```

**How the SQLite test DB is wired (`tests/conftest.py`):**
```python
# 1. Patch DATABASE_URL before any app import
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

# 2. Create a separate SQLite engine
engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})

# 3. Override the FastAPI get_db() dependency so all routes use the test engine
app.dependency_overrides[get_db] = override_get_db

# 4. Session-scoped fixture creates tables once, drops them after all tests finish
@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")
```

This means:
- **No Postgres needed** — 100% SQLite
- **No network calls** — watsonx.ai uses local fallback, channel adapters skip outbound
- **Tables created once** per pytest session — fast
- **SQLite file cleaned up** after the session completes

---

## 9. Test File Reference

### `test_health.py` — 4 tests

| Test | What it checks |
|---|---|
| `test_health_ok` | `GET /health` → 200 + `{"status":"ok"}` |
| `test_health_no_auth_required` | /health accessible without token |
| `test_docs_accessible` | `GET /docs` → 200 (Swagger UI) |
| `test_openapi_json` | `GET /openapi.json` → 200 + contains `/api/complaints` path |

### `test_auth.py` — 12 tests

| Group | Tests |
|---|---|
| `TestRegister` | success, duplicate email → 400, officer role, missing email → 422, missing name → 422 |
| `TestLogin` | success, wrong password → 401, unknown email → 401, JWT returned |
| `TestMe` | authenticated returns user, unauthenticated → 401, invalid token → 401 |

### `test_complaints.py` — 19 tests

| Group | Tests |
|---|---|
| `TestCreateComplaint` | success → 201 + ticket_id, unauthenticated → 401, missing title → 422, unique ticket IDs |
| `TestListComplaints` | citizen sees own only, unauthenticated → 401, limit/offset pagination |
| `TestGetComplaint` | get existing, get nonexistent → 404 |
| `TestUpdateComplaint` | update status, resolve sets `resolved_at`, update nonexistent → 404 |
| `TestRateComplaint` | rate success, out-of-range → 400 |

> **`[AI]`** — `test_create_success` triggers `classify_with_watsonx()`. The test patches `httpx.AsyncClient` so no real IBM call is made; the local fallback runs instead. The returned `ComplaintOut` will have `ai_category`, `ai_priority`, and `ai_summary` populated.

### `test_wards_analytics.py` — 8 tests

| Group | Tests |
|---|---|
| `TestWards` | list wards → non-empty list, ward stats shape |
| `TestAnalytics` | city stats requires auth, authenticated shape, counts non-negative, ward heatmap, contractor leaderboard |

### `test_watsonx.py` — 14 tests  `[AI]`

| Group | Tests |
|---|---|
| `TestLocalClassifier` | garbage keyword, waterlogging, drain blockage, groundwater, cd_waste, unknown→other, critical/high/low priority, default medium, summary contains category, confidence cap ≤ 1.0, all 4 keys present |
| `TestSLAHours` | critical=4h, high=24h, medium=72h, low=168h, all 4 keys covered |
| `TestWatsonxDispatcher` | falls back when no credentials, falls back on network error (mocked `httpx.AsyncClient`) |

**Key test — testing the AI fallback chain:**
```python
async def test_falls_back_on_network_error(self):
    """When httpx raises, falls back to local classifier."""
    settings.WATSONX_API_KEY = "fake-key"
    settings.WATSONX_PROJECT_ID = "fake-project"
    mock_client = AsyncMock()
    mock_client.__aenter__.side_effect = Exception("network error")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await classify_with_watsonx("Flood water", "")
    # result comes from classify_complaint_local()
    assert result["category"] in {"waterlogging", ...}
```

### `test_channels.py` — 18 tests  `[AI]`

| Group | Tests |
|---|---|
| `TestDispatcher` | persists InboundMessage, stores MediaAttachments, accepts string media_type, empty text no crash, ACK mock called |
| `TestWebhookEndpoints` | voice TwiML, Telegram valid payload, Facebook challenge, Facebook wrong token → 403, Instagram challenge, Facebook no signature, Twitter empty payload, email ingest |
| `TestManagementEndpoints` | inbound list requires auth, inbound list authenticated, dispatch 404, manual dispatch complaint not found, manual dispatch creates record + retrievable |

**`[AI]` involvement in `test_channels.py`:**  
`test_dispatch_persists_inbound_message` calls `dispatch_inbound()` which calls `classify_with_watsonx()`. Because `WATSONX_API_KEY=""` in the test environment, the local classifier runs — the returned `InboundMessage` row will have `ai_category` set to a valid category string (e.g. `garbage_black_spot`).

---

## 10. AI Classification in Tests

### How the `[AI]` label works in this project

Every test marked `[AI]` exercises code that calls the AI classification pipeline. In tests, this **always uses the local rule-based classifier** — there are no live IBM API calls.

### Classification pipeline

```
classify_with_watsonx(title, description)
  │
  ├─ WATSONX_API_KEY = ""  ──────────────────────────────────► classify_complaint_local()
  │                                                                 ↓
  │                                                             keyword scan of CATEGORY_KEYWORDS
  │                                                             returns {category, priority, confidence, summary}
  │
  └─ WATSONX_API_KEY set  ──► POST https://iam.cloud.ibm.com  ──► IAM token
                                └─► POST {WATSONX_URL}/ml/v1/text/generation
                                         model: ibm/granite-13b-instruct-v2
                                         ↓
                                     parse JSON from generated_text
                                     ↓
                                     on any exception ──────────► classify_complaint_local()
```

### CATEGORY_KEYWORDS (rule-based fallback)

| Category | Keywords |
|---|---|
| `garbage_black_spot` | garbage, trash, waste, dump, black spot, refuse, littering, ಕಸ |
| `cd_waste` | construction, demolition, debris, rubble, cement, bricks, sand |
| `waterlogging` | flood, waterlog, puddle, stagnant, overflow, rain water, ನೀರು |
| `drain_blockage` | drain, blocked, clog, sewage, manhole, stormwater, rajakaluves |
| `groundwater` | borewell, groundwater, water shortage, dry, no water, tanker |

### SLA hours by priority

| Priority | SLA Deadline |
|---|---|
| `critical` | 4 hours |
| `high` | 24 hours |
| `medium` | 72 hours |
| `low` | 168 hours (7 days) |

### Where AI runs in production vs tests

| Scenario | AI call | Result source |
|---|---|---|
| Production — `WATSONX_API_KEY` set | `POST /ml/v1/text/generation` | IBM Granite-13B |
| Production — no API key | Local keyword scan | `classify_complaint_local()` |
| Any test | No network call | `classify_complaint_local()` (env var empty) |
| Test with mocked httpx failure | Mock raises exception | `classify_complaint_local()` (fallback) |

---

## 11. Enabling Live IBM watsonx.ai

To run with real IBM AI classification:

### 1. Get credentials

1. Log in to https://cloud.ibm.com
2. Create an **API key** under Manage → Access → API Keys
3. Create a **watsonx.ai project** at https://dataplatform.cloud.ibm.com
4. Copy the **Project ID** from your project's Manage tab

### 2. Set in `.env`

```bash
WATSONX_API_KEY=your-32-char-ibm-api-key
WATSONX_PROJECT_ID=your-project-uuid
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### 3. Verify with a curl

```bash
# After `docker compose up`:
curl -X POST http://localhost:8000/api/complaints/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Garbage pile near Jayanagar bus stop",
    "description": "Huge amount of construction debris on footpath",
    "category": "cd_waste"
  }'
```

The response will include:
```json
{
  "ai_classification": "cd_waste",
  "ai_confidence": 0.92,
  "ai_summary": "Construction debris blocking footpath near Jayanagar bus stop.",
  "priority": "medium",
  "sla_deadline": "2026-11-25T09:00:00Z"
}
```

### 4. Test with a live key

```bash
# Override env at runtime in Docker
docker run --rm \
  -e WATSONX_API_KEY="your-key" \
  -e WATSONX_PROJECT_ID="your-project" \
  -e DATABASE_URL="sqlite:///./test.db" \
  -e SECRET_KEY="test-secret-key" \
  nagaraai-test:latest \
  pytest tests/test_watsonx.py::TestWatsonxDispatcher -v
```

> With real credentials, `test_falls_back_when_no_credentials` will still pass because it temporarily sets `settings.WATSONX_API_KEY = ""` inside the test. `test_falls_back_on_network_error` patches `httpx.AsyncClient` before the network call and forces a fallback.

---

## 12. Verifying Channel Webhooks

After `docker compose up`, the webhook endpoints are live at `http://localhost:8000/api/channels/webhook/*`. To expose them publicly for testing with real platforms, use **ngrok**:

```bash
ngrok http 8000
# Forwarding: https://abc123.ngrok-free.app → localhost:8000
```

### Quick smoke test — email webhook

```bash
curl -X POST http://localhost:8000/api/channels/webhook/email \
  -H "Content-Type: application/json" \
  -d '{
    "from": "citizen@example.com",
    "subject": "Waterlogging on 3rd Main",
    "body": "There is severe waterlogging outside my building due to blocked drain."
  }'
# → {"status":"ok"}
```

Check the inbound message was saved and AI-classified:  
```bash
# Get a JWT first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"citizen@demo.com","password":"demo1234"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/channels/inbound \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### Facebook/Instagram hub challenge test

```bash
curl "http://localhost:8000/api/channels/webhook/facebook?hub.mode=subscribe&hub.verify_token=nagaraai-verify&hub.challenge=TEST_CHALLENGE"
# → TEST_CHALLENGE
```

### Telegram webhook test

```bash
curl -X POST http://localhost:8000/api/channels/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 1,
      "chat": {"id": 123456, "type": "private"},
      "from": {"id": 123456, "first_name": "Ravi", "last_name": "Kumar"},
      "text": "Garbage pile near Koramangala 5th Block",
      "date": 1700000000
    }
  }'
# → {"ok":true}
```

---

## 13. CI Workflow Reference

For a CI pipeline (GitHub Actions, GitLab CI, Jenkins, etc.), the minimum working job is:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build test image
        run: docker build -f backend/Dockerfile.test -t nagaraai-test ./backend

      - name: Run tests
        run: docker run --rm nagaraai-test

      # Optional: fail if any new test is added without passing
      - name: Assert test count
        run: |
          COUNT=$(docker run --rm nagaraai-test pytest --collect-only -q 2>/dev/null | grep "selected" | grep -oP '\d+')
          echo "Collected $COUNT tests"
          [ "$COUNT" -ge 75 ] || (echo "Expected ≥75 tests, got $COUNT" && exit 1)
```

No secrets needed — watsonx.ai uses the local fallback (`WATSONX_API_KEY=` is baked into `Dockerfile.test`).

---

## 14. Troubleshooting

### `docker: error getting credentials — docker-credential-desktop not found`
Add the Docker bin directory to PATH:
```powershell
$env:PATH = "C:\Users\$env:USERNAME\AppData\Local\Programs\DockerDesktop\resources\bin;" + $env:PATH
```

### `ModuleNotFoundError: No module named 'twilio'`
The twilio package is in `requirements.txt`. Rebuild the image:
```bash
docker build --no-cache -f backend/Dockerfile.test -t nagaraai-test ./backend
```

### `passlib AttributeError: __about__`
bcrypt ≥ 4.1 broke passlib 1.7.4. The fix is already in `requirements.txt`:
```
bcrypt==4.0.1
```
If you see this error, make sure your image was built from the pinned `requirements.txt`.

### `pydantic_settings extra_forbidden`
pydantic-settings v2 rejects unknown env vars unless `extra="ignore"` is set. Already fixed in `config.py`:
```python
model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

### Frontend shows `500` on login / API calls return `502`
The `REACT_APP_PROXY_TARGET` env var must point to the backend by its Docker service name, not `localhost`:
```yaml
# docker-compose.yml
frontend:
  environment:
    REACT_APP_PROXY_TARGET: http://backend:8000   ← correct
```
`setupProxy.js` reads this variable and sets the proxy target at CRA startup.

### Backend does not start — `could not connect to server: Connection refused`
The backend depends on `db` being healthy. Wait for the healthcheck to pass:
```bash
docker compose ps   # check db health column
docker compose logs db
```

### Test DB not cleaned up between runs
If a previous test run crashed, `test.db` may still exist in `backend/`. Delete it:
```bash
Remove-Item backend/test.db -ErrorAction SilentlyContinue   # PowerShell
# rm backend/test.db                                         # bash
```

### `[AI]` test fails with `KeyError: 'results'`
This only happens when running with a real `WATSONX_API_KEY` set. It means the watsonx endpoint returned an unexpected response format. The test suite normally runs with an empty key, so this won't occur in Docker test runs. If needed, check your project ID and regional endpoint.

### Running tests outside Docker on Windows (venv missing)
```powershell
cd nagaraai/backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v
```

---

*NagaraAI · Build & Test Guide · November 2026*
