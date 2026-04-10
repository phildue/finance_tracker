# Finance Tracker — Deployment Design

**Date:** 2026-04-11
**Scope:** Docker Compose deployment, local and remote, with a single deploy script

---

## Overview

The app runs as two Docker containers managed by Docker Compose, accessible on port 80 of the host machine (local or LAN). A `deploy.sh` script builds and starts the containers from the current directory — no git operations involved. The same script accepts an optional `user@host` argument to deploy to a remote machine over SSH.

---

## Architecture

```
[ Browser on LAN ]
        │  :80
        ▼
┌─────────────────────┐
│  frontend container │  nginx — serves built React static files
│                     │  proxies /expenses → backend:8000
└─────────┬───────────┘
          │  internal Docker network
          ▼
┌─────────────────────┐
│  backend container  │  uvicorn — FastAPI app
│                     │  reads/writes /data/expenses.db
└─────────────────────┘
          │
    bind mount: ./data:/data  (survives rebuilds)
```

- The **frontend container** uses a multi-stage build: Node builds the React app, nginx serves the output.
- The **backend container** runs uvicorn on port 8000, internal only (no host port binding).
- The **nginx** config serves static files at `/` (with SPA fallback) and proxies `/expenses` to `http://backend:8000`.
- Both containers use Docker's default network; `frontend` reaches `backend` by service name.
- `restart: unless-stopped` ensures both services survive reboots.

---

## Files

```
finance_tracker/
├── docker-compose.yml
├── deploy.sh
├── backend/
│   └── Dockerfile
├── frontend/
│   ├── Dockerfile
│   └── nginx.conf
└── data/                  # created on first run; holds expenses.db
```

---

## Backend changes

`backend/adapters/api/main.py` updated to read the database path from an environment variable:

```python
import os
DB_PATH = os.environ.get("DB_PATH", "expenses.db")
_repo = SqliteExpenseRepository(DB_PATH)
```

This keeps the local dev workflow unchanged (no env var → falls back to `expenses.db` in cwd) while allowing Docker to point it at `/data/expenses.db`.

---

## docker-compose.yml

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

---

## backend/Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
CMD ["uvicorn", "adapters.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## frontend/Dockerfile

```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
```

---

## frontend/nginx.conf

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

---

## deploy.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-}"
REMOTE_DIR="/opt/finance_tracker"

if [ -z "$REMOTE" ]; then
    docker compose build
    docker compose up -d
else
    ssh "$REMOTE" "mkdir -p $REMOTE_DIR"
    rsync -az \
        --exclude='.git/' \
        --exclude='data/' \
        --exclude='node_modules/' \
        --exclude='__pycache__/' \
        --exclude='frontend/dist/' \
        . "$REMOTE:$REMOTE_DIR"
    ssh "$REMOTE" "cd $REMOTE_DIR && docker compose build && docker compose up -d"
fi
```

**Usage:**
- `./deploy.sh` — deploy locally
- `./deploy.sh phil@192.168.1.10` — deploy to remote machine over SSH

rsync excludes `.git/`, `data/` (database stays on the remote between deploys), `node_modules/`, build artifacts, and Python cache. Docker builds happen on the target machine.

---

## Out of scope

- TLS / HTTPS (LAN only, no public domain)
- CI/CD integration (deploy.sh is designed to be called by CI — no changes needed)
- Database backups
- Log aggregation
