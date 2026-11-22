# 🏙️ NagaraAI — Bengaluru Civic Intelligence Platform

End-to-end civic issue management platform built with **React (JS)**, **FastAPI (Python)**, **PostgreSQL**, and **IBM watsonx.ai**. Citizens can report civic issues via the web portal or **9 external channels** — WhatsApp, SMS/MMS, Voice, Telegram, Email, Facebook, Instagram, and Twitter/X.

> **Test status:** 75 tests passing · Docker Compose + Kubernetes ready

---

## 🗂️ Project Structure

```
nagaraai/
├── backend/                  # FastAPI + Python 3.12
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── models.py         # SQLAlchemy ORM models + enums
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── auth.py           # JWT authentication + role guards
│   │   ├── watsonx.py        # IBM watsonx.ai integration + local fallback
│   │   ├── config.py         # Settings from .env (40+ vars)
│   │   ├── database.py       # DB session + engine
│   │   ├── routes/
│   │   │   ├── auth.py       # /api/auth/*
│   │   │   ├── complaints.py # /api/complaints/*
│   │   │   ├── wards.py      # /api/wards/*
│   │   │   ├── analytics.py  # /api/analytics/*
│   │   │   └── channels.py   # /api/channels/* (webhooks + dispatch)
│   │   └── channels/         # Multi-channel adapters
│   │       ├── dispatcher.py # Central AI dispatcher
│   │       ├── whatsapp.py   # Twilio WhatsApp
│   │       ├── sms.py        # Twilio SMS/MMS
│   │       ├── voice.py      # Twilio Voice TwiML
│   │       ├── telegram.py   # Telegram Bot API
│   │       ├── email_chan.py  # SMTP + inbound email parser
│   │       └── social.py     # Facebook / Instagram / Twitter-X
│   ├── tests/                # 75 pytest tests
│   ├── seed.py               # Seed demo data
│   ├── requirements.txt
│   └── Dockerfile / Dockerfile.test
├── frontend/                 # React 18
│   └── src/
│       ├── pages/            # Login, Register, Dashboard, Complaints, WardMap
│       ├── components/       # AppShell, Sidebar, ReportModal, ComplaintDetail
│       └── setupProxy.js     # Docker-safe API proxy
├── k8s/                      # Kubernetes manifests (kind + skaffold)
├── docker-compose.yml
├── SETUP.md                  # Detailed setup + operations guide
├── CODEBASE.md               # Full file-by-file reference
└── nagaraai-guide.html       # 7-tab interactive architecture guide
```

---

## 🚀 Quick Start (Local Dev)

### Prerequisites
- Docker Desktop (recommended) **or** Python 3.12+, Node 20+, PostgreSQL 15+

### Option A: Docker Compose (recommended)

```bash
cd nagaraai
docker compose up --build
```

Then seed the database:
```bash
docker compose exec backend python seed.py
```

Access: **http://localhost:3000** (frontend) · **http://localhost:8000/docs** (API)

### Option B: Manual

**Backend:**
```bash
cd nagaraai/backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
copy .env.example .env         # Edit DATABASE_URL etc.
python seed.py
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd nagaraai/frontend
npm install
npm start
```

---

## 🧪 Running Tests

```bash
# Build and run the full test suite in Docker (no Postgres needed)
docker build -f backend/Dockerfile.test -t nagaraai-test ./backend
docker run --rm nagaraai-test
# → 75 passed in ~4.6s
```

---

## 🔐 Demo Logins

| Role | Email | Password |
|---|---|---|
| Citizen | citizen@demo.com | demo1234 |
| Field Officer | field@demo.com | demo1234 |
| Ward Officer | ward@demo.com | demo1234 |
| Commissioner | commissioner@demo.com | demo1234 |

---

## 🤖 IBM watsonx.ai Integration

Set in `backend/.env`:
```
WATSONX_API_KEY=your-ibm-api-key
WATSONX_PROJECT_ID=your-project-id
```

Without credentials the app uses a **built-in rule-based classifier** (zero external dependencies for demo).

With credentials it calls `ibm/granite-13b-instruct-v2` to:
- Classify complaint category (Kannada/English NLP)
- Assign priority (low/medium/high/critical)
- Generate a plain-language summary
- Auto-set SLA deadline

---

## 📡 Multi-Channel Intake

Citizens can report issues via any channel — NagaraAI classifies and acknowledges automatically:

| Channel | Webhook | Technology |
|---|---|---|
| WhatsApp | `POST /api/channels/webhook/whatsapp` | Twilio |
| SMS / MMS | `POST /api/channels/webhook/sms` | Twilio |
| Voice call | `POST /api/channels/webhook/voice` | Twilio TwiML |
| Telegram | `POST /api/channels/webhook/telegram` | Telegram Bot API |
| Email | `POST /api/channels/webhook/email` | SMTP / MTA parse |
| Facebook | `POST /api/channels/webhook/facebook` | Meta Graph API |
| Instagram | `POST /api/channels/webhook/instagram` | Meta Graph API |
| Twitter/X | `POST /api/channels/webhook/twitter` | Account Activity API |

Officers can send status notifications back to citizens on any channel from the complaint detail view.

---

## 📋 API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login → JWT token |
| GET | `/api/auth/me` | Current user |

### Complaints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/complaints/` | File a complaint (AI classifies) |
| GET | `/api/complaints/` | List complaints (role-scoped) |
| PATCH | `/api/complaints/{id}` | Update status/assign |
| POST | `/api/complaints/{id}/rate` | Citizen rates resolution |

### Analytics
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/analytics/city` | City-wide KPIs |
| GET | `/api/analytics/ward-heatmap` | Per-ward risk data |
| GET | `/api/analytics/contractors` | Contractor leaderboard |

### Channels
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/channels/webhook/*` | 9 inbound channel webhooks |
| POST | `/api/channels/dispatch` | Send notification on any channel |
| GET | `/api/channels/inbound` | List inbound messages |
| GET | `/api/channels/dispatch/{id}` | Dispatch status |

Interactive docs: **http://localhost:8000/docs**

---

## 🎯 Single-Window UX

One URL, role-adaptive interface:
- **Citizen** — Report issues via web or any channel, track status, rate resolution
- **Field Officer** — Task list, one-tap status updates, send notifications
- **Ward Officer** — Heat map, dispatch, SLA dashboard, multi-channel alerts
- **Commissioner** — City KPIs, contractor compliance, flood risk analytics

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Recharts, Leaflet |
| Backend | FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| AI | IBM watsonx.ai (Granite-13B), rule-based fallback |
| Auth | JWT (python-jose + bcrypt) |
| Channels | Twilio, Telegram Bot API, Meta Graph API, Twitter/X DM API |
| Infra | Docker Compose, Kubernetes (kind + skaffold) |
| Tests | pytest 8.2, pytest-asyncio — **75 tests** |
