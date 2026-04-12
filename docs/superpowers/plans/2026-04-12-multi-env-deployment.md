# Multi-Environment Deployment via GHCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace rsync+build deployment with a registry-based pipeline that builds images once on GitHub-hosted runners, pushes to GHCR, and deploys to separate test (auto on merge) and prod (on GitHub Release) VMs.

**Architecture:** A `build.yml` workflow builds Docker images on `ubuntu-latest` and pushes to GHCR tagged by git SHA, then a `self-hosted` deploy job SSHes to the test VM to pull+run. A separate `deploy-prod.yml` workflow fires on GitHub Release, re-tags the existing SHA image as the release version (no rebuild), then deploys to prod. The self-hosted runner never needs Docker — only SSH.

**Tech Stack:** GitHub Actions, GitHub Container Registry (GHCR), Docker Compose, bash, SSH

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `docker-compose.yml` | Add `image:` with `IMAGE_TAG` var alongside existing `build:` |
| Create | `.github/workflows/build.yml` | Build images → push GHCR → deploy test |
| Create | `.github/workflows/deploy-prod.yml` | Retag image → deploy prod on release |
| Delete | `.github/workflows/deploy.yml` | Retired — replaced by above two |
| Modify | `docs/runner-setup.md` | Add GHCR login step + update secret names |

---

### Task 1: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add `image:` directives**

Replace the content of `docker-compose.yml` with:

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

- [ ] **Step 2: Verify config parses correctly without IMAGE_TAG**

```bash
cd /home/phil/code/finance_tracker
docker compose config --quiet
```

Expected: no errors. The `image:` fields should resolve to `ghcr.io/phildue/finance_tracker/backend:local` and `ghcr.io/phildue/finance_tracker/frontend:local`.

- [ ] **Step 3: Verify config parses correctly with IMAGE_TAG set**

```bash
IMAGE_TAG=sha-abc1234 docker compose config --quiet
```

Expected: no errors. Images should resolve to `ghcr.io/phildue/finance_tracker/backend:sha-abc1234` and `ghcr.io/phildue/finance_tracker/frontend:sha-abc1234`.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add IMAGE_TAG support to docker-compose for registry-based deployment"
```

---

### Task 2: Create build.yml

**Files:**
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: Create `.github/workflows/build.yml`**

```yaml
name: Build and Deploy Test

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    outputs:
      sha: ${{ steps.sha.outputs.sha }}
    steps:
      - uses: actions/checkout@v4

      - name: Compute short SHA
        id: sha
        run: echo "sha=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Login to GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Build and push backend
        run: |
          docker build \
            -t ghcr.io/phildue/finance_tracker/backend:sha-${{ steps.sha.outputs.sha }} \
            -t ghcr.io/phildue/finance_tracker/backend:test \
            -f backend/Dockerfile .
          docker push ghcr.io/phildue/finance_tracker/backend:sha-${{ steps.sha.outputs.sha }}
          docker push ghcr.io/phildue/finance_tracker/backend:test

      - name: Build and push frontend
        run: |
          docker build \
            -t ghcr.io/phildue/finance_tracker/frontend:sha-${{ steps.sha.outputs.sha }} \
            -t ghcr.io/phildue/finance_tracker/frontend:test \
            -f frontend/Dockerfile .
          docker push ghcr.io/phildue/finance_tracker/frontend:sha-${{ steps.sha.outputs.sha }}
          docker push ghcr.io/phildue/finance_tracker/frontend:test

  deploy-test:
    runs-on: self-hosted
    needs: build
    steps:
      - name: Deploy to test
        run: |
          ssh -i ~/.ssh/deploy_key \
              -o StrictHostKeyChecking=accept-new \
              "${{ secrets.DEPLOY_TEST_TARGET }}" \
              "cd /opt/finance_tracker && export IMAGE_TAG=sha-${{ needs.build.outputs.sha }} && docker compose pull && docker compose up -d"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "feat: add build workflow — build images, push to GHCR, deploy to test"
```

---

### Task 3: Create deploy-prod.yml

**Files:**
- Create: `.github/workflows/deploy-prod.yml`

- [ ] **Step 1: Create `.github/workflows/deploy-prod.yml`**

```yaml
name: Deploy to Production

on:
  release:
    types: [published]

jobs:
  retag:
    runs-on: ubuntu-latest
    outputs:
      sha: ${{ steps.sha.outputs.sha }}
      tag: ${{ github.event.release.tag_name }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Resolve release commit SHA
        id: sha
        run: echo "sha=$(git rev-parse --short ${{ github.event.release.tag_name }}^{})" >> $GITHUB_OUTPUT

      - name: Login to GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Retag backend
        run: |
          docker buildx imagetools create \
            -t ghcr.io/phildue/finance_tracker/backend:${{ github.event.release.tag_name }} \
            -t ghcr.io/phildue/finance_tracker/backend:prod \
            ghcr.io/phildue/finance_tracker/backend:sha-${{ steps.sha.outputs.sha }}

      - name: Retag frontend
        run: |
          docker buildx imagetools create \
            -t ghcr.io/phildue/finance_tracker/frontend:${{ github.event.release.tag_name }} \
            -t ghcr.io/phildue/finance_tracker/frontend:prod \
            ghcr.io/phildue/finance_tracker/frontend:sha-${{ steps.sha.outputs.sha }}

  deploy:
    runs-on: self-hosted
    needs: retag
    steps:
      - name: Deploy to prod
        run: |
          ssh -i ~/.ssh/deploy_key \
              -o StrictHostKeyChecking=accept-new \
              "${{ secrets.DEPLOY_PROD_TARGET }}" \
              "cd /opt/finance_tracker && export IMAGE_TAG=${{ needs.retag.outputs.tag }} && docker compose pull && docker compose up -d"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy-prod.yml
git commit -m "feat: add prod deploy workflow — retag GHCR image on release, deploy to prod"
```

---

### Task 4: Retire deploy.yml and update runner-setup.md

**Files:**
- Delete: `.github/workflows/deploy.yml`
- Modify: `docs/runner-setup.md`

- [ ] **Step 1: Delete deploy.yml**

```bash
git rm .github/workflows/deploy.yml
```

- [ ] **Step 2: Update docs/runner-setup.md**

Replace the entire **Section 4 (SSH key for deployment)** and add a new **Section 5 (GHCR authentication)** before the existing **Section 5 (Deployment target prerequisites)**. The updated sections:

Replace the existing `## 4. SSH key for deployment` section with:

```markdown
## 4. SSH key for deployment

The private key lives on the runner machine — it never needs to leave the local network.

Generate a key pair on the runner machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
```

Copy the public key to **both** deployment VMs (test and prod):

```bash
ssh-copy-id -i ~/.ssh/deploy_key.pub user@<test-vm-ip>
ssh-copy-id -i ~/.ssh/deploy_key.pub user@<prod-vm-ip>
```

The deploy workflows reference `~/.ssh/deploy_key` directly. No GitHub secret needed for the key.

Add two GitHub Actions secrets:

1. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `DEPLOY_TEST_TARGET`, value: `user@<test-vm-ip>` (e.g. `ubuntu@192.168.1.50`)
3. Name: `DEPLOY_PROD_TARGET`, value: `user@<prod-vm-ip>` (e.g. `ubuntu@192.168.1.51`)

The old `DEPLOY_TARGET` secret can be deleted.

## 5. GHCR authentication on deployment VMs

Both test and prod VMs must authenticate with GHCR once to pull images.

On each VM:

1. Create a GitHub Personal Access Token (classic) with `read:packages` scope:
   GitHub → Settings → Developer settings → Personal access tokens (classic) → Generate new token

2. Log in to GHCR:
   ```bash
   echo <PAT> | docker login ghcr.io -u phildue --password-stdin
   ```

3. Verify:
   ```bash
   cat ~/.docker/config.json | grep ghcr
   ```
   Expected: entry for `ghcr.io` present.

Credentials are stored in `~/.docker/config.json` and persist across reboots.
```

- [ ] **Step 3: Commit**

`git rm` in Step 1 already staged the deletion. Just stage the docs change and commit:

```bash
git add docs/runner-setup.md
git commit -m "chore: retire deploy.yml, update runner-setup with GHCR auth and new secret names"
```

Verify with `git status` before committing — `deploy.yml` should show as `deleted`, `runner-setup.md` as `modified`.

- [ ] **Step 4: Push all commits**

```bash
git push
```

- [ ] **Step 5: Add GitHub secrets**

In the GitHub repo → **Settings → Secrets and variables → Actions**:

- Add `DEPLOY_TEST_TARGET`: `user@<test-vm-ip>`
- Add `DEPLOY_PROD_TARGET`: `user@<prod-vm-ip>`
- Delete the old `DEPLOY_TARGET` secret (three-dot menu → Delete)

- [ ] **Step 6: Authenticate GHCR on both deployment VMs**

On each VM, follow Section 5 of `docs/runner-setup.md` — create a PAT with `read:packages` scope and run `docker login ghcr.io`.

**Pause here and confirm with the user before continuing** — this requires manual action on the deployment VMs.

- [ ] **Step 7: Verify first build run**

After pushing, a merge to main will trigger `ci.yml`. Once CI passes, `build.yml` will trigger automatically. Watch it at **GitHub → Actions → Build and Deploy Test**.

The `build` job (ubuntu-latest) should:
- Build both images
- Push tags `sha-<hash>` and `test` to GHCR
- The packages will appear at `https://github.com/phildue?tab=packages`

The `deploy-test` job (self-hosted) will then SSH to the test VM and run `docker compose pull && up`.
