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
    """Verify HTML5 required attribute prevents form submission with empty required fields."""
    page.goto(ui_url)
    page.wait_for_load_state("networkidle")
    initial_row_count = page.locator("tbody tr").count()
    page.fill("#amount", "")
    page.fill("#category", "")
    page.fill("#date", "")
    page.click('button[type="submit"]')
    page.wait_for_timeout(500)
    assert page.locator("tbody tr").count() == initial_row_count
