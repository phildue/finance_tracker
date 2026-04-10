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
    ssh "$REMOTE" "mkdir -p '$REMOTE_DIR' '$REMOTE_DIR/data'"
    rsync -az \
        --exclude='.git/' \
        --exclude='data/' \
        --exclude='node_modules/' \
        --exclude='__pycache__/' \
        --exclude='frontend/dist/' \
        . "$REMOTE:$REMOTE_DIR"
    ssh "$REMOTE" "cd '$REMOTE_DIR' && docker compose build && docker compose up -d"
    echo "Done. App available at http://${REMOTE#*@}"
fi
