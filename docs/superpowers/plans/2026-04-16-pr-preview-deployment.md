# PR Preview Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically deploy an ephemeral app instance for each PR on the test server at port `8000 + PR_NUMBER`, and tear it down when the PR is closed.

**Architecture:** A new GitHub Actions workflow triggers on `pull_request` events. On open/update it rsyncs the PR branch source to the test server and starts a Docker Compose stack under project name `pr-<N>` on port `8000+N`. On close it shuts the stack down and removes the directory. A PR comment is posted with the URL.

**Tech Stack:** GitHub Actions, Docker Compose, bash, `gh` CLI, rsync/SSH

---

## File Map

| File | Action |
|------|--------|
| `docker-compose.yml` | Modify — make frontend host port configurable |
| `.github/workflows/deploy-preview.yml` | Create — PR preview deploy/teardown workflow |

---

### Task 1: Make frontend port configurable in docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Edit docker-compose.yml to use FRONTEND_PORT env var**

In `docker-compose.yml`, change the `frontend` service `ports` entry from:

```yaml
    ports:
      - "80:80"
```

to:

```yaml
    ports:
      - "${FRONTEND_PORT:-80}:80"
```

The default `80` keeps the existing test deployment unchanged.

- [ ] **Step 2: Verify the compose file is valid**

```bash
docker compose config --quiet
```

Expected: no output, exit code 0. If Docker is not available locally, validate the YAML syntax:

```bash
python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: make frontend host port configurable via FRONTEND_PORT"
```

---

### Task 2: Create the deploy-preview workflow

**Files:**
- Create: `.github/workflows/deploy-preview.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/deploy-preview.yml` with this content:

```yaml
name: PR Preview

on:
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened, closed]

jobs:
  deploy-preview:
    if: github.event.action != 'closed'
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4

      - name: Compute preview port
        run: echo "PREVIEW_PORT=$((8000 + ${{ github.event.pull_request.number }}))" >> $GITHUB_ENV

      - name: Sync source to server
        run: |
          rsync -az \
            -e "ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/deploy_key" \
            --exclude='.git/' \
            --exclude='data/' \
            --exclude='node_modules/' \
            --exclude='__pycache__/' \
            --exclude='frontend/dist/' \
            . "${{ secrets.DEPLOY_TEST_TARGET }}:/opt/finance_tracker_pr_${{ github.event.pull_request.number }}/"

      - name: Prepare data directory
        run: |
          ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/deploy_key \
            "${{ secrets.DEPLOY_TEST_TARGET }}" \
            "mkdir -p /opt/finance_tracker_pr_${{ github.event.pull_request.number }}/data && chown 1000:1000 /opt/finance_tracker_pr_${{ github.event.pull_request.number }}/data"

      - name: Deploy preview stack
        run: |
          ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/deploy_key \
            "${{ secrets.DEPLOY_TEST_TARGET }}" \
            "cd /opt/finance_tracker_pr_${{ github.event.pull_request.number }} && FRONTEND_PORT=${{ env.PREVIEW_PORT }} IMAGE_TAG=local docker compose -p pr-${{ github.event.pull_request.number }} up -d --build"

      - name: Post preview URL comment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }} \
            --body "Preview deployed: http://${{ secrets.DEPLOY_TEST_HOST }}:${{ env.PREVIEW_PORT }}" \
            --edit-last --create-if-none

  teardown-preview:
    if: github.event.action == 'closed'
    runs-on: self-hosted
    steps:
      - name: Tear down preview stack
        run: |
          ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/deploy_key \
            "${{ secrets.DEPLOY_TEST_TARGET }}" \
            "docker compose -p pr-${{ github.event.pull_request.number }} down --volumes || true; rm -rf /opt/finance_tracker_pr_${{ github.event.pull_request.number }}"

      - name: Post teardown comment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }} \
            --body "Preview instance torn down." \
            --edit-last --create-if-none
```

- [ ] **Step 2: Validate the workflow YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-preview.yml')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy-preview.yml
git commit -m "feat: add PR preview deploy/teardown workflow"
```

---

### Task 3: Add the DEPLOY_TEST_HOST secret

**Files:** none (GitHub repo secret — set via `gh` CLI)

- [ ] **Step 1: Set the secret**

Replace `<hostname-or-ip>` with the bare hostname or IP of the test server (no `user@`, no port):

```bash
gh secret set DEPLOY_TEST_HOST --repo phildue/finance_tracker --body "<hostname-or-ip>"
```

Expected: no output, exit code 0.

- [ ] **Step 2: Verify the secret exists**

```bash
gh secret list --repo phildue/finance_tracker
```

Expected: `DEPLOY_TEST_HOST` appears in the list alongside `DEPLOY_TEST_TARGET`.

---

### Task 4: Open firewall ports on the test server (ops step)

**Files:** none — manual SSH step on the test server.

The test server must accept inbound TCP on the port range you'll use for PRs. With `ufw`:

- [ ] **Step 1: Open the port range**

SSH into the test server and run:

```bash
sudo ufw allow 8001:8999/tcp
sudo ufw reload
sudo ufw status | grep 80
```

Expected: rules for `8001:8999/tcp` appear in the output.

> If the server uses a different firewall (`iptables`, cloud security group, etc.), apply the equivalent rule there instead.

---

### Task 5: End-to-end smoke test

- [ ] **Step 1: Create a test branch and open a PR**

```bash
git checkout -b test/pr-preview-smoke
git commit --allow-empty -m "test: trigger PR preview smoke test"
git push origin test/pr-preview-smoke
gh pr create --repo phildue/finance_tracker \
  --title "test: PR preview smoke test" \
  --body "Testing preview deployment. Delete after." \
  --base main
```

Note the PR number from the output (e.g., `#11`).

- [ ] **Step 2: Watch the workflow run**

```bash
gh run list --repo phildue/finance_tracker --workflow=deploy-preview.yml --limit 5
```

Wait for the `deploy-preview` job to complete (status: `completed`, conclusion: `success`).

- [ ] **Step 3: Verify the PR comment**

```bash
gh pr view <PR_NUMBER> --repo phildue/finance_tracker --comments
```

Expected: a comment from `github-actions[bot]` containing `Preview deployed: http://<host>:8<N>`.

- [ ] **Step 4: Verify the running instance**

Open `http://<host>:8<N>` in a browser (or curl it):

```bash
curl -sf http://<host>:$((8000 + PR_NUMBER))/expenses | python3 -m json.tool
```

Expected: JSON array response (may be empty `[]`).

- [ ] **Step 5: Close the PR and verify teardown**

```bash
gh pr close <PR_NUMBER> --repo phildue/finance_tracker
```

Wait for the `teardown-preview` job to complete:

```bash
gh run list --repo phildue/finance_tracker --workflow=deploy-preview.yml --limit 5
```

- [ ] **Step 6: Verify the instance is gone**

```bash
curl -sf http://<host>:$((8000 + PR_NUMBER))/expenses
```

Expected: connection refused (exit code non-zero).

- [ ] **Step 7: Delete the test branch**

```bash
git push origin --delete test/pr-preview-smoke
git checkout main
git branch -d test/pr-preview-smoke
```
