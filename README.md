# Climate-View
An API that tracks current climate threats, their corporate backings and organisations apposing them

Live API:
https://web-production-20ec6.up.railway.app
Documentation:
https://web-production-20ec6.up.railway.app/docs


# Climate Threat & Resistance Tracker API

A fully deployed RESTful API that maps large-scale environmental threats — oil pipelines, deforestation actors, polluters — and the civil society organisations opposing them. Built with FastAPI, PostgreSQL, and deployed live on Railway.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Railway](https://img.shields.io/badge/Deployed-Railway-0B0D0E?style=flat&logo=railway)](https://web-production-20ec6.up.railway.app)
[![Tests](https://img.shields.io/badge/Tests-44%20passing-brightgreen?style=flat)]()

---

## Links

Live API: https://web-production-20ec6.up.railway.app
Documentation: https://web-production-20ec6.up.railway.app/docs
Interactive Docs (Swagger UI): https://web-production-20ec6.up.railway.app/docs |
API Documentation (PDF): [docs/api_documentation.pdf](./docs/api_documentation.pdf) |

---

## Project Structure

```
app/
├── main.py               # Application entry point, middleware, router registration
├── dependencies.py       # Shared FastAPI dependencies (auth, DB session)
├── core/
│   ├── config.py         # Pydantic settings, environment variable loading
│   ├── database.py       # Async SQLAlchemy engine and session factory
│   └── security.py       # JWT creation, password hashing (bcrypt)
├── models/               # SQLAlchemy ORM table definitions
├── schemas/              # Pydantic request/response schemas
├── routers/              # FastAPI route handlers (one file per resource)
└── services/             # Business logic decoupled from HTTP layer
```

**Request flow:** `routers → services → models → PostgreSQL`

---

## Endpoints Overview

| Group | Base Path | Auth Required | Description |
|-------|-----------|---------------|-------------|
| Authentication | `/auth` | Partial | Register, login, current user |
| Threats | `/threats` | Partial | Full CRUD + filtering + pagination |
| Companies | `/companies` | Partial | Full CRUD + linked threats |
| Organisations | `/organisations` | Partial | Full CRUD + linked campaigns |
| Campaigns | `/campaigns` | Partial | Full CRUD |
| Analytics | `/analytics` | No | 11 analytical endpoints + composite risk score |

Full endpoint reference with parameters, request bodies, and example responses is available in the [API Documentation PDF](./docs/api_documentation.pdf) or interactively at `/docs`.

---

## Local Setup

### Prerequisites

- Python 3.14+
- PostgreSQL (local instance or connection string to a remote instance)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/CodingOz/Climate-Threat-and-Resistance-Tracker.git
cd climate-threat-tracker
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. **Do not commit this file.** It is listed in `.gitignore`.

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/climate_tracker
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost/db` |
| `SECRET_KEY` | JWT signing secret — use a long random string in production | `changeme` |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `30` |

### 5. Apply database migrations

```bash
alembic upgrade head
```

### 6. Seed the database with real-world data

```bash
python seed.py
```

This populates the database with real-world cases including Rosebank Oilfield, the Willow Project, the East African Crude Oil Pipeline (EACOP), and JBS Amazon deforestation.

### 7. Run the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Swagger UI: `http://localhost:8000/docs`

---

## Running Tests

The test suite uses `pytest-asyncio` and `httpx` against an isolated test database.

### Prerequisites

Create a test database and set the test connection string. The suite derives the test URL automatically from `DATABASE_URL` by string replacement — ensure your local PostgreSQL has a `climate_test_db` database:

```bash
createdb climate_test_db
```

### Run all tests

```bash
pytest tests/ -v
```

Expected output: **44 tests, 0 warnings.**

Tests cover: happy-path CRUD, 401 unauthorised rejections, 403 forbidden role violations, 404 not-found cases, 422 validation failures, analytics endpoints, and the composite risk score calculation.

---

## Authentication

The API uses JWT Bearer token authentication with role-based access control.

**Roles:** `ADMIN` · `CONTRIBUTOR` · `READER`

```bash
# 1. Register
POST /auth/register
{
  "email": "user@example.com",
  "username": "string",
  "password": "string",
  "role": "READER"
}

# 2. Login — returns access token
POST /auth/token
form-data: username=user@example.com, password=string

# 3. Use token in subsequent requests
Authorization: Bearer <access_token>
```

Tokens expire after 30 minutes. Full authentication documentation is in the [API Documentation PDF](./docs/api_documentation.pdf).

---

## Rate Limiting

| Endpoint Group | Limit |
|---------------|-------|
| Read endpoints | 100 requests / minute |
| Write endpoints | 20 requests / minute |
| Analytics endpoints | 60 requests / minute |

Limits are applied per IP address. Exceeding a limit returns `429 Too Many Requests`.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.115 with Starlette |
| Database | PostgreSQL 18 |
| ORM | SQLAlchemy 2.0 (async) with asyncpg driver |
| Migrations | Alembic with versioned migration history |
| Authentication | python-jose (JWT), passlib + bcrypt |
| Rate Limiting | slowapi |
| Testing | pytest-asyncio, httpx |
| Deployment | Railway (auto-deploy from GitHub, pre-deploy migrations) |
| Documentation | Swagger UI (auto-generated), ReDoc, PDF export |

---

## Deployment Notes

The live deployment on Railway is configured with:

- **Pre-deploy command:** `alembic upgrade head` — migrations are applied atomically before traffic is served
- **Environment variables:** injected via Railway's environment variable management — no secrets in the repository
- **Database:** Railway-managed PostgreSQL 18 instance

---

## Academic Context

This project was developed as Coursework 1 for COMP3011 Web Services and Web Data at the University of Leeds (2025–2026). The technical report, GenAI declaration, and supplementary materials are submitted separately via Minerva.
