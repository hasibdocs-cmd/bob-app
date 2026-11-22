# NagaraAI — Codebase Reference

Complete file-by-file description of every file and folder in the project: its purpose, what it exports, its dependencies, which other files depend on it, and how it fits into the overall application workflow.

> **Last updated:** November 2026 — includes multi-channel intake (WhatsApp, SMS, Voice, Telegram, Email, Facebook, Instagram, Twitter/X), central AI dispatcher, channel management API, and 75-test suite.

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
   - [Channel Adapters](#55-channel-adapters)
   - [Tests](#56-tests)
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
11. [API Endpoint Reference](#11-api-endpoint-reference)

---

## 1. Project Overview

**NagaraAI** is a full-stack civic issue management platform for Bengaluru. Citizens report problems (potholes, garbage, flooding) through the web portal **or any of 9 external channels** (WhatsApp, SMS/MMS, Voice, Telegram, Email, Facebook, Instagram, Twitter/X). Every inbound message is automatically classified by IBM watsonx.ai Granite-13B (or a local rule-based fallback), persisted, and acknowledged. Ward officers, field officers, and commissioners track, dispatch, and analyse resolution in real time through a role-adaptive single-page application.

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Recharts, Leaflet, Axios |
| Backend API | FastAPI 0.111, Python 3.12 |
| ORM | SQLAlchemy 2.0, Alembic 1.13 |
| Database | PostgreSQL 16 (Docker) / SQLite (tests) |
| AI | IBM watsonx.ai Granite-13B + rule-based fallback |
| Auth | JWT (python-jose + bcrypt via passlib) |
| Channel integrations | Twilio (WhatsApp/SMS/MMS/Voice), Telegram Bot API, Meta Graph API, Twitter/X DM API, SMTP |
| Infrastructure | Docker Compose, Kubernetes (kind + skaffold) |
| Testing | pytest 8.2, pytest-asyncio, aiosqlite — **75 tests, all passing** |

---

## 2. Repository Layout

```
nagaraai/
├── docker-compose.yml              # Orchestrates all 4 services (db, backend, frontend, test)
├── README.md                       # Quick-start guide
├── CODEBASE.md                     # ← this file
├── SETUP.md                        # Detailed setup + operations guide
├── nagaraai-guide.html             # 7-tab interactive architecture guide (HTML)
├── nagaraai-multi-channel-intake-implementation-guide.html
│                                   # Multi-channel implementation walkthrough (HTML)
├── nagaraai-self-hosting-guide.html
│
├── backend/
│   ├── Dockerfile                  # Production backend image (uvicorn)
│   ├── Dockerfile.test             # Test runner image (pytest, SQLite)
│   ├── pytest.ini                  # pytest config — testpaths + asyncio_mode=auto
│   ├── requirements.txt            # Python runtime + test dependencies
│   ├── seed.py                     # One-time DB population script
│   ├── .env.example                # Template for secrets
│   ├── .env                        # Local secrets (gitignored)
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory + CORS + router registration
│       ├── config.py               # Settings (pydantic-settings, 40+ env vars)
│       ├── database.py             # SQLAlchemy engine + session factory
│       ├── models.py               # ORM models + enums (incl. channel models)
│       ├── schemas.py              # Pydantic request/response models
│       ├── auth.py                 # JWT + password hashing + guards
│       ├── watsonx.py              # AI classifier + analyze_media + transcribe_voice
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── auth.py             # POST /api/auth/register|login, GET /me
│       │   ├── complaints.py       # CRUD /api/complaints/
│       │   ├── wards.py            # GET /api/wards/
│       │   ├── analytics.py        # GET /api/analytics/*
│       │   └── channels.py         # /api/channels/* — webhooks + dispatch mgmt
│       └── channels/               # ← NEW: multi-channel adapter package
│           ├── __init__.py
│           ├── dispatcher.py       # Central AI dispatcher (all channels funnel here)
│           ├── whatsapp.py         # Twilio WhatsApp Business API
│           ├── sms.py              # Twilio SMS / MMS
│           ├── voice.py            # Twilio Voice TwiML + IVR
│           ├── telegram.py         # Telegram Bot API
│           ├── email_chan.py        # SMTP outbound + RFC 2822 inbound parser
│           └── social.py           # Facebook / Instagram / Twitter-X adapters
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # pytest fixtures + test helpers
│   ├── test_health.py              # /health + OpenAPI smoke tests  (4 tests)
│   ├── test_auth.py                # Register / Login / /me tests  (12 tests)
│   ├── test_complaints.py          # Full complaint lifecycle tests (19 tests)
│   ├── test_wards_analytics.py     # Wards + analytics endpoints    (8 tests)
│   ├── test_watsonx.py             # AI classifier unit tests       (14 tests)
│   └── test_channels.py            # ← NEW: channel intake tests   (18 tests)
│
├── frontend/
│   ├── Dockerfile                  # Dev-server image (npm start, CRA)
│   ├── Dockerfile.k8s              # Production multi-stage image (Node build → Nginx)
│   ├── package.json                # npm dependencies + scripts
│   └── src/
│       ├── index.js                # React DOM entry point
│       ├── index.css               # Global CSS variables + base styles
│       ├── App.js                  # Router root + auth-gated routes
│       ├── api.js                  # Axios instance + interceptors
│       ├── setupProxy.js           # CRA dev-proxy → backend:8000 (Docker safe)
│       ├── context/
│       │   └── AuthContext.js      # Auth state (user, login, logout)
│       ├── pages/
│       │   ├── Login.js            # Login form page
│       │   ├── Register.js         # Registration form page
│       │   ├── Dashboard.js        # City analytics + charts
│       │   ├── Complaints.js       # Issue list + filters + actions
│       │   └── WardMap.js          # Leaflet choropleth risk map
│       └── components/
│           ├── AppShell.js         # Authenticated layout wrapper + sub-router
│           ├── Sidebar.js          # Role-adaptive nav + user chip
│           ├── ReportModal.js      # Citizen complaint form + channel selector
│           └── ComplaintDetail.js  # Complaint detail + status updates + notify panel
│
└── k8s/                            # Kubernetes manifests
    ├── namespace.yaml
    ├── kind-config.yaml
    ├── skaffold.yaml
    ├── README.md
    ├── secrets/secrets.yaml
    ├── postgres/  (pvc + deployment + service)
    ├── backend/   (deployment + service)
    ├── frontend/  (deployment + service)
    └── ingress/ingress.yaml
```

---

## 3. Application Workflow

### 3.1 Web complaint lifecycle

```
Browser (Citizen)
  └─→ ReportModal.js          POST /api/complaints/
        └─→ api.js            attaches Bearer token
              └─→ routes/complaints.py
                    ├─→ auth.py::get_current_user()   validates JWT
                    ├─→ watsonx.py::classify_with_watsonx()
                    │         ├─ WATSONX_API_KEY set → IBM Granite-13B
                    │         └─ else → classify_complaint_local()
                    ├─→ models.Complaint  (created in DB)
                    └─→ schemas.ComplaintOut  (returned to browser)
```

### 3.2 Multi-channel inbound lifecycle (NEW)

```
Citizen (any channel: WhatsApp / SMS / Telegram / Voice / Email / FB / IG / Twitter)
  └─→ Platform webhook POST → routes/channels.py::webhook_<channel>()
        ├─→ Signature verification (Twilio HMAC / Meta SHA256 / Telegram secret)
        └─→ channels/dispatcher.py::dispatch_inbound()
              ├─→ watsonx.py::classify_with_watsonx()   (AI classification)
              ├─→ DB: InboundMessage row  (+ MediaAttachment rows if media present)
              └─→ _send_ack()  → reply on the same channel
                        ├─ ChannelType.whatsapp  → channels/whatsapp.py::send_whatsapp()
                        ├─ ChannelType.sms/mms   → channels/sms.py::send_sms()
                        ├─ ChannelType.telegram  → channels/telegram.py::send_telegram()
                        ├─ ChannelType.email     → channels/email_chan.py::send_email()
                        ├─ ChannelType.facebook  → channels/social.py::send_facebook_message()
                        ├─ ChannelType.instagram → channels/social.py::send_instagram_message()
                        └─ ChannelType.twitter_x → channels/social.py::send_twitter_dm()
```

### 3.3 Officer outbound notification lifecycle (NEW)

```
Officer (ComplaintDetail.js → Send Notification panel)
  └─→ POST /api/channels/dispatch  { complaint_id, channel, recipient }
        └─→ routes/channels.py::manual_dispatch()
              ├─→ DB: Complaint lookup (404 if not found)
              ├─→ Auto-generate message body from complaint if not supplied
              ├─→ Call channel adapter outbound sender
              └─→ DB: ChannelDispatch row (status: sent | queued)
```

### 3.4 Auth lifecycle

```
Login.js  POST /api/auth/login
  └─→ routes/auth.py::login()
        └─→ auth.py::verify_password() + create_access_token()
              └─→ Token { access_token, user }
                    └─→ AuthContext.js::login()
                          └─→ localStorage["token"] + localStorage["user"]
                                └─→ api.js interceptor auto-injects header
```

### 3.5 Role-based view scoping

| Role | Complaint list scope | Can update status | Send notifications |
|---|---|---|---|
| `citizen` | Only their own reports | No | No |
| `field_officer` | Assigned to them | Yes | Yes |
| `ward_officer` | All in their ward | Yes | Yes |
| `commissioner` | All city-wide | Yes | Yes |

---

## 4. Root Files

### `docker-compose.yml`

**Purpose:** Defines and connects all four services.
**Used by:** `docker compose up`, CI pipelines.

| Service | Image / Build | Ports | Key env vars | Depends on |
|---|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | `POSTGRES_*` | — |
| `backend` | `./backend/Dockerfile` | 8000 | `DATABASE_URL`, `SECRET_KEY`, `WATSONX_*`, all channel vars | `db` (healthy) |
| `frontend` | `./frontend/Dockerfile` | 3000 | `REACT_APP_PROXY_TARGET` | `backend` |
| `test` | `./backend/Dockerfile.test` | — | `DATABASE_URL=sqlite:///./test.db` | — (profile: `test`) |

The `test` service uses Docker profile `test`:
```bash
docker compose --profile test up test
# or directly:
docker run --rm nagaraai-test:latest
```

### `README.md`
Quick-start guide, demo logins, API reference table, tech-stack summary.

### `SETUP.md`
Detailed setup + operations guide covering Docker Compose, manual install, Kubernetes, secrets configuration, channel webhook registration, and troubleshooting.

### `nagaraai-guide.html`
7-tab interactive HTML architecture guide (Architecture, Lifecycle, Escalation Matrix, Role Permissions, SLA & Categories, API Reference, User Guide).

### `nagaraai-multi-channel-intake-implementation-guide.html`
Walkthrough of the multi-channel implementation: schema, dispatcher internals, channel adapters, all API endpoints, env vars, frontend changes, test coverage.

---

## 5. Backend — `backend/`

---

### 5.1 Configuration & Bootstrap

#### `backend/Dockerfile`
Multi-stage production image. Installs Python 3.12-slim, copies `requirements.txt`, runs `pip install`, copies application code, starts `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

#### `backend/Dockerfile.test`
Identical base, but runs `pytest -v --tb=short` as `CMD`. Sets `DATABASE_URL=sqlite:///./test.db` so no Postgres is needed. Used by `docker run --rm nagaraai-test:latest`.

#### `backend/pytest.ini`
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
```
Sets `asyncio_mode=auto` so all `async def test_*` functions run without explicit `@pytest.mark.asyncio` markers (though the existing tests also use them for clarity).

#### `backend/requirements.txt`
Key dependencies:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.111.0 | Web framework |
| `uvicorn[standard]` | 0.29.0 | ASGI server |
| `sqlalchemy` | 2.0.30 | ORM |
| `alembic` | 1.13.1 | Migrations |
| `pydantic` | 2.7.1 | Data validation |
| `pydantic-settings` | 2.2.1 | Settings from env |
| `python-jose[cryptography]` | 3.3.0 | JWT |
| `passlib[bcrypt]` | 1.7.4 | Password hashing |
| `bcrypt` | 4.0.1 | Pinned — passlib incompatible with 4.1+ |
| `httpx` | 0.27.0 | Async HTTP (watsonx + social APIs) |
| `twilio` | 9.0.4 | WhatsApp / SMS / Voice |
| `requests-oauthlib` | 1.3.1 | Twitter/X OAuth1 |
| `pytest` | 8.2.2 | Test runner |
| `pytest-asyncio` | 0.23.7 | Async test support |
| `aiosqlite` | 0.20.0 | SQLite async driver for tests |

#### `backend/app/config.py`
**Exports:** `settings` (singleton `Settings` instance).
**Pattern:** `pydantic_settings.BaseSettings` with `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`. Settings are read from environment variables first, then `.env` file, then defaults.

Groups:
- **Core:** `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- **watsonx.ai:** `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`
- **Twilio:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TWILIO_WHATSAPP_NUMBER`, `TWILIO_VERIFY_SIGNATURE`
- **Telegram:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
- **SMTP:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- **Meta:** `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_PAGE_ACCESS_TOKEN`, `META_IG_ACCESS_TOKEN`
- **Twitter/X:** `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
- **App:** `APP_BASE_URL` (used for Twilio voice transcription callback URL)

#### `backend/app/database.py`
**Exports:** `Base`, `engine`, `SessionLocal`, `get_db` (FastAPI dependency).
Creates the SQLAlchemy engine from `settings.DATABASE_URL`. `get_db()` is a generator that yields a session and closes it after the request.

#### `backend/app/main.py`
**Exports:** `app` (FastAPI instance).
Creates the app, adds CORS middleware (allow all origins — tighten in production), creates all DB tables (`Base.metadata.create_all`), and registers all routers:

```python
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(wards.router)
app.include_router(analytics.router)
app.include_router(channels_router.router)   # ← NEW
```

---

### 5.2 Data Layer

#### `backend/app/models.py`
**Exports:** All ORM models + enums.

**Enums:**
| Enum | Values |
|---|---|
| `UserRole` | citizen, field_officer, ward_officer, commissioner |
| `IssueCategory` | garbage_black_spot, cd_waste, waterlogging, drain_blockage, groundwater, other |
| `IssuePriority` | low, medium, high, critical |
| `IssueStatus` | open, assigned, in_progress, resolved, closed, escalated |
| `ChannelType` *(new)* | whatsapp, telegram, sms, mms, email, voice, twitter_x, facebook, instagram, web, api |
| `MediaType` *(new)* | image, video, audio, document, location |

**ORM Models:**

| Model | Table | Key relationships |
|---|---|---|
| `User` | `users` | → `Ward`, → `Complaint` (reporter + assignee) |
| `Ward` | `wards` | ← `User`, ← `Complaint`, ← `Contractor` |
| `Contractor` | `contractors` | → `Ward`, ← `Complaint` |
| `Complaint` | `complaints` | → `User` (×2), → `Ward`, → `Contractor`, ← `ComplaintUpdate`, ← `InboundMessage`, ← `ChannelDispatch` |
| `ComplaintUpdate` | `complaint_updates` | → `Complaint`, → `User` |
| `InboundMessage` *(new)* | `inbound_messages` | → `Complaint` (nullable), ← `MediaAttachment` |
| `MediaAttachment` *(new)* | `media_attachments` | → `InboundMessage` |
| `ChannelDispatch` *(new)* | `channel_dispatches` | → `Complaint` |

#### `backend/app/schemas.py`
**Exports:** Pydantic models for request validation and response serialization.

Core schemas: `UserCreate`, `UserLogin`, `UserOut`, `Token`, `WardOut`, `ContractorOut`, `ComplaintCreate`, `ComplaintUpdate`, `ComplaintRating`, `ComplaintOut`, `ComplaintUpdateOut`, `CityStats`, `WardStats`.

Channel schemas *(new)*:
- `MediaAttachmentOut` — response model for `MediaAttachment`
- `InboundMessageOut` — response model for `InboundMessage` with nested `attachments`
- `ChannelDispatchOut` — response model for `ChannelDispatch`
- `DispatchRequest` — body for `POST /api/channels/dispatch`
- `TwilioWebhookPayload` — Twilio form-encoded webhook fields
- `TelegramUpdate` — Telegram Update JSON object
- `MetaWebhookPayload` — Meta (Facebook/Instagram) webhook entry array

#### `backend/seed.py`
Standalone script. Creates all tables, inserts 4 wards, 4 demo users (citizen / field_officer / ward_officer / commissioner), 2 contractors, and 6 sample complaints. Run once after first `docker compose up`:
```bash
docker compose exec backend python seed.py
```

---

### 5.3 Business Logic

#### `backend/app/auth.py`
**Exports:** `hash_password`, `verify_password`, `create_access_token`, `get_current_user`, `require_role`, `oauth2_scheme`.

- `get_current_user` — FastAPI dependency; decodes JWT, queries User by `sub` claim, raises 401 if invalid.
- `require_role(*roles)` — higher-order dependency factory for role-based access.

#### `backend/app/watsonx.py`
**Exports:** `classify_complaint_local`, `classify_with_watsonx`, `analyze_media`, `transcribe_voice`, `SLA_HOURS`.

| Function | Purpose |
|---|---|
| `classify_complaint_local(title, desc)` | Keyword-based rule classifier — always available, no credentials needed |
| `classify_with_watsonx(title, desc)` | Async — calls IBM Granite-13B via IAM token; falls back to local on any error |
| `analyze_media(url, mime_type)` | Stub for watsonx Vision — returns placeholder if no key |
| `transcribe_voice(audio_url)` | Stub for watsonx Speech-to-Text — returns `""` if no key |
| `SLA_HOURS` | Dict: `{critical: 4, high: 24, medium: 72, low: 168}` |

---

### 5.4 API Routes

#### `backend/app/routes/auth.py`
Prefix: none. Endpoints:
- `POST /api/auth/register` — creates User, returns `Token`
- `POST /api/auth/login` — verifies credentials, returns `Token`
- `GET /api/auth/me` — returns `UserOut` for current JWT holder

#### `backend/app/routes/complaints.py`
Prefix: `/api/complaints`. Endpoints:
- `POST /` — creates Complaint, runs AI classification, sets SLA deadline
- `GET /` — lists complaints scoped to role (citizen → own, field_officer → assigned, ward_officer → ward, commissioner → all)
- `GET /{id}` — single complaint with updates
- `PATCH /{id}` — update status / priority / assignee / contractor; creates `ComplaintUpdate` row
- `POST /{id}/rate` — citizen submits rating 1–5

#### `backend/app/routes/wards.py`
Prefix: `/api/wards`. Endpoints:
- `GET /` — lists all wards
- `GET /{id}/stats` — open + resolved counts + scores for one ward

#### `backend/app/routes/analytics.py`
Prefix: `/api/analytics`. Endpoints (all require auth):
- `GET /city` — `CityStats` aggregate
- `GET /ward-heatmap` — list of `WardStats`
- `GET /contractors` — contractor leaderboard sorted by compliance

#### `backend/app/routes/channels.py` *(NEW)*
Prefix: `/api/channels`. Two groups:

**Webhook endpoints (no auth — platform-verified):**

| Method | Path | Channel | Verification |
|---|---|---|---|
| POST | `/webhook/whatsapp` | Twilio WhatsApp | HMAC `X-Twilio-Signature` |
| POST | `/webhook/sms` | Twilio SMS/MMS | HMAC `X-Twilio-Signature` |
| POST | `/webhook/voice` | Twilio Voice | Returns TwiML only |
| POST | `/webhook/voice/transcription` | Twilio transcription cb | None (internal) |
| POST | `/webhook/telegram` | Telegram Bot | `X-Telegram-Bot-Api-Secret-Token` |
| GET/POST | `/webhook/facebook` | Meta Messenger | Hub challenge / `X-Hub-Signature-256` |
| GET/POST | `/webhook/instagram` | Meta Instagram DM | Hub challenge / `X-Hub-Signature-256` |
| POST | `/webhook/twitter` | Twitter/X Account Activity | None (bearer token) |
| POST | `/webhook/email` | Email (via MTA parse) | None |

**Management endpoints (JWT Bearer required):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/dispatch` | Send outbound notification to citizen on any channel |
| `GET` | `/inbound` | List InboundMessages (filterable: `?channel=whatsapp`) |
| `GET` | `/dispatch/{id}` | Get ChannelDispatch status |

---

### 5.5 Channel Adapters

All adapters are in `backend/app/channels/`. Every outbound sender checks for required credentials first and logs an info-level skip instead of raising — safe to run unconfigured.

#### `dispatcher.py` — Central dispatcher
**Exports:** `dispatch_inbound(*, db, channel, sender_id, raw_text, ...)`.

Called by every webhook handler. Steps:
1. Run `classify_with_watsonx()` on `raw_text` or `ai_transcript`
2. Write `InboundMessage` row to DB (`db.flush()` for child ID)
3. Write `MediaAttachment` rows for each attachment
4. `db.commit()` + `db.refresh()`
5. Call `_send_ack()` → picks the right outbound sender for `channel`

#### `whatsapp.py`
- `send_whatsapp(to, body, complaint_id)` → Twilio Messages API (`from_=whatsapp:+1…`)
- `verify_twilio_signature(url, params, sig)` → `twilio.request_validator.RequestValidator`

#### `sms.py`
- `send_sms(to, body)` → Twilio Messages API (plain phone number)
- `send_mms(to, body, media_url)` → Twilio Messages API with `media_url` list

#### `voice.py`
- `get_ivr_twiml(record_callback_url)` → TwiML string with `<Say>` + `<Record transcribe=true>`

#### `telegram.py`
- `send_telegram(chat_id, text)` → `POST /sendMessage`
- `verify_telegram_secret(body, header_secret)` → `hmac.compare_digest`
- `set_webhook(webhook_url)` → `POST /setWebhook` (call once at deploy time)

#### `email_chan.py`
- `send_email(to, subject, html_body)` → SMTP with TLS (`smtplib`)
- `parse_email_report(raw_email_text)` → dict with `sender_id`, `raw_text`, `metadata_`

#### `social.py`
- `verify_meta_signature(body, header_signature)` → HMAC-SHA256 against `META_APP_SECRET`
- `extract_facebook_messages(payload)` → list of `{sender_id, text, attachments}`
- `extract_instagram_messages(payload)` → same as Facebook (identical Meta format)
- `extract_twitter_mentions(payload)` → list of `{sender_id, sender_name, text, external_id}`
- `send_facebook_message(recipient_id, text)` → Meta Graph API `/me/messages`
- `send_instagram_message(recipient_id, text)` → Meta Graph API `/me/messages`
- `send_twitter_dm(recipient_id, text)` → Twitter v2 DM Conversations API (OAuth1)

---

### 5.6 Tests

All tests run in-memory SQLite. No external services needed. Run via:
```bash
docker run --rm nagaraai-test:latest
# → 75 passed in ~4.6s
```

#### `tests/conftest.py`
Patches `DATABASE_URL` before any import, creates a shared SQLite engine, overrides `get_db` dependency, defines `client` (session-scoped `TestClient`), and exports helpers `register_user`, `login_user`, `auth_headers`.

#### `tests/test_health.py` — 4 tests
Smoke tests: `/health` returns `{"status": "ok"}`, docs at `/docs`, OpenAPI JSON at `/openapi.json`.

#### `tests/test_auth.py` — 12 tests
Register success/duplicate/missing fields; login success/wrong-password/unknown-email/JWT-returned; `GET /me` authenticated/unauthenticated/invalid-token.

#### `tests/test_complaints.py` — 19 tests
Create success/unauthenticated/missing-title/unique-ticket; list scoping; get existing/nonexistent; update status/resolve; rate success/out-of-range.

#### `tests/test_wards_analytics.py` — 8 tests
List wards; ward stats; city stats requires-auth/authenticated/non-negative; ward heatmap; contractor leaderboard.

#### `tests/test_watsonx.py` — 14 tests
Local classifier — keyword matching for all 5 categories, priority keywords, confidence cap, keys present; SLA hours dict; watsonx dispatcher falls-back without credentials and on network error.

#### `tests/test_channels.py` *(NEW)* — 18 tests

*Dispatcher (5):* persists `InboundMessage`, stores `MediaAttachment` rows, accepts string `media_type`, handles empty text without crash, mock-verifies ACK is sent on WhatsApp.

*Webhook endpoints (8):* voice returns valid TwiML, Telegram webhook accepts correct payload, Facebook hub challenge returns challenge string, wrong token → 403, Instagram hub challenge, Facebook with no `META_APP_SECRET` → 200, Twitter empty payload → 200, email ingest → 200.

*Management endpoints (5):* inbound list requires auth, inbound list authenticated, dispatch/{id} 404, manual dispatch complaint-not-found, manual dispatch creates record and is retrievable.

---

## 6. Frontend — `frontend/`

---

### 6.1 Entry Points

#### `frontend/src/index.js`
React DOM entry. Renders `<App />` into `#root`. Wraps with `<AuthProvider>` and `<Toaster>` (react-hot-toast).

#### `frontend/src/index.css`
CSS custom properties: `--accent`, `--surface`, `--border`, `--text`, `--muted`, `--success`, `--danger`, badge and button classes, modal and form styles.

#### `frontend/src/App.js`
React Router 6 `<Routes>`. Public routes: `/login`, `/register`. Private routes wrapped in `<RequireAuth>`: renders `<AppShell>` with sub-routes for Dashboard, Complaints, WardMap.

#### `frontend/src/setupProxy.js`
CRA HTTP proxy configuration. Forwards all `/api/*` requests to `process.env.REACT_APP_PROXY_TARGET` (default `http://localhost:8000`). Set `REACT_APP_PROXY_TARGET=http://backend:8000` in Docker Compose so the frontend container resolves the backend by service name, not `localhost`.

---

### 6.2 API Client

#### `frontend/src/api.js`
Axios instance with `baseURL: ""`. Request interceptor injects `Authorization: Bearer <token>` from `localStorage`. Response interceptor redirects to `/login` on 401.

---

### 6.3 Auth Context

#### `frontend/src/context/AuthContext.js`
React context with `useAuth()` hook. Provides `user`, `login(token, user)`, `logout()`. Persists to `localStorage`. `login()` decodes the JWT to get the user object; `logout()` clears storage and redirects.

---

### 6.4 Pages

#### `frontend/src/pages/Login.js`
Email + password form. `POST /api/auth/login`. Calls `AuthContext.login()` on success. Shows error toast on failure.

#### `frontend/src/pages/Register.js`
Name / email / password / role dropdown. `POST /api/auth/register`. Redirects to `/login` after success.

#### `frontend/src/pages/Dashboard.js`
Fetches `GET /api/analytics/city` and `GET /api/analytics/ward-heatmap`. Renders KPI cards (total complaints, open, resolved today, avg resolution hours) and a Recharts bar chart of ward open counts.

#### `frontend/src/pages/Complaints.js`
Fetches complaint list with role-scoped filter. Renders a table with ticket ID, title, category badge, priority badge, status badge, SLA countdown. Opens `<ReportModal>` for new reports; opens `<ComplaintDetail>` for existing ones.

#### `frontend/src/pages/WardMap.js`
Renders a Leaflet map centered on Bengaluru. Fetches ward heatmap data, draws GeoJSON polygons colour-coded by `flood_risk_score`. Clicking a ward shows a tooltip with its stats.

---

### 6.5 Components

#### `frontend/src/components/AppShell.js`
Authenticated shell: `<Sidebar>` on the left, page content on the right. Renders the correct page based on the current route. Provides a "Report Issue" floating button for citizens.

#### `frontend/src/components/Sidebar.js`
Renders nav links appropriate to the user's role. Shows the current user's name and role chip. Logout button. Active link highlighting via `useLocation`.

#### `frontend/src/components/ReportModal.js`
Citizen complaint form. Fields: title, category, description, address, latitude/longitude (with "Use My Location" button), image URL, **channel selector** *(new)*.

The channel selector lets citizens indicate how they prefer to interact:
- Web (default) — this form
- WhatsApp, Telegram, SMS, Email — shows a contextual hint about reporting directly on that channel

Submits `POST /api/complaints/`. On success shows a toast with the ticket ID and AI-assigned priority.

#### `frontend/src/components/ComplaintDetail.js`
Displays full complaint detail in a modal panel. Sections:
- AI watsonx.ai analysis block (category, confidence, summary)
- Status / priority / category / dates grid
- Image preview
- Activity timeline (ComplaintUpdates)
- Status-update buttons (officers only)
- **📣 Send Notification panel** *(new)* — officers can dispatch a notification on WhatsApp/SMS/Telegram/Email to any recipient. Calls `POST /api/channels/dispatch`.
- Star rating (citizens, resolved complaints only)

---

## 7. Kubernetes — `k8s/`

### 7.1 Cluster Config

#### `k8s/namespace.yaml`
Creates the `nagaraai` namespace used by all other manifests.

#### `k8s/kind-config.yaml`
kind cluster with one control-plane node, two worker nodes, and port mappings 80→30080 and 443→30443 for ingress.

#### `k8s/skaffold.yaml`
Skaffold v2 dev-loop: builds both Docker images on file change, applies all manifests via `kubectl`, tails logs.

#### `k8s/README.md`
Step-by-step Kubernetes deployment guide (kind / minikube / cloud cluster).

### 7.2 Secrets
#### `k8s/secrets/secrets.yaml`
Kubernetes `Secret` with base64-encoded: `DATABASE_URL`, `SECRET_KEY`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`. Referenced by backend `Deployment` as `envFrom.secretRef`.

### 7.3 PostgreSQL
`postgres/pvc.yaml` — 1 Gi `PersistentVolumeClaim`.
`postgres/deployment.yaml` — `postgres:16-alpine` pod with readiness probe (`pg_isready`).
`postgres/service.yaml` — `ClusterIP` `postgres-svc` on port 5432.

### 7.4 Backend
`backend/deployment.yaml` — FastAPI pod with `initContainer` running `python seed.py`, liveness probe `GET /health`, env vars from secret. Replicas: 1.
`backend/service.yaml` — `ClusterIP` `backend-svc` on port 8000.

### 7.5 Frontend
`frontend/deployment.yaml` — Nginx pod serving the React build. `ConfigMap` injects `nginx.conf` with `/api` proxy to `backend-svc:8000`.
`frontend/service.yaml` — `NodePort` `frontend-svc` on port 3000, `nodePort: 30080`.

### 7.6 Ingress
`ingress/ingress.yaml` — `nginx` ingress class. Routes `/api` → `backend-svc:8000`, `/` → `frontend-svc:3000`.

---

## 8. Dependency Graph

```
docker-compose.yml
  ├── backend/Dockerfile
  │     └── requirements.txt
  │           └── app/
  │                 ├── config.py ← .env / environment vars
  │                 ├── database.py ← config.py
  │                 ├── models.py ← database.py
  │                 ├── schemas.py ← models.py
  │                 ├── auth.py ← config.py, database.py, models
  │                 ├── watsonx.py ← config.py
  │                 ├── main.py ← database.py, routes/*, channels/dispatcher
  │                 ├── routes/
  │                 │     ├── auth.py ← database, models, schemas, auth
  │                 │     ├── complaints.py ← database, models, schemas, auth, watsonx
  │                 │     ├── wards.py ← database, models, schemas
  │                 │     ├── analytics.py ← database, models, schemas, auth
  │                 │     └── channels.py ← database, models, schemas, auth,
  │                 │                       channels/dispatcher, channels/*adapters,
  │                 │                       config
  │                 └── channels/
  │                       ├── dispatcher.py ← models, watsonx, channels/*adapters
  │                       ├── whatsapp.py ← config
  │                       ├── sms.py ← config
  │                       ├── voice.py ← config
  │                       ├── telegram.py ← config
  │                       ├── email_chan.py ← config
  │                       └── social.py ← config
  │
  ├── backend/Dockerfile.test
  │     └── tests/conftest.py ← app/main.py, app/database
  │           ├── test_health.py
  │           ├── test_auth.py
  │           ├── test_complaints.py
  │           ├── test_wards_analytics.py
  │           ├── test_watsonx.py
  │           └── test_channels.py ← channels/dispatcher, routes/channels
  │
  ├── frontend/Dockerfile (dev server)
  │     └── package.json
  │           └── src/
  │                 ├── index.js → App.js
  │                 ├── App.js → AuthContext, AppShell, Login, Register
  │                 ├── api.js (used by all pages + components)
  │                 ├── setupProxy.js (dev proxy only)
  │                 ├── context/AuthContext.js
  │                 ├── pages/
  │                 │     ├── Login.js ← api, AuthContext
  │                 │     ├── Register.js ← api
  │                 │     ├── Dashboard.js ← api, AuthContext
  │                 │     ├── Complaints.js ← api, AuthContext, ReportModal, ComplaintDetail
  │                 │     └── WardMap.js ← api
  │                 └── components/
  │                       ├── AppShell.js ← AuthContext, Sidebar, pages/*
  │                       ├── Sidebar.js ← AuthContext
  │                       ├── ReportModal.js ← api           [+ channel selector]
  │                       └── ComplaintDetail.js ← api, AuthContext  [+ notify panel → /api/channels/dispatch]
  │
  ├── frontend/Dockerfile.k8s (production)
  │     └── same src/ → npm run build → nginx static serve
  │           └── k8s/frontend/deployment.yaml (ConfigMap nginx conf)
  │
  ├── db (postgres:16-alpine)
  │     └── pgdata volume (docker) / postgres-pvc (k8s)
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

### Core

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://nagaraai:nagaraai123@localhost:5432/nagaraai_db` | SQLAlchemy connection string |
| `SECRET_KEY` | **Yes — change in prod** | `dev-secret-key` | JWT signing secret |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | Token TTL (24 h) |

### IBM watsonx.ai

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `WATSONX_API_KEY` | No | `""` | IBM Cloud API key — empty → local fallback |
| `WATSONX_PROJECT_ID` | No | `""` | watsonx project ID |
| `WATSONX_URL` | No | `https://us-south.ml.cloud.ibm.com` | watsonx regional endpoint |

### Twilio (WhatsApp / SMS / Voice)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TWILIO_ACCOUNT_SID` | No | `""` | Account SID |
| `TWILIO_AUTH_TOKEN` | No | `""` | Auth token (also used for HMAC signature verify) |
| `TWILIO_PHONE_NUMBER` | No | `""` | E.164 number for SMS/Voice |
| `TWILIO_WHATSAPP_NUMBER` | No | `""` | `whatsapp:+1…` for WhatsApp |
| `TWILIO_VERIFY_SIGNATURE` | No | `true` | Set `false` for local dev with ngrok |

### Telegram

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | No | `""` | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | No | `""` | Secret token for webhook header verification |

### Email (SMTP)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | `""` | SMTP username |
| `SMTP_PASSWORD` | No | `""` | SMTP password / app password |
| `SMTP_FROM` | No | `nagaraai@example.com` | From address |

### Meta (Facebook / Instagram)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `META_APP_SECRET` | No | `""` | App secret for X-Hub-Signature-256 verification |
| `META_VERIFY_TOKEN` | No | `nagaraai-verify` | Hub challenge verify token |
| `META_PAGE_ACCESS_TOKEN` | No | `""` | Facebook page token (outbound) |
| `META_IG_ACCESS_TOKEN` | No | `""` | Instagram business token (outbound) |

### Twitter/X

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TWITTER_API_KEY` | No | `""` | Consumer API key |
| `TWITTER_API_SECRET` | No | `""` | Consumer API secret |
| `TWITTER_ACCESS_TOKEN` | No | `""` | User access token |
| `TWITTER_ACCESS_SECRET` | No | `""` | User access token secret |
| `TWITTER_BEARER_TOKEN` | No | `""` | Bearer token (read-only streams) |

### App

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `APP_BASE_URL` | No | `https://nagaraai.example.com` | Public base URL — used in Twilio voice transcription callback |

### Frontend / Docker

| Variable | Service | Default | Purpose |
|---|---|---|---|
| `REACT_APP_PROXY_TARGET` | frontend | `http://localhost:8000` | Dev-proxy target — set `http://backend:8000` in Docker |
| `POSTGRES_USER` | db | `nagaraai` | PostgreSQL user |
| `POSTGRES_PASSWORD` | db | `nagaraai123` | PostgreSQL password |
| `POSTGRES_DB` | db | `nagaraai_db` | PostgreSQL database name |

---

## 10. Database Schema

```
users
  id PK, name, email (unique), phone (unique), hashed_password,
  role ENUM(citizen|field_officer|ward_officer|commissioner),
  ward_id FK→wards.id, is_active BOOL, created_at TIMESTAMP

wards
  id PK, name, zone, population INT,
  flood_risk_score FLOAT, cleanliness_score FLOAT

contractors
  id PK, name, contact, ward_id FK→wards.id,
  compliance_score FLOAT, total_assigned INT, total_resolved INT, created_at

complaints
  id PK, ticket_id VARCHAR(20) unique,
  title, description TEXT,
  category ENUM, priority ENUM, status ENUM,
  latitude FLOAT, longitude FLOAT, address,
  image_url, ai_classification, ai_confidence FLOAT, ai_summary TEXT,
  reporter_id FK→users.id, assignee_id FK→users.id,
  ward_id FK→wards.id, contractor_id FK→contractors.id,
  sla_deadline TIMESTAMP, resolved_at TIMESTAMP,
  citizen_rating INT(1-5), created_at, updated_at

complaint_updates
  id PK, complaint_id FK→complaints.id, updated_by FK→users.id,
  status ENUM, note TEXT, created_at

── NEW (multi-channel intake) ─────────────────────────────────────────────

inbound_messages
  id PK,
  channel ENUM(whatsapp|telegram|sms|mms|email|voice|facebook|instagram|twitter_x|web|api),
  external_id VARCHAR(255),          -- platform message ID
  sender_id VARCHAR(255),            -- phone / handle / chat_id
  sender_name VARCHAR(255),
  raw_text TEXT,                     -- original message body
  language VARCHAR(20),
  ai_transcript TEXT,                -- voice → text (from Twilio transcription)
  ai_summary TEXT,                   -- watsonx one-liner
  ai_category VARCHAR(100),
  ai_priority VARCHAR(50),
  ai_confidence FLOAT,
  location_text VARCHAR(500),
  latitude FLOAT, longitude FLOAT,
  complaint_id FK→complaints.id,     -- NULL until promoted to Complaint
  is_processed BOOL,
  metadata_ JSON,                    -- raw platform-specific extras
  created_at

media_attachments
  id PK, message_id FK→inbound_messages.id,
  media_type ENUM(image|video|audio|document|location),
  url VARCHAR(1000),
  mime_type VARCHAR(100),
  file_size_bytes INT,
  ai_description TEXT,               -- future AI image caption / transcript
  created_at

channel_dispatches
  id PK, complaint_id FK→complaints.id,
  channel ENUM,
  recipient VARCHAR(255),            -- phone / email / chat_id
  message_body TEXT,
  external_id VARCHAR(255),          -- platform message send ID
  status VARCHAR(50),                -- queued | sent | delivered | failed
  created_at
```

**Foreign key summary:**

```
users.ward_id                    → wards.id
complaints.reporter_id           → users.id
complaints.assignee_id           → users.id
complaints.ward_id               → wards.id
complaints.contractor_id         → contractors.id
contractors.ward_id              → wards.id
complaint_updates.complaint_id   → complaints.id
complaint_updates.updated_by     → users.id
inbound_messages.complaint_id    → complaints.id  (nullable)
media_attachments.message_id     → inbound_messages.id  (cascade delete)
channel_dispatches.complaint_id  → complaints.id
```

---

## 11. API Endpoint Reference

### Auth — `/api/auth`

| Method | Path | Auth | Body / Params | Returns |
|---|---|---|---|---|
| POST | `/api/auth/register` | No | `UserCreate` | `Token` |
| POST | `/api/auth/login` | No | `UserLogin` | `Token` |
| GET | `/api/auth/me` | Bearer | — | `UserOut` |

### Complaints — `/api/complaints`

| Method | Path | Auth | Body / Params | Returns |
|---|---|---|---|---|
| POST | `/api/complaints/` | Bearer | `ComplaintCreate` | `ComplaintOut` 201 |
| GET | `/api/complaints/` | Bearer | `?skip=0&limit=50` | `List[ComplaintOut]` |
| GET | `/api/complaints/{id}` | Bearer | — | `ComplaintOut` |
| PATCH | `/api/complaints/{id}` | Bearer | `ComplaintUpdate` | `ComplaintOut` |
| POST | `/api/complaints/{id}/rate` | Bearer | `ComplaintRating` | `ComplaintOut` |

### Wards — `/api/wards`

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/api/wards/` | No | `List[WardOut]` |
| GET | `/api/wards/{id}/stats` | No | `WardStats` |

### Analytics — `/api/analytics`

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/api/analytics/city` | Bearer | `CityStats` |
| GET | `/api/analytics/ward-heatmap` | Bearer | `List[WardStats]` |
| GET | `/api/analytics/contractors` | Bearer | `List[ContractorOut]` |

### Channels — `/api/channels`

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/channels/webhook/whatsapp` | None (Twilio HMAC) | Form-encoded |
| POST | `/api/channels/webhook/sms` | None (Twilio HMAC) | Form-encoded |
| POST | `/api/channels/webhook/voice` | None | Returns TwiML |
| POST | `/api/channels/webhook/voice/transcription` | None | Twilio callback |
| POST | `/api/channels/webhook/telegram` | None (secret header) | JSON Update |
| GET | `/api/channels/webhook/facebook` | None | Hub challenge |
| POST | `/api/channels/webhook/facebook` | None (SHA256) | Meta payload |
| GET | `/api/channels/webhook/instagram` | None | Hub challenge |
| POST | `/api/channels/webhook/instagram` | None (SHA256) | Meta payload |
| POST | `/api/channels/webhook/twitter` | None | Account Activity JSON |
| POST | `/api/channels/webhook/email` | None | `{from, subject, body}` |
| POST | `/api/channels/dispatch` | Bearer | `DispatchRequest` → `ChannelDispatchOut` |
| GET | `/api/channels/inbound` | Bearer | `?channel=&skip=&limit=` → `List[InboundMessageOut]` |
| GET | `/api/channels/dispatch/{id}` | Bearer | `ChannelDispatchOut` |

### System

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/health` | No | `{"status": "ok", "service": "NagaraAI"}` |
| GET | `/docs` | No | Swagger UI |
| GET | `/openapi.json` | No | OpenAPI 3 spec |
