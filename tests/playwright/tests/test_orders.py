"""Example smoke tests for the Orders application."""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.orders
@pytest.mark.smoke
def test_orders_dashboard_loads(page: Page):
    page.goto("/Orders")
    expect(page.locator("h1")).to_be_visible(timeout=10_000)
