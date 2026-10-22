# GoaConnect — Cybersecurity AI Force

> **Next-Generation Autonomous Multi-Agent Cybersecurity Platform + Goa Tourism AI**
> Built with Python · FastAPI · SQLite/PostgreSQL · Zero-dependency frontend SPA

[![Tests](https://img.shields.io/badge/tests-38%20passed-brightgreen)](#testing)
[![Live Tests](https://img.shields.io/badge/live%20tests-35%20passed-brightgreen)](#testing)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#installation)
[![License](https://img.shields.io/badge/license-MIT-blue)](#license)

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Project Structure](#project-structure)
6. [API Reference](#api-reference)
7. [Agent Fleet](#agent-fleet)
8. [Security Model](#security-model)
9. [Testing](#testing)
10. [Configuration](#configuration)
11. [Production Deployment](#production-deployment)
12. [Feature Status Matrix](#feature-status-matrix)
13. [Contributing](#contributing)
14. [License](#license)

---

## Overview

GoaConnect Cybersecurity AI Force is a **full-stack, modular, multi-agent cybersecurity platform** that also serves as a Goa tourism intelligence system. It demonstrates:

- **Defensive AI security** — autonomous agents detecting threats, triaging alerts, and coordinating incident response
- **Human-in-the-loop governance** — high-impact actions require explicit human approval; no agent approves its own requests
- **Secure multi-agent orchestration** — typed inputs/outputs, least-privilege permissions, deterministic policy enforcement
- **Tourism AI** — travel assistant, itinerary planner, heritage guide, and Goa place explorer
- **Zero-dependency frontend** — single HTML file served by FastAPI, no npm/Node.js required

---

## Features

### Security Platform
| Feature | Status |
|---------|--------|
| JWT authentication with refresh tokens | ✅ |
| Role-based access control (admin / security_analyst / viewer) | ✅ |
| Account lockout after 5 failed attempts | ✅ |
| Security alerts — create, filter, investigate, resolve | ✅ |
| Human approval queue for high-impact actions | ✅ |
| Append-only audit log (all events recorded) | ✅ |
| Security posture dashboard | ✅ |
| Rate limiting (slowapi, memory backend) | ✅ |
| Request ID tracing | ✅ |
| Structured JSON logging (structlog) | ✅ |

### AI Agent Fleet
| Agent | Capability |
|-------|-----------|
| Manager Agent | Routes tasks to specialist agents |
| Authentication Guardian | Detects brute force, login anomalies |
| API Security Guardian | Detects abuse patterns |
| Alert Triage Agent | Deduplicates and classifies alerts |
| Risk Prioritization Agent | Scores findings by severity and impact |
| Containment Advisor | Recommends reversible containment actions |
| Travel Assistant | AI-powered Goa travel recommendations |
| Itinerary Planner | Day-by-day trip plans with budget |
| Heritage Guide | Historical information on Goa heritage sites |
| Policy Enforcement Service | Deterministic (non-LLM) permission checks |

### Tourism & Goa
| Feature | Status |
|---------|--------|
| AI travel chat (6 quick prompts) | ✅ |
| Itinerary planner (days / budget / group size / focus) | ✅ |
| Heritage quick lookup with site chips | ✅ |
| 9 seeded Goa places (beaches, heritage, nature, markets) | ✅ |
| Full-text + tag search | ✅ |
| Source citations on all content | ✅ |
| Verified badge for curated places | ✅ |

### Frontend
| Feature | Status |
|---------|--------|
| Zero-dependency single HTML SPA | ✅ |
| Sidebar navigation with live badges | ✅ |
| Glassmorphism login with quick-access buttons | ✅ |
| Live stat cards (posture, alerts, critical, approvals) | ✅ |
| Quick agent action shortcuts on dashboard | ✅ |
| Policy checker tool | ✅ |
| Responsive layout | ✅ |
| Dark theme | ✅ |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (localhost:8000)                   │
│              Single-file HTML SPA (zero deps)                │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / JSON
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  /auth   │  │/security │  │/tourism  │  │ /agents  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Manager Agent                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │ Security │  │ Tourism  │  │  Policy Engine   │  │   │
│  │  │  Agents  │  │  Agents  │  │  (deterministic) │  │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         SQLite (dev)  /  PostgreSQL (prod)            │  │
│  │   users · alerts · approvals · audit_events · places  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Request flow:**
```
Request → Auth middleware → RBAC check → Route handler
       → Manager Agent → Specialist Agent → Policy check
       → Evidence collection → Human approval (if required)
       → Audit log → Response
```

---

## Quick Start

### Prerequisites
- Python 3.10 or higher (tested on 3.14.2)
- No Docker, no Node.js, no npm required for development

### 1 — Clone and install
```bash
git clone https://github.com/yourusername/goaConnect.git
cd goaConnect/backend
pip install -r requirements.txt
```

### 2 — Start the server
```bash
python serve.py
```

Output:
```
GoaConnect is running!
  API:    http://localhost:8000
  Docs:   http://localhost:8000/docs
  Health: http://localhost:8000/health
```

### 3 — Open the app
Navigate to **http://localhost:8000** in your browser.

### Default credentials
| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `Admin@GoaConnect1` |
| Security Analyst | `analyst` | `Analyst@GoaConnect1` |
| Guest (read-only) | `guest` | `Guest@GoaConnect1` |

### Stop the server
```bash
python stop_server.py
```

---

## Project Structure

```
goaConnect/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── static/
│   │   │   └── index.html             # Complete single-file SPA frontend
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic settings
│   │   │   ├── database.py            # Async SQLAlchemy engine
│   │   │   ├── security.py            # Password hashing, JWT
│   │   │   ├── deps.py                # FastAPI auth dependencies, RBAC
│   │   │   └── logging.py             # Structlog configuration
│   │   ├── api/v1/
│   │   │   ├── auth.py                # Register, login, refresh, whoami
│   │   │   ├── security.py            # Alerts, audit, approvals, posture
│   │   │   ├── tourism.py             # Places, itineraries, assistant
│   │   │   ├── agents.py              # Task submit, policy check, roles
│   │   │   └── health.py              # /health, /ready
│   │   ├── db/models/
│   │   │   ├── user.py                # User ORM model
│   │   │   ├── security.py            # Alert, Approval, AuditEvent models
│   │   │   └── tourism.py             # Place, Itinerary models
│   │   ├── schemas/
│   │   │   ├── auth.py                # Auth request/response schemas
│   │   │   ├── security.py            # Security schemas
│   │   │   └── tourism.py             # Tourism schemas
│   │   ├── services/security/
│   │   │   ├── audit.py               # Append-only audit log service
│   │   │   └── alert_service.py       # Alert management service
│   │   └── agents/
│   │       ├── core/
│   │       │   ├── base.py            # AgentInput/Output, BaseAgent
│   │       │   └── manager.py         # ManagerAgent, task routing
│   │       ├── security/
│   │       │   └── detection_agents.py # Auth guardian, triage, risk, containment
│   │       ├── tourism/
│   │       │   └── tourism_agents.py  # Travel, itinerary, heritage agents
│   │       └── governance/
│   │           └── policy_enforcement.py # Deterministic permission matrix
│   ├── tests/
│   │   ├── conftest.py                # SQLite in-memory, pytest-asyncio
│   │   ├── unit/test_auth.py          # 11 auth unit tests
│   │   ├── integration/test_security.py # 8 security integration tests
│   │   └── security/test_agents.py   # 19 agent + policy tests
│   ├── serve.py                       # Non-blocking server launcher
│   ├── stop_server.py                 # Stop server by PID
│   ├── start_dev.py                   # DB init + seed + uvicorn (blocking)
│   ├── live_test.py                   # 35 live HTTP endpoint tests
│   ├── run_tests.py                   # Subprocess test runner
│   ├── requirements.txt               # Python dependencies
│   ├── setup.cfg                      # pytest configuration
│   ├── dev.env                        # Development environment variables
│   └── Dockerfile                     # Container definition
├── frontend/                          # React/Vite/TypeScript scaffold
│   └── src/                           # (requires Node.js — not built)
├── scripts/
│   ├── seed_db.py                     # Database seeder
│   └── load_test.py                   # Performance benchmark
├── infra/
│   └── init-db.sql                    # PostgreSQL + PostGIS setup
├── docker-compose.yml                 # Full stack with PostgreSQL + Redis
├── .env.template                      # Environment variable template
└── README.md                          # This file
```

---

## API Reference

Base URL: `http://localhost:8000`

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/login` | None | Login, get JWT tokens |
| POST | `/api/v1/auth/refresh` | None | Refresh access token |
| GET | `/api/v1/auth/me` | Bearer | Get current user |

### Security
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/security/posture` | Bearer | System health summary |
| POST | `/api/v1/security/alerts` | Bearer + role | Create alert |
| GET | `/api/v1/security/alerts` | Bearer | List/filter alerts |
| GET | `/api/v1/security/alerts/{id}` | Bearer | Get alert by ID |
| PATCH | `/api/v1/security/alerts/{id}` | Bearer | Update alert status |
| GET | `/api/v1/security/audit` | Bearer | List audit events |
| POST | `/api/v1/security/approvals` | Bearer | Create approval request |
| GET | `/api/v1/security/approvals` | Bearer | List approval requests |
| POST | `/api/v1/security/approvals/{id}/decide` | Bearer | Approve or reject |

### Tourism
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/tourism/places` | None | List/search Goa places |
| GET | `/api/v1/tourism/places/{id}` | None | Get place details |
| POST | `/api/v1/tourism/itineraries` | Bearer | Create itinerary |

### Agents
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/agents/tasks` | Bearer | Submit agent task |
| POST | `/api/v1/agents/policy/check` | Bearer | Check action permission |
| GET | `/api/v1/agents/roles` | Bearer | View permission matrix |

### System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/ready` | None | Readiness probe |
| GET | `/docs` | None | Swagger UI (dev only) |

---

## Agent Fleet

### Task Types

| Task Type | Agent | Input | Output |
|-----------|-------|-------|--------|
| `auth_anomaly` | AuthenticationGuardian | login_events, user_id | findings, confidence |
| `alert_triage` | AlertTriageAgent | alerts[] | deduplicated alerts |
| `containment` | ContainmentAdvisor | alert_type | actions, requires_approval |
| `risk_score` | RiskPrioritizationAgent | findings[] | scored, ranked findings |
| `travel_query` | TravelAssistant | query, days, budget_inr | response, recommendations |
| `itinerary` | ItineraryPlanner | days, budget_inr, group_size | day-by-day plan |
| `heritage` | HeritageGuide | site | description, facts, citations |

### Policy Rules (enforced in code, not prompts)

```
travel_assistant     → read: tourism_places, tourism_itinerary
                     → write: tourism_itinerary
                     ✗ BLOCKED: security_alert, audit_event

authentication_guardian → read: audit_event, security_alert
                        → write: security_alert
                        ✗ BLOCKED: user_account, system_config

containment_advisor  → read: security_alert, audit_event
                     → write: security_alert [requires_approval]
                     ✗ BLOCKED: user_account
```

---

## Security Model

### Authentication
- JWT access tokens (15-minute expiry by default)
- JWT refresh tokens (7-day expiry)
- `sha256_crypt` primary hash + bcrypt fallback
- Account lockout after 5 failed attempts (15-minute lock)

### Authorization
- Roles: `admin`, `security_analyst`, `viewer`
- All permission checks enforced in backend code
- Agents operate with minimum required permissions
- Monitoring agents are read-only by default

### Audit Trail
- Every auth event, alert change, and approval decision is logged
- Audit log is append-only (no delete endpoint)
- Each event includes: timestamp, user, IP, action, outcome, agent_id

### Human Approval
- Required for: account suspension, bulk operations, production changes
- Approval expires after configurable timeout
- One agent cannot approve its own high-impact request
- All approval decisions recorded in audit log

---

## Testing

### Run unit + integration tests
```bash
cd backend
python -m pytest tests/ -v
# Expected: 38 passed
```

### Run live HTTP tests (server must be running)
```bash
python serve.py       # start server first
python live_test.py   # 35 live endpoint tests
```

### Test coverage areas
- Auth registration, login, token refresh
- RBAC enforcement per role
- Alert CRUD operations
- Approval workflow (approve / reject / double-approve)
- Audit event creation
- SQL injection protection
- Agent task routing and policy enforcement
- Tourism place search and itinerary generation

---

## Configuration

Copy `dev.env` to `.env` and adjust:

```env
DATABASE_URL=sqlite+aiosqlite:///./goaConnect_dev.db
DATABASE_URL_SYNC=sqlite:///./goaConnect_dev.db
SECRET_KEY=your-32-character-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=info
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173
RATE_LIMIT_PER_MINUTE=60
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### For PostgreSQL (production):
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/goaconnect
DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@localhost:5432/goaconnect
```

---

## Production Deployment

### With Docker Compose
```bash
docker-compose up -d
```

Services started:
- `backend` — FastAPI on port 8000
- `postgres` — PostgreSQL 15 with PostGIS
- `redis` — Redis for rate limiting and caching
- `frontend` — Nginx serving the React build

### Manual production setup
```bash
# 1. Set environment variables
export DATABASE_URL=postgresql+asyncpg://...
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export ENVIRONMENT=production

# 2. Run migrations
cd backend
alembic upgrade head

# 3. Seed database
python start_dev.py --seed-only

# 4. Start with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Feature Status Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| Authentication (JWT) | ✅ Verified | Full test coverage |
| RBAC enforcement | ✅ Verified | 3 roles tested |
| Security alerts CRUD | ✅ Verified | Filter, paginate |
| Human approval workflow | ✅ Verified | Approve/reject/expire |
| Audit log (append-only) | ✅ Verified | All events recorded |
| Security posture dashboard | ✅ Verified | Live stats |
| Rate limiting | ✅ Implemented | Memory backend |
| Manager Agent routing | ✅ Verified | Deterministic |
| Auth Guardian | ✅ Verified | Brute-force detection |
| Alert Triage Agent | ✅ Verified | Deduplication |
| Risk Prioritization | ✅ Verified | Score ranking |
| Containment Advisor | ✅ Verified | Approval required |
| Policy Enforcement | ✅ Verified | Code-enforced |
| Travel Assistant | ✅ Verified | Recommendations |
| Itinerary Planner | ✅ Verified | Day-by-day |
| Heritage Guide | ✅ Verified | Citations |
| Tourism places (9 seeded) | ✅ Verified | Search + filter |
| Single-file SPA frontend | ✅ Verified | Zero dependencies |
| Swagger API docs | ✅ Verified | /docs |
| SQLite dev database | ✅ Verified | Auto-init |
| PostgreSQL (production) | 🔶 Partial | Schema ready |
| Redis caching | 🔶 Partial | Falls back to memory |
| PostGIS geospatial | 🔶 Partial | Schema ready |
| pgvector semantic search | 🔷 Not started | Dependency installed |
| Ollama local inference | 🔷 Not started | Adapter pattern ready |
| React/Vite frontend | 🔷 Blocked | Requires Node.js |
| WebXR/AR features | 🔷 Not started | Optional milestone |
| n8n workflow integration | 🔷 Not started | Optional |

Legend: ✅ Verified · 🔶 Partial/Unverified · 🔷 Not started

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and run tests: `python -m pytest tests/ -q`
4. Run live tests: `python live_test.py`
5. Commit: `git commit -m "feat: your feature description"`
6. Push and open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Database ORM: [SQLAlchemy](https://sqlalchemy.org/)
- Goa tourism data: Goa Tourism Official Website, UNESCO, ASI, Goa Forest Department
- Developed using [IBM Bob](https://www.ibm.com/products/bob) AI-assisted development

---

*GoaConnect Cybersecurity AI Force — Defending digital Goa, one agent at a time. 🛡🌴*
