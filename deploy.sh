#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-}"
IMAGE_TAG="${2:-}"      # optional: pull this tag from the registry instead of building
REMOTE_DIR="/opt/finance_tracker"

# SSH_KEY env var: path to a private key (set in CI; omit for manual deploys).
SSH_ARGS=(-o StrictHostKeyChecking=accept-new)
[[ -n "${SSH_KEY:-}" ]] && SSH_ARGS+=(-i "$SSH_KEY")

remote_ssh() { ssh "${SSH_ARGS[@]}" "$@"; }

if [ -z "$REMOTE" ]; then
    echo "Deploying locally..."
    docker compose build
    docker compose up -d
    echo "Done. App available at http://localhost"
else
    echo "Deploying to $REMOTE..."

    # Ensure the data directory exists and is writable by the container user (UID 1000).
    remote_ssh "$REMOTE" "mkdir -p '$REMOTE_DIR/data' && chown 1000:1000 '$REMOTE_DIR/data'"

    if [ -n "$IMAGE_TAG" ]; then
        # CI path: images are already in the registry — just pull and restart.
        remote_ssh "$REMOTE" "cd '$REMOTE_DIR' && echo IMAGE_TAG=$IMAGE_TAG > .env && docker compose pull && docker compose up -d"
    else
        # Manual path: build from the current working tree.
        rsync -az -e "ssh ${SSH_ARGS[*]}" \
            --exclude='.git/' \
            --exclude='data/' \
            --exclude='node_modules/' \
            --exclude='__pycache__/' \
            --exclude='frontend/dist/' \
            . "$REMOTE:$REMOTE_DIR"
        remote_ssh "$REMOTE" "cd '$REMOTE_DIR' && docker compose build && docker compose up -d"
    fi

    echo "Done. App available at http://${REMOTE#*@}"
fi
