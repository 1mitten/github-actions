"""
Shared pytest fixtures for Playwright tests run via the SSM tunnel.

Environment variables (set by the composite action):
    BASE_URL          - e.g. https://localhost:8443
    APP_HOST_HEADER   - hostname the app expects (for host-based routing)
    TENANT_SLUG       - tenant identifier
    APP_NAME          - which app is under test

When running locally without the tunnel, point BASE_URL at the real URL and
leave APP_HOST_HEADER unset (or set to match BASE_URL's hostname).
"""
import os
import pytest


def _required(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        pytest.exit(f"Required environment variable {name!r} is not set", returncode=2)
    return val


@pytest.fixture(scope="session")
def base_url() -> str:
    return _required("BASE_URL")


@pytest.fixture(scope="session")
def app_host_header() -> str:
    # Falls back to the BASE_URL host if not provided — useful when not tunnelling.
    explicit = os.environ.get("APP_HOST_HEADER", "").strip()
    if explicit:
        return explicit
    from urllib.parse import urlparse
    return urlparse(_required("BASE_URL")).hostname or ""


@pytest.fixture(scope="session")
def tenant_slug() -> str:
    return os.environ.get("TENANT_SLUG", "test")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url, app_host_header):
    """Inject Host header and ignore self-signed cert (tunnel terminates TLS locally)."""
    extra_headers = dict(browser_context_args.get("extra_http_headers", {}))
    if app_host_header:
        extra_headers["Host"] = app_host_header
    return {
        **browser_context_args,
        "base_url": base_url,
        "ignore_https_errors": True,
        "extra_http_headers": extra_headers,
    }
