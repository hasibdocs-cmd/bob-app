# 🏙️ NagaraAI — Bengaluru Civic Intelligence Platform

End-to-end civic issue management platform built with **React (JS)**, **FastAPI (Python)**, **PostgreSQL**, and **IBM watsonx.ai**.

---

## 🗂️ Project Structure

```
nagaraai/
├── backend/                  # FastAPI + Python
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── auth.py           # JWT authentication
│   │   ├── watsonx.py        # IBM watsonx.ai integration
│   │   ├── config.py         # Settings from .env
│   │   ├── database.py       # DB session + engine
│   │   └── routes/
│   │       ├── auth.py       # /api/auth/*
│   │       ├── complaints.py # /api/complaints/*
│   │       ├── wards.py      # /api/wards/*
│   │       └── analytics.py  # /api/analytics/*
│   ├── seed.py               # Seed demo data
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # React JS
│   ├── src/
│   │   ├── App.js            # Root with routing
│   │   ├── api.js            # Axios client
│   │   ├── index.css         # Global styles
│   │   ├── context/
│   │   │   └── AuthContext.js
│   │   ├── pages/
│   │   │   ├── Login.js
│   │   │   ├── Register.js
│   │   │   ├── Dashboard.js  # City analytics + charts
│   │   │   ├── Complaints.js # Issue list + filters
│   │   │   └── WardMap.js    # Leaflet risk map
│   │   └── components/
│   │       ├── AppShell.js   # Layout wrapper
│   │       ├── Sidebar.js    # Role-adaptive navigation
│   │       ├── ReportModal.js      # Citizen report form
│   │       └── ComplaintDetail.js  # Detail + status updates
│   └── Dockerfile
└── docker-compose.yml
```

---

## 🚀 Quick Start (Local Dev)

### Prerequisites
- Python 3.12+, Node 20+, PostgreSQL 15+ (or Docker)

### Option A: Docker Compose (recommended)

```bash
cd nagaraai
docker-compose up --build
```

Then seed the database:
```bash
docker-compose exec backend python seed.py
```

### Option B: Manual

**Backend:**
```bash
cd nagaraai/backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
copy .env.example .env         # Edit DATABASE_URL etc.
python seed.py                 # Creates tables + demo data
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd nagaraai/frontend
npm install
npm start
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

Without credentials, the app uses a **built-in rule-based classifier** (zero external dependency for demo).

With credentials, it calls `ibm/granite-13b-instruct-v2` to:
- Classify complaint category (Kannada/English NLP)
- Assign priority (low/medium/high/critical)
- Generate a plain-language summary
- Auto-set SLA deadline

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login → JWT token |
| GET | `/api/auth/me` | Current user |
| POST | `/api/complaints/` | File a complaint (AI classifies) |
| GET | `/api/complaints/` | List complaints (role-scoped) |
| PATCH | `/api/complaints/{id}` | Update status/assign |
| POST | `/api/complaints/{id}/rate` | Citizen rates resolution |
| GET | `/api/analytics/city` | City-wide KPIs |
| GET | `/api/analytics/ward-heatmap` | Per-ward risk data |
| GET | `/api/analytics/contractors` | Contractor leaderboard |
| GET | `/api/wards/` | List wards |

Interactive docs: **http://localhost:8000/docs**

---

## 🎯 Single Window UX

One URL, role-adaptive interface:
- **Citizen** — Report issues, track status, rate resolution
- **Field Officer** — Task list, one-tap status updates
- **Ward Officer** — Heat map, dispatch, SLA dashboard
- **Commissioner** — City KPIs, contractor compliance, flood risk

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Recharts, Leaflet |
| Backend | FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| AI | IBM watsonx.ai (Granite-13B), rule-based fallback |
| Auth | JWT (python-jose + bcrypt) |
| Infra | Docker Compose |
