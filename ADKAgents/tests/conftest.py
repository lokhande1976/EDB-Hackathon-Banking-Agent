import os
import pytest
import allure
from fastapi.testclient import TestClient

os.environ.setdefault("SESSION_DB_PATH", "/tmp/pytest_adk_sessions.db")
os.environ.setdefault("TRACE_TO_CLOUD", "false")


# ── FastAPI structural test client ─────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """In-process FastAPI test client — no real server, no LLM calls."""
    from main import app
    with TestClient(app) as c:
        yield c


# ── Live service URL ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def live_base_url():
    """Base URL for integration/Playwright tests. Set TEST_BASE_URL to enable."""
    url = os.environ.get("TEST_BASE_URL", "").rstrip("/")
    if not url:
        pytest.skip("TEST_BASE_URL not set — skipping live tests")
    return url


# ── Allure: capture Playwright screenshot on failure ──────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store per-phase (setup/call/teardown) result on the test item."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def allure_screenshot_on_failure(request):
    """After each Playwright test, attach a full-page screenshot if it failed."""
    yield
    if "page" not in request.fixturenames:
        return
    rep = getattr(request.node, "rep_call", None)
    if rep is None or not rep.failed:
        return
    try:
        page = request.getfixturevalue("page")
        allure.attach(
            page.screenshot(full_page=True),
            name="screenshot_on_failure",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(
            page.url,
            name="url_at_failure",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            page.title(),
            name="page_title",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass
