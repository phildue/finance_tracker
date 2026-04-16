# PR Preview Deployment Design

**Date:** 2026-04-16
**Issue:** phildue/finance_tracker#5 — Implement a mechanism to verify feature branch

## Overview

Deploy an ephemeral instance of the app for each PR targeting `main`, hosted on the test server at a PR-number-derived port. The instance is torn down when the PR is closed (merged or rejected).

## Architecture

A new GitHub Actions workflow (`deploy-preview.yml`) triggers on `pull_request` events (`opened`, `synchronize`, `reopened`, `closed`) targeting `main`. It runs on the self-hosted runner, which already has SSH key access to the test server.

**Port formula:** `8000 + PR_NUMBER` (e.g., PR #5 → port 8005)

**Isolation:** Each PR instance uses Docker Compose project name `pr-<N>`, keeping containers, networks, and volumes fully separate from the permanent test deployment (project `finance_tracker`, port 80) and from other PR instances.

**Data:** Each instance gets a fresh empty database — `data/` is excluded from rsync, same as the existing deploy script.

## Components

### `docker-compose.yml` change

Make the frontend host port configurable:

```yaml
ports:
  - "${FRONTEND_PORT:-80}:80"
```

The default remains `80`, so the existing test deployment is unaffected.

### `deploy-preview.yml` workflow

**Deploy job** (runs on open/sync/reopen):

1. Checkout PR branch source
2. `rsync` to `/opt/finance_tracker_pr_<N>/` on the test server (exclude `.git/`, `data/`, `node_modules/`, `__pycache__/`, `frontend/dist/`)
3. SSH: `mkdir -p data && chown 1000:1000 data`
4. SSH: `FRONTEND_PORT=$((8000 + N)) IMAGE_TAG=local docker compose -p pr-<N> up -d --build`
5. Post PR comment (create if none, edit if exists): `"Preview deployed: http://<host>:$((8000 + N))"`

**Teardown job** (runs on close):

1. SSH: `docker compose -p pr-<N> down --volumes`
2. SSH: `rm -rf /opt/finance_tracker_pr_<N>/`
3. Post PR comment: `"Preview instance torn down."`

### Secrets / configuration

| Name | Purpose |
|------|---------|
| `DEPLOY_TEST_TARGET` | Existing — `user@host` for SSH |
| `DEPLOY_TEST_HOST` | New — bare hostname/IP for the PR comment URL |

The SSH key is already at `~/.ssh/deploy_key` on the self-hosted runner.

## Error Handling & Edge Cases

- **Concurrent pushes to the same PR:** `docker compose up -d --build` is idempotent — rebuilds and restarts in place.
- **PR closed before deploy finishes:** `docker compose down` is safe against partially-started stacks.
- **Port collisions:** impossible — PR numbers are unique, so ports never overlap.
- **Test deployment unaffected:** uses default project name and port 80; PR instances use `pr-<N>` and port `8000+N`.
- **Firewall:** the test server must have ports in the `8000+N` range open for incoming traffic. This is a manual ops step and is not automated by this workflow.

## Out of Scope

- Building and pushing Docker images to GHCR for PR branches (uses local build on the server instead)
- Running system tests against PR instances (covered by issue #8)
- Smoke tests post-deploy (covered by issue #7)
