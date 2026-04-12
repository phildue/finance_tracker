# CI/CD via GitHub Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push the finance tracker to GitHub, establish CI quality gates (pytest, ruff, tsc, build, smoke test), and automate deployment to a local VM on every merge to main via a self-hosted GitHub Actions runner.

**Architecture:** Two workflow files — `ci.yml` runs tests + linting + a Docker smoke test on every push/PR; `deploy.yml` triggers after `ci.yml` succeeds on `main` and deploys via SSH using the existing `deploy.sh` approach (rsync + `docker compose up`). Both run on a self-hosted runner on PVE.

**Tech Stack:** GitHub Actions, Python 3.11, ruff, pytest, Node 20, TypeScript compiler, Docker Compose, bash, SSH/rsync

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `.gitignore` | Add `node_modules/` and `frontend/dist/` |
| Modify | `backend/requirements-dev.txt` | Add `ruff>=0.4.0` |
| Modify | `backend/adapters/api/routes.py` | Add `GET /health` endpoint |
| Modify | `backend/tests/test_api.py` | Add health endpoint test |
| Modify | `frontend/nginx.conf` | Proxy `/health` to backend |
| Create | `.github/workflows/ci.yml` | CI: lint + test + smoke test |
| Create | `.github/workflows/deploy.yml` | Deploy on merge to main |
| Create | `docs/runner-setup.md` | Self-hosted runner provisioning guide |

---

### Task 1: Fix .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add missing entries**

Open `.gitignore` and add these two lines after the existing entries:

```
node_modules/
frontend/dist/
```

The file should then read:
```
*.pyc
data/expenses.db
node_modules/
frontend/dist/
```

- [ ] **Step 2: Verify node_modules is now ignored**

```bash
git check-ignore -v frontend/node_modules
```

Expected output: `.gitignore:3:node_modules/  frontend/node_modules`

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore node_modules and frontend/dist"
```

---

### Task 2: Add ruff and verify backend linting

**Files:**
- Modify: `backend/requirements-dev.txt`

- [ ] **Step 1: Add ruff to dev dependencies**

Open `backend/requirements-dev.txt` and add `ruff>=0.4.0`:

```
-r requirements.txt
pytest>=8.0.0
httpx>=0.27.0
ruff>=0.4.0
```

- [ ] **Step 2: Install and verify ruff runs cleanly**

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .
```

Expected: no output (zero violations). If violations are reported, fix them before continuing — most will be auto-fixable with `ruff check --fix .`.

- [ ] **Step 3: Commit**

```bash
git add backend/requirements-dev.txt
git commit -m "chore: add ruff linter to dev dependencies"
```

---

### Task 3: Add GET /health endpoint (TDD)

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/adapters/api/routes.py`
- Modify: `frontend/nginx.conf`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_api.py`:

```python
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_api.py::test_health_returns_ok -v
```

Expected: `FAILED` — `assert 404 == 200`

- [ ] **Step 3: Implement the health endpoint**

In `backend/adapters/api/routes.py`, add the route inside `build_router` before the `return router` line:

```python
    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}
```

The end of `build_router` should now look like:

```python
    @router.get("/expenses", response_model=list[ExpenseResponse])
    def get_expenses() -> list[ExpenseResponse]:
        return [_to_response(e) for e in list_expenses.execute()]

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return router
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend
pytest tests/test_api.py::test_health_returns_ok -v
```

Expected: `PASSED`

- [ ] **Step 5: Run full backend test suite to check for regressions**

```bash
cd backend
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Proxy /health through nginx**

In `frontend/nginx.conf`, add a `/health` location block after the `/expenses` block:

```nginx
    location /health {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
```

Full file after edit:

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

    location /health {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_api.py backend/adapters/api/routes.py frontend/nginx.conf
git commit -m "feat: add GET /health endpoint and nginx proxy"
```

---

### Task 4: Create CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write ci.yml**

Create `.github/workflows/ci.yml` with this content:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements-dev.txt

      - name: Lint
        working-directory: backend
        run: ruff check .

      - name: Test
        working-directory: backend
        run: pytest -v

  frontend:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Type check
        working-directory: frontend
        run: npx tsc --noEmit

      - name: Build
        working-directory: frontend
        run: npm run build

  system:
    runs-on: self-hosted
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4

      - name: Build stack
        run: docker compose build

      - name: Start stack
        run: docker compose up -d

      - name: Wait for health
        run: |
          for i in $(seq 1 30); do
            if curl -sf http://localhost/health > /dev/null; then
              echo "Stack is healthy"
              exit 0
            fi
            echo "Attempt $i/30 — waiting 2s..."
            sleep 2
          done
          echo "Timed out after 60s waiting for /health"
          docker compose logs
          exit 1

      - name: Tear down
        if: always()
        run: docker compose down
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat: add CI workflow (backend, frontend, system jobs)"
```

---

### Task 5: Create deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Write deploy.yml**

Create `.github/workflows/deploy.yml` with this content:

```yaml
name: Deploy

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    runs-on: self-hosted
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key

      - name: Sync source to target
        run: |
          rsync -az \
            -e "ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=accept-new" \
            --exclude='.git/' \
            --exclude='data/' \
            --exclude='node_modules/' \
            --exclude='__pycache__/' \
            --exclude='frontend/dist/' \
            . "${{ secrets.DEPLOY_TARGET }}:/opt/finance_tracker"

      - name: Deploy on target
        run: |
          ssh -i ~/.ssh/deploy_key \
              -o StrictHostKeyChecking=accept-new \
              "${{ secrets.DEPLOY_TARGET }}" \
              "cd /opt/finance_tracker && docker compose build && docker compose up -d"

      - name: Clean up SSH key
        if: always()
        run: rm -f ~/.ssh/deploy_key
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: add deploy workflow (triggers after CI on main)"
```

---

### Task 6: Write runner setup documentation

**Files:**
- Create: `docs/runner-setup.md`

- [ ] **Step 1: Write docs/runner-setup.md**

Create `docs/runner-setup.md` with this content:

```markdown
# Self-Hosted GitHub Actions Runner Setup

This documents how to provision the self-hosted runner on Proxmox VE.
The runner is distinct from the deployment target VM.

## Prerequisites

A PVE VM or LXC with:
- Ubuntu 22.04 or Debian 12
- Internet access (to reach GitHub and download runner binary)
- Network access to the deployment target VM

## 1. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in for the group change to take effect.

## 2. Register the GitHub Actions runner

In the GitHub repository: **Settings → Actions → Runners → New self-hosted runner**. Select Linux and follow the on-screen instructions. They look like:

```bash
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-<version>.tar.gz -L https://github.com/actions/runner/releases/download/...
tar xzf ./actions-runner-linux-x64-<version>.tar.gz
./config.sh --url https://github.com/<owner>/finance_tracker --token <TOKEN>
```

Use the exact commands shown on the GitHub page (version and token are generated per registration).

## 3. Run as a systemd service

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

The runner now starts automatically on boot and appears as online in GitHub.

## 4. SSH key for deployment

Generate a key pair on the runner machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
```

Copy the public key to the deployment target VM:

```bash
ssh-copy-id -i ~/.ssh/deploy_key.pub user@<deployment-vm-ip>
```

Add the private key as a GitHub Actions secret:

1. Copy the private key contents: `cat ~/.ssh/deploy_key`
2. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `DEPLOY_SSH_KEY`, value: paste the private key

Add the deployment target as a secret:

- Name: `DEPLOY_TARGET`, value: `user@<deployment-vm-ip>` (e.g. `ubuntu@192.168.1.50`)

## 5. Deployment target prerequisites

On the deployment VM (`DEPLOY_TARGET`):

```bash
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
sudo mkdir -p /opt/finance_tracker/data
```

The `data/` directory holds `expenses.db` and persists between deploys (rsync excludes it).
```

- [ ] **Step 2: Commit**

```bash
git add docs/runner-setup.md
git commit -m "docs: add self-hosted runner setup guide"
```

---

### Task 7: Push to GitHub

**Files:** none (git remote operations only)

- [ ] **Step 1: Create the GitHub repository**

Using the `gh` CLI (install from https://cli.github.com if needed):

```bash
gh repo create finance_tracker --private --source=. --remote=origin
```

This creates a private repo named `finance_tracker` under your GitHub account, sets it as `origin`, and links the local repo.

If you prefer the GitHub web UI: create the repo there, then run:

```bash
git remote add origin https://github.com/<your-username>/finance_tracker.git
```

- [ ] **Step 2: Push**

```bash
git push -u origin main
```

Expected: all commits pushed, branch `main` set to track `origin/main`.

- [ ] **Step 3: Verify CI workflow appears in GitHub**

Open the repo on GitHub → **Actions** tab. You should see the "CI" workflow listed. It will only run when triggered by a push or PR — no run yet since we just pushed without a workflow file change triggering it. To trigger it manually, make a trivial commit:

```bash
git commit --allow-empty -m "ci: trigger first CI run"
git push
```

Then check **Actions** — CI should start within seconds and all three jobs (backend, frontend, system) should go green.

- [ ] **Step 4: Verify runner is connected**

GitHub repo → **Settings → Actions → Runners**. The self-hosted runner should show as **Idle** (online and waiting). If it shows as **Offline**, check the systemd service on the PVE runner VM:

```bash
sudo systemctl status actions.runner.<repo-name>.service
```
