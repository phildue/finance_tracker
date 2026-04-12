# System Tests Design

**Date:** 2026-04-12  
**Status:** Approved

## Overview

Add system tests as a quality gate in the CI/CD pipeline. Tests run against the full Docker stack (nginx + backend + SQLite) spun up on the CI runner, covering typical user workflows at both the API and browser levels. A failing system test blocks deployment to the test environment.

## Pipeline Position

```
CI (lint + unit tests) → build (Docker images) → system-test → deploy-test
```

The `deploy-prod` workflow (triggered on release) is unaffected — it promotes the already-tested image.

## Directory Structure

```
system-tests/
  conftest.py          # docker compose lifecycle + base URL fixtures
  requirements.txt     # pytest, httpx, playwright
  test_api.py          # API-level workflow tests
  test_ui.py           # Playwright browser tests
```

Lives at the repo root, separate from `backend/tests/`. Has its own `requirements.txt` so CI installs only what system tests need.

## Test Infrastructure (`conftest.py`)

1. Read `IMAGE_TAG` from the environment (set by CI to `sha-<short-sha>`)
2. Run `docker compose up -d` with that image tag
3. Poll `GET /health` until the stack is ready (timeout: 60 s)
4. Yield base URLs (`http://localhost:8000` for API, `http://localhost:80` for UI) as pytest fixtures
5. Run `docker compose down` on teardown

## Test Scenarios

### API tests (`test_api.py`) — httpx against `http://localhost:8000`

| Scenario | Steps | Expected |
|---|---|---|
| Add an expense | POST `/expenses` with valid payload | 201, response fields match input |
| List expenses | POST two expenses with different dates, GET `/expenses` | Both present, sorted by date descending |
| Validation rejects zero amount | POST with `amount: "0"` | 422 |
| Health check | GET `/health` | 200, `{"status": "ok"}` |

### UI tests (`test_ui.py`) — Playwright headless Chromium against `http://localhost:80`

| Scenario | Steps | Expected |
|---|---|---|
| Add an expense via form | Fill form (amount, currency, category, date), submit | Expense appears in the list |
| Form rejects empty submission | Click submit with empty form | No new entry in list; browser validation prevents submission |

UI tests cover only the form→API→list round-trip. Validation edge cases are covered at the API layer.

## CI Job (`build.yml`)

New `system-test` job added after `build`:

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
      run: pip install -r system-tests/requirements.txt && playwright install chromium
    - name: Login to GHCR
      run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
    - name: Run system tests
      env:
        IMAGE_TAG: sha-${{ needs.build.outputs.sha }}
      run: cd system-tests && pytest -v
```

`deploy-test` changes from `needs: build` to `needs: [build, system-test]`.

## Out of Scope

- Tests against the live test or production environment
- Frontend component tests (covered by TypeScript type checking and the existing build check)
- Performance or load testing
