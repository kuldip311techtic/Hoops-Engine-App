# Hoops Engine Apps

Backend API for the Hoops Engine basketball training platform (Coach, Player, Organization Admin, Super Admin).

## Stack

- Python 3.11+
- FastAPI
- PostgreSQL (SQLAlchemy 2 async + asyncpg)
- Alembic migrations
- OAuth2 password flow issuing JWTs (`AUTH_STRATEGY=jwt`)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pre-commit install
```

Configure `.env` (never commit secrets). Canonical JWT setting is `JWT_SECRET_KEY`; `JWT_SECRET` is accepted as an alias.

## Database

```bash
alembic upgrade head
python -m scripts.check_db
```

## Run

```bash
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/health/ready`
- Super Admin login: `POST /api/v1/auth/login` (alias `POST /api/auth/login`)

Seed the initial Super Admin (from `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD`):

```bash
python -m scripts.seed_super_admin
```

Successful login returns bearer tokens in `data`. The frontend stores them and navigates to `data.redirect_to` (dashboard). Do not expect an HTTP 302 from this API.

## Tests

```bash
pytest
```

## Response envelope

Success:

```json
{"success": true, "message": "Service is healthy", "data": {"status": "ok"}}
```

Error:

```json
{
  "success": false,
  "message": "Request validation failed",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [{"field": "field_name", "message": "Field required", "type": "missing"}]
  }
}
```
