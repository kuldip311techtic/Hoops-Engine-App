# Hoops Engine Apps

Backend API for the Hoops Engine basketball training platform (FastAPI + PostgreSQL).

## Requirements

- Python 3.11+
- PostgreSQL

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
```

Verify database connectivity:

```bash
python -m scripts.check_db
```

Run the API:

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- Health (liveness): `GET /api/v1/health`
- Health (readiness / DB ping): `GET /api/v1/health/ready`
- Super Admin login: `POST /api/super-admin/login`

Seed the initial Super Admin (after migrations):

```bash
python -m scripts.seed_super_admin
```

## Tests

```bash
pytest
```

## Linting

```bash
flake8 app tests scripts
black app tests scripts
pre-commit install
```
