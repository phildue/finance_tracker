import httpx


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
    httpx.post(
        f"{base_url}/expenses",
        json={"amount": "10.00", "currency": "EUR", "category": "sys-test-alpha", "date": "2026-01-01"},
    )
    httpx.post(
        f"{base_url}/expenses",
        json={"amount": "20.00", "currency": "EUR", "category": "sys-test-beta", "date": "2026-03-01"},
    )

    r = httpx.get(f"{base_url}/expenses")
    assert r.status_code == 200
    items = r.json()

    alpha = next(e for e in items if e["category"] == "sys-test-alpha")
    beta = next(e for e in items if e["category"] == "sys-test-beta")
    # beta (2026-03-01) must appear before alpha (2026-01-01) — newest first
    assert items.index(beta) < items.index(alpha)


def test_validation_rejects_zero_amount(base_url):
    r = httpx.post(
        f"{base_url}/expenses",
        json={"amount": "0", "currency": "EUR", "category": "food", "date": "2026-04-12"},
    )
    assert r.status_code == 422
