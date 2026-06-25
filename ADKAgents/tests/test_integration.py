"""Integration tests — hit the live Cloud Run service with real agent calls.

Run with:
    TEST_BASE_URL=https://agent-service-577303767450.asia-south1.run.app \
    pytest tests/test_integration.py -v
"""
import json
import allure
import httpx
import pytest

APP_NAME = "bank_agent"
_USER = "integration_smoke_user"


# ── Helpers ────────────────────────────────────────────────────────────────

def _create_session(url: str, user_id: str = _USER) -> str:
    with allure.step(f"Create session for user {user_id}"):
        resp = httpx.post(
            f"{url}/apps/{APP_NAME}/users/{user_id}/sessions",
            timeout=30,
        )
        assert resp.status_code == 200, f"Session create failed: {resp.text}"
        return resp.json()["id"]


def _send(url: str, session_id: str, message: str, user_id: str = _USER, timeout: int = 90) -> str:
    """Stream SSE from /run_sse and return the concatenated text response."""
    with allure.step(f"Send message: {message[:60]}"):
        payload = {
            "app_name": APP_NAME,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {"role": "user", "parts": [{"text": message}]},
            "streaming": True,
        }
        collected = []
        with httpx.stream("POST", f"{url}/run_sse", json=payload, timeout=timeout) as r:
            assert r.status_code == 200, f"run_sse returned {r.status_code}: {r.text}"
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = json.loads(raw)
                    for part in (event.get("content", {}).get("parts") or []):
                        collected.append(part.get("text", ""))
                except json.JSONDecodeError:
                    pass
        result = "".join(collected).strip()
        allure.attach(result, name="agent_response", attachment_type=allure.attachment_type.TEXT)
        return result


# ── Fixtures ───────────────────────────────────────────────────────────────

# Named api_url to avoid conflict with pytest-base-url plugin's reserved `base_url` fixture
@pytest.fixture(scope="module")
def api_url(live_base_url):
    return live_base_url


# ── Live tests ─────────────────────────────────────────────────────────────

@allure.feature("Agent Integration")
@allure.story("Service Health")
@allure.title("Service is reachable and bank_agent is registered")
@allure.severity(allure.severity_level.BLOCKER)
def test_service_is_reachable(api_url):
    resp = httpx.get(f"{api_url}/list-apps", timeout=30)
    assert resp.status_code == 200
    names = [a["name"] if isinstance(a, dict) else a for a in resp.json()]
    assert APP_NAME in names


@allure.feature("Agent Integration")
@allure.story("Session Management")
@allure.title("Session can be created and retrieved from live service")
@allure.severity(allure.severity_level.CRITICAL)
def test_session_create_and_retrieve(api_url):
    sid = _create_session(api_url, user_id=f"{_USER}_session")
    with allure.step("Retrieve the session by ID"):
        resp = httpx.get(
            f"{api_url}/apps/{APP_NAME}/users/{_USER}_session/sessions/{sid}",
            timeout=15,
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


@allure.feature("Agent Integration")
@allure.story("Mode C — Generic Query")
@allure.title("Generic market question answered without asking for customer ID")
@allure.severity(allure.severity_level.CRITICAL)
def test_mode_c_generic_query_no_customer_id_requested(api_url):
    sid = _create_session(api_url, user_id=f"{_USER}_modec")
    text = _send(api_url, sid, "What is the FTSE 100 index?", user_id=f"{_USER}_modec")
    assert len(text) > 20, f"Expected a real answer, got: {repr(text)}"
    low = text.lower()
    assert not ("customer id" in low and "to access" in low), (
        f"Agent wrongly asked for customer ID on generic query: {text[:300]}"
    )


@allure.feature("Agent Integration")
@allure.story("Mode B — Personal Query Without ID")
@allure.title("Personal query without customer ID triggers ID prompt")
@allure.severity(allure.severity_level.CRITICAL)
def test_mode_b_personal_query_without_id_asks_for_it(api_url):
    sid = _create_session(api_url, user_id=f"{_USER}_modeb")
    text = _send(
        api_url, sid,
        "Can you analyse my financial wellbeing?",
        user_id=f"{_USER}_modeb",
    )
    low = text.lower()
    assert any(k in low for k in ["customer id", "customer number", "your id", "what is your"]), (
        f"Expected agent to ask for customer ID, got: {text[:400]}"
    )


@allure.feature("Agent Integration")
@allure.story("Mode A — Authenticated Flow")
@allure.title("Customer ID C001 returns personalised account data")
@allure.severity(allure.severity_level.CRITICAL)
def test_mode_a_with_customer_id_returns_account_data(api_url):
    sid = _create_session(api_url, user_id=f"{_USER}_modea")
    text = _send(
        api_url, sid,
        "My customer ID is C001. Show me a summary of my accounts.",
        user_id=f"{_USER}_modea",
        timeout=120,
    )
    assert len(text) > 50, f"Expected substantive response, got: {repr(text)}"
    low = text.lower()
    assert any(k in low for k in ["£", "account", "balance", "savings", "current"]), (
        f"Expected account data in response, got: {text[:400]}"
    )


@allure.feature("Agent Integration")
@allure.story("Mode C — Generic Query")
@allure.title("Lloyds product query returns product names without requiring customer ID")
@allure.severity(allure.severity_level.NORMAL)
def test_mode_c_product_info_no_customer_id(api_url):
    sid = _create_session(api_url, user_id=f"{_USER}_products")
    text = _send(
        api_url, sid,
        "What savings accounts does Lloyds Bank offer?",
        user_id=f"{_USER}_products",
    )
    assert len(text) > 30, f"Expected product info, got: {repr(text)}"
    low = text.lower()
    assert any(k in low for k in ["saver", "isa", "savings", "account", "lloyds"]), (
        f"Expected Lloyds product names in response, got: {text[:400]}"
    )
