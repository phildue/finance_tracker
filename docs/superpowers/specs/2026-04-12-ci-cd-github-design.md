# CI/CD via GitHub Actions — Design

**Date:** 2026-04-12
**Scope:** Push repo to GitHub, establish CI quality gates, automated deployment on merge to main via self-hosted runner

---

## Overview

This slice wires the finance tracker into a GitHub-based CI/CD pipeline. A self-hosted GitHub Actions runner on the local PVE server executes all workflows, keeping both CI and deployment within the local network. Merging to `main` is the only path to production.

---

## Architecture

```
GitHub repo
  │
  ├── push / PR → ci.yml        (self-hosted runner)
  │                │
  │                ├── job: backend  (ruff + pytest)
  │                ├── job: frontend (tsc + npm build)
  │                └── job: system   (docker compose smoke test)
  │
  └── push to main → deploy.yml  (self-hosted runner, after ci.yml passes)
                      │
                      └── rsync + SSH → deployment VM → docker compose up
```

The self-hosted runner is provisioned on a PVE VM/LXC (separate from the deployment target). The deployment target is a separate VM reachable over the local network via SSH.

---

## File Changes

### `.gitignore`

Add two missing entries:
- `node_modules/` — was absent; would be committed without this
- `frontend/dist/` — build output, not for version control

### `backend/requirements-dev.txt`

Add `ruff` — used as the linter in the CI backend job.

### `backend/adapters/api/routes.py`

Add `GET /health` — returns `{"status": "ok"}` with HTTP 200. Used by the smoke test to verify the backend is up. No business logic, no database access.

### `.github/workflows/ci.yml`

Triggers on every push and pull request targeting `main`. Runs on `self-hosted`.

**Job: `backend`**
```
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest -v
```

**Job: `frontend`**
```
cd frontend
npm ci
npx tsc --noEmit
npm run build
```

Both jobs run in parallel. A failure in either surfaces independently.

**Job: `system`** (depends on `backend` + `frontend` both passing)

Builds the full Docker stack, waits for the backend to respond, then tears down:
```
docker compose build
docker compose up -d
# retry curl GET http://localhost/health until 200 or timeout
docker compose down
```

The backend gains a `GET /health` endpoint (returns `{"status": "ok"}`, 200) to give the smoke test a stable, lightweight target. Catches Docker build regressions and service wiring failures that unit/type checks cannot.

### `.github/workflows/deploy.yml`

Triggers on push to `main`, gated by `ci.yml` completing successfully (`workflow_run` event).

**Job: `deploy`**
1. Checkout repo
2. Write `DEPLOY_SSH_KEY` secret to `~/.ssh/id_rsa`
3. rsync source to `DEPLOY_TARGET:/opt/finance_tracker` (excluding `data/`, `node_modules/`, `__pycache__/`, `frontend/dist/`)
4. SSH into `DEPLOY_TARGET`: `cd /opt/finance_tracker && docker compose build && docker compose up -d`

**Required GitHub Actions secrets:**
| Secret | Value |
|---|---|
| `DEPLOY_SSH_KEY` | Private SSH key (runner → deployment VM) |
| `DEPLOY_TARGET` | `user@192.168.x.x` (deployment VM address) |

### `docs/runner-setup.md`

Documents how to provision the self-hosted runner on PVE. Not automated — a human-readable checklist. See Runner Setup section below.

---

## Self-Hosted Runner

The runner is a PVE VM or LXC container. It is distinct from the deployment target VM.

**Prerequisites on the runner machine:**
- Docker engine + Docker Compose plugin (`sudo apt-get install docker-compose-plugin`)
- The runner OS user added to the `docker` group
- SSH key pair generated; private key added as `DEPLOY_SSH_KEY` secret in GitHub; public key added to `~/.ssh/authorized_keys` on the deployment VM

**Registration:**
GitHub → repo → Settings → Actions → Runners → New self-hosted runner. Follow the Linux instructions to download and configure the runner binary. Run as a systemd service for persistence.

The `runs-on: self-hosted` label in both workflow files targets this runner.

---

## Out of Scope for This Slice

- E2E browser tests (Playwright) — own vertical slice later
- Additional quality gates (mypy, stricter linting rules) — extend `ci.yml` later
- Multiple environments (staging vs production)
- Container registry (Docker Hub / GHCR) — current approach builds on the deployment VM directly
