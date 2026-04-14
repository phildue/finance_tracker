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


def test_delete_selected_expense(page, ui_url):
    page.goto(ui_url)
    page.wait_for_load_state("networkidle")

    page.fill("#amount", "33.33")
    page.fill("#currency", "EUR")
    page.fill("#category", "sys-test-ui-delete-selected")
    page.fill("#date", "2026-04-14")
    page.click('button[type="submit"]')
    page.wait_for_selector('td:has-text("sys-test-ui-delete-selected")')

    row = page.locator("tbody tr", has=page.locator('td:has-text("sys-test-ui-delete-selected")'))
    row.locator('input[type="checkbox"]').check()
    page.wait_for_selector('button:has-text("Delete selected")')

    page.once("dialog", lambda dialog: dialog.accept())
    page.click('button:has-text("Delete selected")')
    page.wait_for_timeout(500)

    assert page.locator('td:has-text("sys-test-ui-delete-selected")').count() == 0


def test_delete_all_via_toolbar(page, ui_url):
    page.goto(ui_url)
    page.wait_for_load_state("networkidle")

    page.fill("#amount", "44.44")
    page.fill("#currency", "EUR")
    page.fill("#category", "sys-test-ui-delete-all")
    page.fill("#date", "2026-04-14")
    page.click('button[type="submit"]')
    page.wait_for_selector('td:has-text("sys-test-ui-delete-all")')

    page.locator("tbody input[type='checkbox']").first.check()
    page.wait_for_selector('button:has-text("Delete all")')

    page.once("dialog", lambda dialog: dialog.accept())
    page.click('button:has-text("Delete all")')
    page.wait_for_selector('p:has-text("No expenses yet")')
