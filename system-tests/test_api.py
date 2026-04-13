import subprocess
import time

import httpx
import pytest


def test_health(base_url):
    r = httpx.get(f"{base_url}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_add_expense(base_url):
    r = httpx.post(
        f"{base_url}/expenses",
        json={"amount": "42.50", "currency": "EUR", "category": "groceries", "date": "2026-04-12"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == "42.50"
    assert data["currency"] == "EUR"
    assert data["category"] == "groceries"
    assert data["date"] == "2026-04-12"
    assert "id" in data


def test_list_expenses_sorted_by_date_desc(base_url):
    r1 = httpx.post(
        f"{base_url}/expenses",
        json={"amount": "10.00", "currency": "EUR", "category": "sys-test-alpha", "date": "2026-01-01"},
    )
    assert r1.status_code == 201
    r2 = httpx.post(
        f"{base_url}/expenses",
        json={"amount": "20.00", "currency": "EUR", "category": "sys-test-beta", "date": "2026-03-01"},
    )
    assert r2.status_code == 201

    r = httpx.get(f"{base_url}/expenses")
    assert r.status_code == 200
    items = r.json()

    alpha = next((e for e in items if e["category"] == "sys-test-alpha"), None)
    assert alpha is not None, "sys-test-alpha not found in expense list"
    beta = next((e for e in items if e["category"] == "sys-test-beta"), None)
    assert beta is not None, "sys-test-beta not found in expense list"
    # beta (2026-03-01) must appear before alpha (2026-01-01) — newest first
    assert items.index(beta) < items.index(alpha)


def test_validation_rejects_zero_amount(base_url):
    r = httpx.post(
        f"{base_url}/expenses",
        json={"amount": "0", "currency": "EUR", "category": "food", "date": "2026-04-12"},
    )
    assert r.status_code == 422


def test_data_persists_across_backend_restart(base_url, repo_root):
    """Expense written to SQLite must survive a backend container restart.

    Regression test for: /data directory not writable by container user (UID 1000)
    causes sqlite3.OperationalError at startup, crashing the backend so that
    nginx returns 502 on every request — including POST /expenses.
    """
    r = httpx.post(
        f"{base_url}/expenses",
        json={"amount": "7.77", "currency": "EUR", "category": "sys-test-persist", "date": "2026-04-13"},
    )
    assert r.status_code == 201, (
        f"POST /expenses returned {r.status_code} — backend may be crashing at startup "
        "(check that the data directory is writable by UID 1000)"
    )
    expense_id = r.json()["id"]

    subprocess.run(["docker", "compose", "restart", "backend"], cwd=repo_root, check=True)

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if httpx.get(f"{base_url}/health", timeout=2).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail(
            "Backend did not become healthy after restart — "
            "likely cannot open the SQLite database (check /data permissions)"
        )

    r2 = httpx.get(f"{base_url}/expenses")
    assert r2.status_code == 200
    assert any(e["id"] == expense_id for e in r2.json()), \
        "Expense not found after restart — data was not persisted to disk"
