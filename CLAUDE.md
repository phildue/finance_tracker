# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

Hexagonal (Ports & Adapters). `backend/domain/` has zero external dependencies — it never imports from `adapters/`. `backend/adapters/` imports from `domain/`. The only file that names concrete types from both sides is `backend/adapters/api/main.py` (the composition root).

## Running the backend

```bash
cd backend
pip install -r requirements-dev.txt   # first time only (includes dev deps)
uvicorn adapters.api.main:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Running the frontend

```bash
cd frontend
npm install                           # first time only
npm run dev
```

UI available at `http://localhost:5173`. Dev proxy forwards `/expenses` to `http://localhost:8000` — no CORS config needed.

## Running backend tests

```bash
cd backend
pytest -v
```

Run a single test:
```bash
cd backend && pytest tests/test_use_cases.py::test_add_expense_returns_saved_expense -v
```

Domain tests (`test_use_cases.py`) use `FakeExpenseRepository` — no SQLite, no HTTP. API tests (`test_api.py`) use `TestClient` with a temp SQLite file.

## Key conventions

- Pydantic request/response models live in `adapters/api/routes.py`, not in `domain/`
- `amount` is always `Decimal`, never `float`; stored as `TEXT` in SQLite
- Sorting of expenses by date is the use case's responsibility, not the repository's
- TypeScript uses `verbatimModuleSyntax` — use `import type` for type-only imports

## Deployment

**Local:**
```bash
./deploy.sh
```

**Remote (SSH):**
```bash
./deploy.sh user@hostname
```

The script builds Docker images from the current directory (no git pull) and starts the stack with `docker compose up -d`. On remote deployments, rsync copies the source to `/opt/finance_tracker` on the target — the `data/` directory (SQLite database) is excluded from rsync so it persists between deploys.

The app is served on port 80. The `data/` directory (holding `expenses.db`) is pre-created via `data/.gitkeep` and will be populated on first run.

**Prerequisites on the target machine:** Docker engine + Docker Compose plugin (`sudo apt-get install docker-compose-plugin`).
