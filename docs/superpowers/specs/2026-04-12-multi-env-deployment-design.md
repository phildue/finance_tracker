# Multi-Environment Deployment via GHCR — Design

**Date:** 2026-04-12
**Scope:** Registry-based build-once/deploy-everywhere pipeline with test (auto on merge) and prod (on GitHub Release) environments

---

## Overview

Replace the current rsync+build deployment with a container registry pipeline. Images are built once on a GitHub-hosted runner, pushed to GitHub Container Registry (GHCR), and pulled by each deployment target. Test deploys automatically on every merge to main. Prod deploys when a GitHub Release is published, using the exact same image that ran on test.

---

## Architecture

```
merge to main
  → ci.yml (self-hosted): tests pass
  → build.yml:
      job build (ubuntu-latest): docker build → push GHCR
          ghcr.io/phildue/finance_tracker/backend:sha-<short-sha>
          ghcr.io/phildue/finance_tracker/backend:test
          ghcr.io/phildue/finance_tracker/frontend:sha-<short-sha>
          ghcr.io/phildue/finance_tracker/frontend:test
      job deploy-test (self-hosted): SSH → IMAGE_TAG=sha-xxx docker compose pull && up

create GitHub Release (e.g. v1.2.0)
  → deploy-prod.yml (self-hosted):
      re-tag sha-xxx → v1.2.0 + prod in GHCR (no rebuild)
      SSH → IMAGE_TAG=v1.2.0 docker compose pull && up
```

**Key properties:**
- Build step runs on `ubuntu-latest` (GitHub-hosted) — has Docker built-in, no local network needed
- Deploy steps run on `self-hosted` — only need SSH, never Docker
- The Docker-on-LXC runner issue is irrelevant to this pipeline
- Prod always runs the image that was tested, not a fresh build

---

## File Changes

| Action | Path | Purpose |
|---|---|---|
| Modify | `docker-compose.yml` | Add `image:` with `IMAGE_TAG` env var alongside existing `build:` |
| Create | `.github/workflows/build.yml` | Build + push to GHCR + deploy to test |
| Create | `.github/workflows/deploy-prod.yml` | Re-tag image + deploy to prod on release |
| Delete | `.github/workflows/deploy.yml` | Replaced by build.yml + deploy-prod.yml |
| Modify | `docs/runner-setup.md` | Add GHCR login step for deployment VMs |

---

## docker-compose.yml

Add `image:` directives with `IMAGE_TAG` defaulting to `local`:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    image: ghcr.io/phildue/finance_tracker/backend:${IMAGE_TAG:-local}
    user: "1000:1000"
    environment:
      - DB_PATH=/data/expenses.db
    volumes:
      - ./data:/data
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    image: ghcr.io/phildue/finance_tracker/frontend:${IMAGE_TAG:-local}
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

`docker compose build` continues to work unchanged for local development (builds and tags images as `local`). `deploy.sh` remains functional for local builds.

---

## `.github/workflows/build.yml`

Triggers after CI succeeds on main. Two jobs:

**`build` job** (`ubuntu-latest`):
1. Checkout
2. Login to GHCR: `echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin`
3. Compute short SHA: `sha=$(git rev-parse --short HEAD)`
4. Build and push backend: tag as `sha-$sha` and `test`
5. Build and push frontend: tag as `sha-$sha` and `test`

**`deploy-test` job** (`self-hosted`, needs: build):
1. Checkout
2. SSH to `${{ secrets.DEPLOY_TEST_TARGET }}`:
   ```bash
   IMAGE_TAG=sha-$sha docker compose pull
   IMAGE_TAG=sha-$sha docker compose up -d
   ```

The SHA computed in `build` is passed to `deploy-test` via job outputs.

---

## `.github/workflows/deploy-prod.yml`

Triggers on `release: types: [published]`. Two jobs:

**`retag` job** (`ubuntu-latest`):
1. Checkout at the release tag
2. Compute SHA: `sha=$(git rev-parse --short ${{ github.event.release.tag_name }}^{})`
3. Login to GHCR with `GITHUB_TOKEN`
4. Re-tag backend image — copy manifest from `sha-$sha` to `${{ github.event.release.tag_name }}` and `prod`:
   ```bash
   docker buildx imagetools create \
     -t ghcr.io/phildue/finance_tracker/backend:${{ github.event.release.tag_name }} \
     -t ghcr.io/phildue/finance_tracker/backend:prod \
     ghcr.io/phildue/finance_tracker/backend:sha-$sha
   ```
5. Same for frontend
6. Output `sha` and `tag` as job outputs for the deploy job

**`deploy` job** (`self-hosted`, needs: retag):
1. SSH to `${{ secrets.DEPLOY_PROD_TARGET }}`:
   ```bash
   IMAGE_TAG=${{ github.event.release.tag_name }} docker compose pull
   IMAGE_TAG=${{ github.event.release.tag_name }} docker compose up -d
   ```

---

## GitHub Secrets Required

| Secret | Value | Used by |
|---|---|---|
| `DEPLOY_TEST_TARGET` | `user@<test-vm-ip>` | build.yml deploy-test job |
| `DEPLOY_PROD_TARGET` | `user@<prod-vm-ip>` | deploy-prod.yml |

`GITHUB_TOKEN` is built-in — no configuration needed for GHCR push.

The existing `DEPLOY_TARGET` secret (from current deploy.yml) can be removed.

---

## GHCR Authentication on Deployment VMs

Both test and prod VMs need to authenticate with GHCR once to pull private images. On each VM:

1. Create a GitHub PAT with `read:packages` scope (GitHub → Settings → Developer settings → Personal access tokens)
2. `echo <PAT> | docker login ghcr.io -u phildue --password-stdin`
3. Credentials are stored in `~/.docker/config.json` and persist

This is a one-time manual step. `docs/runner-setup.md` will be updated to document it.

---

## What Gets Retired

- `.github/workflows/deploy.yml` — deleted
- `DEPLOY_TARGET` GitHub secret — no longer needed (replaced by `DEPLOY_TEST_TARGET` and `DEPLOY_PROD_TARGET`)

---

## Out of Scope for This Slice

- Rollback mechanism (re-deploy previous tag manually for now)
- Approval gate for prod (GitHub Environments with required reviewers — future slice)
- Smoke test after prod deploy
- Notification on deploy success/failure
