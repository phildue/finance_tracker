# System Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pytest + Playwright system tests that spin up the full Docker stack on the CI runner and block deployment on failure.

**Architecture:** A top-level `system-tests/` directory holds infrastructure (`conftest.py`) and two test modules. A session-scoped autouse fixture in `conftest.py` starts/stops docker compose around the full test run. API tests use `httpx`; browser tests use `pytest-playwright`. A new `system-test` CI job runs between `build` and `deploy-test`, blocking deployment on failure.

**Tech Stack:** Python 3.11, pytest, httpx, pytest-playwright, Playwright Chromium, Docker Compose

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `system-tests/requirements.txt` | Create | Test dependencies |
| `system-tests/conftest.py` | Create | Docker compose lifecycle + `api_url`/`ui_url` fixtures |
| `system-tests/test_api.py` | Create | API-level workflow tests (httpx) |
| `system-tests/test_ui.py` | Create | Browser workflow tests (Playwright) |
| `.github/workflows/build.yml` | Modify | Add `system-test` job; block `deploy-test` on it |

---

### Task 1: Create system-tests/requirements.txt

**Files:**
- Create: `system-tests/requirements.txt`

- [ ] **Step 1: Create the requirements file**

```
pytest
httpx
pytest-playwright
```

Save as `system-tests/requirements.txt`.

- [ ] **Step 2: Commit**

```bash
git add system-tests/requirements.txt
git commit -m "chore: scaffold system-tests directory"
```

---

### Task 2: Implement conftest.py

**Files:**
- Create: `system-tests/conftest.py`

The `docker_stack` fixture is `scope="session"` and `autouse=True` — it runs once before any test in the session, including Playwright tests. `REPO_ROOT` is computed from the file's own location so the fixture finds `docker-compose.yml` regardless of which directory pytest is invoked from.

- [ ] **Step 1: Create conftest.py**

```python
import os
import subprocess
import time

import httpx
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "http://localhost:8000"
UI_URL = "http://localhost:80"


@pytest.fixture(scope="session", autouse=True)
def docker_stack():
    image_tag = os.environ.get("IMAGE_TAG", "local")
    env = {**os.environ, "IMAGE_TAG": image_tag}
    subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = httpx.get(f"{API_URL}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        subprocess.run(["docker", "compose", "down"], cwd=REPO_ROOT)
        raise RuntimeError("Stack did not become healthy within 60s")
    yield
    subprocess.run(["docker", "compose", "down"], cwd=REPO_ROOT, check=True)


@pytest.fixture(scope="session")
def api_url():
    return API_URL


@pytest.fixture(scope="session")
def ui_url():
    return UI_URL
```

- [ ] **Step 2: Verify the conftest starts and stops the stack locally**

First build the local images (one-time):

```bash
docker compose build
```

Then verify conftest runs without errors (no tests yet, just collection):

```bash
cd system-tests && IMAGE_TAG=local pytest --collect-only
```

Expected: `no tests ran` with no errors. Verify with `docker ps` immediately after — no containers should be running (stack was torn down).

- [ ] **Step 3: Commit**

```bash
git add system-tests/conftest.py
git commit -m "feat: add system-tests conftest with docker compose lifecycle"
```

---

### Task 3: Write and verify API system tests

**Files:**
- Create: `system-tests/test_api.py`

Each test uses a fresh `httpx` call — no shared client state. The `test_list_expenses_sorted_by_date_desc` test uses unique category names (`sys-test-alpha`, `sys-test-beta`) to find its own rows in the list without assuming an empty database.

- [ ] **Step 1: Write test_api.py**

```python
import httpx


def test_health(api_url):
    r = httpx.get(f"{api_url}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_add_expense(api_url):
    r = httpx.post(
        f"{api_url}/expenses",
        json={"amount": "42.50", "currency": "EUR", "category": "groceries", "date": "2026-04-12"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == "42.50"
    assert data["currency"] == "EUR"
    assert data["category"] == "groceries"
    assert data["date"] == "2026-04-12"
    assert "id" in data


def test_list_expenses_sorted_by_date_desc(api_url):
    httpx.post(
        f"{api_url}/expenses",
        json={"amount": "10.00", "currency": "EUR", "category": "sys-test-alpha", "date": "2026-01-01"},
    )
    httpx.post(
        f"{api_url}/expenses",
        json={"amount": "20.00", "currency": "EUR", "category": "sys-test-beta", "date": "2026-03-01"},
    )

    r = httpx.get(f"{api_url}/expenses")
    assert r.status_code == 200
    items = r.json()

    alpha = next(e for e in items if e["category"] == "sys-test-alpha")
    beta = next(e for e in items if e["category"] == "sys-test-beta")
    # beta (2026-03-01) must appear before alpha (2026-01-01) — newest first
    assert items.index(beta) < items.index(alpha)


def test_validation_rejects_zero_amount(api_url):
    r = httpx.post(
        f"{api_url}/expenses",
        json={"amount": "0", "currency": "EUR", "category": "food", "date": "2026-04-12"},
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests against the local stack**

```bash
cd system-tests && IMAGE_TAG=local pytest test_api.py -v
```

Expected:
```
test_api.py::test_health PASSED
test_api.py::test_add_expense PASSED
test_api.py::test_list_expenses_sorted_by_date_desc PASSED
test_api.py::test_validation_rejects_zero_amount PASSED
4 passed
```

- [ ] **Step 3: Commit**

```bash
git add system-tests/test_api.py
git commit -m "feat: add API system tests"
```

---

### Task 4: Write and verify UI system tests

**Files:**
- Create: `system-tests/test_ui.py`

The `page` fixture is provided automatically by `pytest-playwright` (installed via `requirements.txt`). It gives a headless Chromium page per test. You must install the browser binary once before running:

```bash
playwright install chromium
```

The `test_form_rejects_empty_submission` test counts `tbody tr` before and after clicking submit with empty required fields. Native browser validation (`required` attributes on the form inputs) blocks the submission, so the count is unchanged. The count works correctly whether the table is empty (0 rows, no `<tbody>`) or has rows from previous tests — `locator().count()` returns 0 when no elements match.

- [ ] **Step 1: Write test_ui.py**

```python
def test_add_expense_via_form(page, ui_url):
    page.goto(ui_url)
    page.wait_for_load_state("networkidle")
    page.fill("#amount", "55.00")
    page.fill("#currency", "EUR")
    page.fill("#category", "sys-test-ui-add")
    page.fill("#date", "2026-04-12")
    page.click('button[type="submit"]')
    page.wait_for_selector('td:has-text("sys-test-ui-add")')
    assert page.locator('td:has-text("sys-test-ui-add")').count() >= 1


def test_form_rejects_empty_submission(page, ui_url):
    page.goto(ui_url)
    page.wait_for_load_state("networkidle")
    initial_row_count = page.locator("tbody tr").count()
    page.fill("#amount", "")
    page.fill("#category", "")
    page.fill("#date", "")
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)
    assert page.locator("tbody tr").count() == initial_row_count
```

- [ ] **Step 2: Install Playwright Chromium (one-time)**

```bash
playwright install chromium
```

- [ ] **Step 3: Run UI tests against the local stack**

```bash
cd system-tests && IMAGE_TAG=local pytest test_ui.py -v
```

Expected:
```
test_ui.py::test_add_expense_via_form PASSED
test_ui.py::test_form_rejects_empty_submission PASSED
2 passed
```

- [ ] **Step 4: Run the full suite**

```bash
cd system-tests && IMAGE_TAG=local pytest -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add system-tests/test_ui.py
git commit -m "feat: add UI system tests with Playwright"
```

---

### Task 5: Update build.yml — add system-test job

**Files:**
- Modify: `.github/workflows/build.yml:47-57`

- [ ] **Step 1: Add the system-test job after the build job**

In `.github/workflows/build.yml`, add this job block after the closing of the `build` job and before `deploy-test`:

```yaml
  system-test:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r system-tests/requirements.txt && playwright install --with-deps chromium

      - name: Login to GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Run system tests
        env:
          IMAGE_TAG: sha-${{ needs.build.outputs.sha }}
        run: cd system-tests && pytest -v
```

- [ ] **Step 2: Block deploy-test on system-test**

Change the `deploy-test` job's `needs` line from:

```yaml
    needs: build
```

to:

```yaml
    needs: [build, system-test]
```

- [ ] **Step 3: Verify the full build.yml is valid YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml'))" && echo "valid"
```

Expected: `valid`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: add system-test job as gate before deploy-test"
```
