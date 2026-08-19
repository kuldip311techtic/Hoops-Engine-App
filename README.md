# Hoops Engine Apps

FastAPI backend for the Hoops Engine application.

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your local database and JWT settings
alembic upgrade head
python scripts/seed_super_admin.py
```

## Run

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Verify Database

```bash
python scripts/verify_db.py
```

## Tests

```bash
pytest
```

## Lint & Format

```bash
flake8 app tests
black app tests
```

## Optional Pre-commit

```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
app/
  main.py              # ASGI entry point
  api/v1/              # Versioned REST routes
  core/                # Config, security, logging
  db/                  # Async SQLAlchemy + Alembic migrations
  models/              # ORM models
  schemas/             # Pydantic request/response DTOs
  services/            # Business logic
  repositories/        # Data access
  middleware/          # CORS, logging, rate limiting
  dependencies/        # FastAPI DI providers
  exceptions/          # Custom errors + handlers
tests/
  unit/
  integration/
scripts/
docs/
```
