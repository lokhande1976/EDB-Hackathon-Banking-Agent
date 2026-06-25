"""Structural API tests — validate server behavior without any LLM calls."""
import os
import allure
import pytest

APP_NAME = "bank_agent"
USER_ID = "pytest_structural_user"


# ── App discovery ──────────────────────────────────────────────────────────

@allure.feature("API Layer")
@allure.story("App Discovery")
@allure.title("bank_agent appears in /list-apps")
@allure.severity(allure.severity_level.CRITICAL)
def test_list_apps_includes_bank_agent(client):
    resp = client.get("/list-apps")
    assert resp.status_code == 200
    apps = resp.json()
    names = [a["name"] if isinstance(a, dict) else a for a in apps]
    assert APP_NAME in names, f"Expected '{APP_NAME}' in {names}"


# ── Session management ─────────────────────────────────────────────────────

@allure.feature("API Layer")
@allure.story("Session Management")
@allure.title("POST /sessions returns a session ID")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_session_returns_id(client):
    resp = client.post(f"/apps/{APP_NAME}/users/{USER_ID}/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data, f"No 'id' in response: {data}"


@allure.feature("API Layer")
@allure.story("Session Management")
@allure.title("GET /sessions/{id} retrieves the created session")
@allure.severity(allure.severity_level.CRITICAL)
def test_get_session_by_id(client):
    create = client.post(f"/apps/{APP_NAME}/users/{USER_ID}/sessions")
    session_id = create.json()["id"]
    resp = client.get(f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session_id


@allure.feature("API Layer")
@allure.story("Session Management")
@allure.title("GET /sessions returns a list")
@allure.severity(allure.severity_level.NORMAL)
def test_list_sessions_returns_list(client):
    resp = client.get(f"/apps/{APP_NAME}/users/{USER_ID}/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@allure.feature("API Layer")
@allure.story("Session Management")
@allure.title("Unknown session ID returns 404")
@allure.severity(allure.severity_level.NORMAL)
def test_unknown_session_returns_404(client):
    resp = client.get(
        f"/apps/{APP_NAME}/users/{USER_ID}/sessions/does-not-exist-xyz-000"
    )
    assert resp.status_code == 404


# ── Static files ───────────────────────────────────────────────────────────

@allure.feature("API Layer")
@allure.story("Static Files")
@allure.title("/ui/ serves HTML")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_root_serves_html(client):
    resp = client.get("/ui/")
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "text/html" in ct, f"Expected HTML, got content-type: {ct}"


@allure.feature("API Layer")
@allure.story("Static Files")
@allure.title("index.html does not have immutable cache header")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_index_html_cache_header(client):
    resp = client.get("/ui/index.html")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "max-age=31536000" not in cc


@allure.feature("API Layer")
@allure.story("Static Files")
@allure.title("Vite-hashed assets have 1-year immutable cache header")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_assets_have_immutable_cache(client):
    assets_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "frontend", "dist", "assets",
    )
    if not os.path.isdir(assets_dir):
        pytest.skip("frontend/dist not built — run `npm run build` in frontend/")
    files = [f for f in os.listdir(assets_dir) if not f.startswith(".")]
    if not files:
        pytest.skip("No asset files found in frontend/dist/assets/")
    resp = client.get(f"/ui/assets/{files[0]}")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "max-age=31536000" in cc
    assert "immutable" in cc


# ── Observability endpoints ────────────────────────────────────────────────

@allure.feature("API Layer")
@allure.story("Observability")
@allure.title("/obs/summary returns 200")
@allure.severity(allure.severity_level.MINOR)
def test_obs_summary_ok(client):
    resp = client.get("/obs/summary")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@allure.feature("API Layer")
@allure.story("Observability")
@allure.title("/obs/traces returns a list")
@allure.severity(allure.severity_level.MINOR)
def test_obs_traces_ok(client):
    resp = client.get("/obs/traces")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@allure.feature("API Layer")
@allure.story("Observability")
@allure.title("/obs/tools returns 200")
@allure.severity(allure.severity_level.MINOR)
def test_obs_tools_ok(client):
    resp = client.get("/obs/tools")
    assert resp.status_code == 200


@allure.feature("API Layer")
@allure.story("Observability")
@allure.title("POST /obs/reset clears data")
@allure.severity(allure.severity_level.MINOR)
def test_obs_reset_ok(client):
    resp = client.post("/obs/reset")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


# ── Compression ────────────────────────────────────────────────────────────

@allure.feature("API Layer")
@allure.story("Compression")
@allure.title("GZip accepted on JSON responses")
@allure.severity(allure.severity_level.MINOR)
def test_gzip_accepted_on_json(client):
    resp = client.get("/list-apps", headers={"Accept-Encoding": "gzip"})
    assert resp.status_code == 200
