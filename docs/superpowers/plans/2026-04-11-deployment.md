# Finance Tracker — Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the app as two Docker containers (nginx frontend + uvicorn backend) managed by Docker Compose, with a `deploy.sh` script that deploys locally or to a remote host over SSH.

**Architecture:** nginx container serves the built React app and proxies `/expenses` to the FastAPI container. SQLite database is persisted via a bind mount at `./data/` on the host. Both containers start automatically on boot via `restart: unless-stopped`.

**Tech Stack:** Docker, Docker Compose plugin, nginx:alpine, node:20-alpine, python:3.11-slim, bash + rsync (deploy script)

---

## File Map

```
finance_tracker/             ← repo root
├── .dockerignore            # keeps build context lean
├── docker-compose.yml       # orchestrates backend + frontend services
├── deploy.sh                # build + start locally or on remote via SSH
├── backend/
│   ├── Dockerfile           # python:3.11-slim, runs uvicorn
│   └── adapters/api/main.py # modified: reads DB_PATH env var
└── frontend/
    ├── Dockerfile           # multi-stage: node builds, nginx serves
    └── nginx.conf           # serves static files + proxies /expenses
```

---

## Task 1: Install Docker Compose plugin

**Files:** none (system setup)

The Docker engine is installed but the Compose plugin is not. All subsequent tasks require it.

- [ ] **Step 1: Install the plugin**

```bash
sudo apt-get update && sudo apt-get install -y docker-compose-plugin
```

- [ ] **Step 2: Verify**

```bash
docker compose version
```

Expected output (version may vary):
```
Docker Compose version v2.x.x
```

- [ ] **Step 3: Verify Docker daemon is accessible without sudo (optional but convenient)**

```bash
docker ps
```

If you see `permission denied`, run:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Task 2: Update backend to read DB_PATH from environment

**Files:**
- Modify: `backend/adapters/api/main.py`

This is the only code change to the application itself. The fallback keeps local dev working unchanged.

- [ ] **Step 1: Update `backend/adapters/api/main.py`**

Replace the file contents with:

```python
import os

from fastapi import FastAPI

from adapters.sqlite_repository import SqliteExpenseRepository
from adapters.api.routes import build_router
from domain.use_cases import AddExpense, ListExpenses

app = FastAPI(title="Finance Tracker")

_db_path = os.environ.get("DB_PATH", "expenses.db")
_repo = SqliteExpenseRepository(_db_path)
app.include_router(build_router(AddExpense(_repo), ListExpenses(_repo)))
```

- [ ] **Step 2: Run existing tests to confirm nothing broke**

```bash
cd backend && pytest -v
```

Expected: `16 passed`

- [ ] **Step 3: Commit**

```bash
git add backend/adapters/api/main.py
git commit -m "feat: read DB_PATH from environment variable"
```

---

## Task 3: Add .dockerignore

**Files:**
- Create: `.dockerignore`

Keeps the Docker build context small — without this, `node_modules/`, `.git/`, and build artifacts are sent to the daemon on every build.

- [ ] **Step 1: Create `.dockerignore` at the repo root**

```
.git
data/
node_modules/
frontend/dist/
**/__pycache__/
**/*.pyc
.pytest_cache/
backend/expenses.db
```

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore"
```

---

## Task 4: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

Build context is always the **repo root** (set in `docker-compose.yml`), so paths in the Dockerfile are relative to the repo root.

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
CMD ["uvicorn", "adapters.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Build and verify**

Run from the repo root:

```bash
docker build -f backend/Dockerfile -t finance-tracker-backend .
```

Expected: build completes, final line is something like:
```
=> exporting to image
=> => naming to docker.io/library/finance-tracker-backend
```

- [ ] **Step 3: Confirm the container starts and the app imports correctly**

```bash
docker run --rm finance-tracker-backend python -c "from adapters.api.main import app; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Remove the test image**

```bash
docker rmi finance-tracker-backend
```

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: add backend Dockerfile"
```

---

## Task 5: Frontend nginx config and Dockerfile

**Files:**
- Create: `frontend/nginx.conf`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /expenses {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
# Stage 1: build React app
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
```

- [ ] **Step 3: Build and verify**

Run from the repo root:

```bash
docker build -f frontend/Dockerfile -t finance-tracker-frontend .
```

Expected: build completes (this will take a minute — npm ci downloads packages).

- [ ] **Step 4: Confirm nginx config is valid inside the image**

```bash
docker run --rm finance-tracker-frontend nginx -t
```

Expected:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

- [ ] **Step 5: Remove the test image**

```bash
docker rmi finance-tracker-frontend
```

- [ ] **Step 6: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: add frontend Dockerfile and nginx config"
```

---

## Task 6: docker-compose.yml and smoke test

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml` at the repo root**

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      - DB_PATH=/data/expenses.db
    volumes:
      - ./data:/data
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

- [ ] **Step 2: Build both images**

```bash
docker compose build
```

Expected: both `backend` and `frontend` build successfully.

- [ ] **Step 3: Start the stack**

```bash
docker compose up -d
```

Expected:
```
[+] Running 2/2
 ✔ Container finance_tracker-backend-1   Started
 ✔ Container finance_tracker-frontend-1  Started
```

- [ ] **Step 4: Wait for services to be ready, then smoke test**

```bash
sleep 3
curl -s http://localhost/expenses
```

Expected: `[]`

```bash
curl -s -X POST http://localhost/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount": "9.99", "currency": "EUR", "category": "test", "date": "2026-04-11"}'
```

Expected: JSON with `id`, `amount`, `currency`, `category`, `date`, `description: null`

```bash
curl -s http://localhost/expenses
```

Expected: JSON array with one expense.

- [ ] **Step 5: Verify the data directory and database were created**

```bash
ls data/
```

Expected: `expenses.db`

- [ ] **Step 6: Stop and clean up the test data**

```bash
docker compose down
rm -rf data/
```

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml"
```

---

## Task 7: deploy.sh

**Files:**
- Create: `deploy.sh`

- [ ] **Step 1: Create `deploy.sh` at the repo root**

```bash
#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-}"
REMOTE_DIR="/opt/finance_tracker"

if [ -z "$REMOTE" ]; then
    echo "Deploying locally..."
    docker compose build
    docker compose up -d
    echo "Done. App available at http://localhost"
else
    echo "Deploying to $REMOTE..."
    ssh "$REMOTE" "mkdir -p $REMOTE_DIR"
    rsync -az \
        --exclude='.git/' \
        --exclude='data/' \
        --exclude='node_modules/' \
        --exclude='__pycache__/' \
        --exclude='frontend/dist/' \
        . "$REMOTE:$REMOTE_DIR"
    ssh "$REMOTE" "cd $REMOTE_DIR && docker compose build && docker compose up -d"
    echo "Done. App available at http://$REMOTE"
fi
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x deploy.sh
```

- [ ] **Step 3: Run local deploy and verify**

```bash
./deploy.sh
```

Expected:
```
Deploying locally...
...
Done. App available at http://localhost
```

```bash
sleep 3 && curl -s http://localhost/expenses
```

Expected: `[]`

- [ ] **Step 4: Stop the stack**

```bash
docker compose down
rm -rf data/
```

- [ ] **Step 5: Commit**

```bash
git add deploy.sh
git commit -m "feat: add deploy.sh for local and remote deployment"
```

---

## Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Append a Deployment section to `CLAUDE.md`**

Add the following after the existing content:

```markdown
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

The app is served on port 80. The `data/` directory is created automatically on first run and holds `expenses.db`.

**Prerequisites on the target machine:** Docker engine + Docker Compose plugin (`sudo apt-get install docker-compose-plugin`).
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add deployment instructions to CLAUDE.md"
```
