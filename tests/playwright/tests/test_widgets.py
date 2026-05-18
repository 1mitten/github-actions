"""
Example smoke tests for the Widgets application.

Run all widgets tests:           pytest -m widgets
Run only fast widgets smoke:     pytest -m "widgets and smoke"
Run everything except slow:      pytest -m "not slow"
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.widgets
@pytest.mark.smoke
def test_homepage_responds(page: Page):
    """Tenant is up and serving HTML at /."""
    response = page.goto("/")
    assert response is not None
    # Any 2xx/3xx is fine — we just want to confirm reachability.
    assert response.status < 400, f"Got HTTP {response.status}"


@pytest.mark.widgets
@pytest.mark.smoke
def test_widgets_index_loads(page: Page):
    """Widgets list page renders without server error."""
    page.goto("/Widgets")
    # Replace with a stable selector for your app — h1 text, data-testid, etc.
    expect(page.locator("h1")).to_be_visible(timeout=10_000)


@pytest.mark.widgets
@pytest.mark.regression
@pytest.mark.slow
def test_widget_create_flow(page: Page):
    """Full happy-path: navigate, fill, submit, verify."""
    page.goto("/Widgets/Create")
    page.get_by_label("Name").fill("smoke-test-widget")
    page.get_by_role("button", name="Save").click()
    expect(page.locator(".alert-success")).to_be_visible(timeout=10_000)
