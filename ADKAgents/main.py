#def main():
#    print("Hello from adkagents!")


import os
import sqlite3
import uuid
from datetime import date

import uvicorn
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from google.adk.cli.fast_api import get_fast_api_app

# 1. Grab the dynamic port assigned by Google Cloud Run
port = int(os.environ.get("PORT", 8080))

# 2. Wrap your ADK agent in a production-ready FastAPI web server
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

_session_db = os.environ.get("SESSION_DB_PATH", "/tmp/adk_sessions.db")
app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=["*"],
    web=True,
    trace_to_cloud=os.environ.get("TRACE_TO_CLOUD", "false").lower() == "true",
    session_service_uri=f"sqlite:///{_session_db}",
)

# Compress all text/json responses >= 1 KB
app.add_middleware(GZipMiddleware, minimum_size=1000)


class StaticCacheMiddleware(BaseHTTPMiddleware):
    """Cache headers for Vite-hashed assets (1 year) and HTML (5 min)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/ui/assets/"):
            # Vite content-hashes filenames — immutable for 1 year
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path in ("/ui", "/ui/", "/ui/index.html"):
            response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
        return response


app.add_middleware(StaticCacheMiddleware)

# 3. Serve the React frontend at /ui (built via `npm run build` in frontend/)
_frontend_dist = os.path.join(AGENT_DIR, "frontend", "dist")
if os.path.exists(_frontend_dist):
    app.mount("/ui", StaticFiles(directory=_frontend_dist, html=True), name="ui")

_automation_ui_dist = os.path.join(AGENT_DIR, "automation_ui", "dist")
if os.path.exists(_automation_ui_dist):
    app.mount("/automation-ui", StaticFiles(directory=_automation_ui_dist, html=True), name="automation-ui")


from fastapi.responses import HTMLResponse
from bank_agent.observability import store, CostGranularity


@app.get("/obs", response_class=HTMLResponse)
async def obs_dashboard():
    """Serves the frontend dashboard for agent observability."""
    html_path = os.path.join(AGENT_DIR, "bank_agent", "observability", "dashboard.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="Dashboard file not found.", status_code=404)


@app.get("/obs/summary")
async def obs_summary(granularity: str | None = None):
    """Aggregated stats: sessions, total tokens, cost, avg latency.

    Optional ``?granularity=session|turn|cumulative`` query param overrides
    the default (env ``COST_GRANULARITY``).
    """
    gran = None
    if granularity:
        try:
            gran = CostGranularity(granularity.strip().lower())
        except ValueError:
            pass
    return store.get_summary(granularity=gran)


@app.get("/obs/traces")
async def obs_traces(limit: int = 100):
    """Individual LLM call records (newest first).

    Optional ``?limit=N`` query param controls the number of records returned
    (default 100).
    """
    return store.get_traces(limit=limit)


@app.get("/obs/tools")
async def obs_tools():
    """Per-tool call counts, success rates, and duration percentiles."""
    return store.get_tool_stats()


@app.post("/obs/reset")
async def obs_reset():
    """Clear all recorded observability data."""
    store.reset()
    return {"status": "ok", "message": "Observability data cleared"}


# ── Account opening endpoint ──────────────────────────────────────────────────

class ApplyRequest(BaseModel):
    product_name: str
    customer_id: str | None = None
    customer_name: str | None = None


_CREATE_APPS_TABLE = """
    CREATE TABLE IF NOT EXISTS applications (
        application_id TEXT PRIMARY KEY,
        customer_id    TEXT,
        customer_name  TEXT,
        product_name   TEXT NOT NULL,
        product_type   TEXT,
        interest_rate  REAL,
        status         TEXT DEFAULT 'submitted',
        applied_date   TEXT,
        product_url    TEXT
    )
"""

_DB_PATH = os.path.join(AGENT_DIR, "bank_data.db")


@app.post("/apply")
async def apply_for_account(req: ApplyRequest):
    """Direct account-opening endpoint — no agent roundtrip needed.

    Validates the product exists, inserts an application record and returns
    the application reference.
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.execute(_CREATE_APPS_TABLE)
        conn.commit()

        # Look up product
        cursor = conn.cursor()
        cursor.execute(
            "SELECT product_name, product_type, interest_rate_pa, product_url "
            "FROM products WHERE LOWER(product_name) = LOWER(?)",
            [req.product_name],
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(
                status_code=404,
                content={"status": "error", "error": f"Product '{req.product_name}' not found."},
            )
        pname, ptype, rate, purl = row

        application_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
        applied_date = date.today().isoformat()
        customer_name = req.customer_name or "Account Holder"

        cursor.execute(
            """INSERT INTO applications
                   (application_id, customer_id, customer_name, product_name,
                    product_type, interest_rate, status, applied_date, product_url)
               VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?)""",
            [application_id, req.customer_id or "", customer_name,
             pname, ptype, rate or 0.0, applied_date, purl or ""],
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "application_id": application_id,
            "product_name": pname,
            "product_type": ptype,
            "interest_rate_pa": rate or 0.0,
            "customer_id": req.customer_id or "",
            "customer_name": customer_name,
            "applied_date": applied_date,
            "product_url": purl or "",
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(exc)})


@app.get("/applications")
async def get_applications(customer_id: str | None = None):
    """List submitted account applications, optionally filtered by customer_id."""
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.execute(_CREATE_APPS_TABLE)
        conn.commit()
        cursor = conn.cursor()
        if customer_id:
            cursor.execute(
                "SELECT * FROM applications WHERE customer_id = ? ORDER BY applied_date DESC",
                [customer_id],
            )
        else:
            cursor.execute("SELECT * FROM applications ORDER BY applied_date DESC")
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        conn.close()
        return {"status": "success", "applications": rows}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(exc)})


# ── Automation Framework Generator endpoint ───────────────────────────────────

class GenerateFrameworkRequest(BaseModel):
    project_name:   str
    group_id:       str
    artifact_id:    str
    language:       str           # java | typescript | javascript | python | csharp | ruby
    framework:      str           # playwright | cypress | selenium | webdriverio | puppeteer
    build_tool:     str = "Maven"
    test_runner:    str = "TestNG"
    app_url:        str = ""
    pages:          list[str] = []
    test_scenarios: str = "verify page loads, verify positive flow, verify error handling"
    browser:        str = "chromium"
    author:         str = "Developer"


@app.post("/api/generate-framework")
async def generate_framework(req: GenerateFrameworkRequest):
    """Generate a complete automation framework from project requirements.

    Returns a JSON list of {filename, content} dicts — one entry per generated file.
    No agent roundtrip; tools are called directly for speed.
    """
    try:
        files: list[dict] = []
        pkg  = req.group_id
        ns   = "".join(w.capitalize() for w in req.project_name.split())
        pages = req.pages if req.pages else ["Home", "Login"]
        scenarios = req.test_scenarios

        lang = req.language.lower()
        fw   = req.framework.lower()

        # ── Java ─────────────────────────────────────────────────────────────
        if lang == "java":
            from automation_agent.tools import (
                generate_pom_xml, generate_testng_xml, generate_folder_manifest,
                generate_base_page, generate_base_test, generate_page_object,
                generate_test_class, generate_constants,
                generate_config_reader, generate_wait_helper, generate_screenshot_util,
                generate_excel_reader, generate_config_properties,
                generate_log4j2_config, generate_allure_properties,
            )
            pkg_path = pkg.replace(".", "/")
            files += [
                generate_pom_xml(req.project_name, pkg, req.artifact_id),
                generate_testng_xml(req.project_name, [p.replace(" ", "") + "Test" for p in pages], pkg),
                generate_folder_manifest(req.artifact_id, pkg_path),
                generate_constants(pkg, req.app_url),
                generate_base_page(pkg),
                generate_base_test(pkg, req.browser),
                generate_config_reader(pkg),
                generate_wait_helper(pkg),
                generate_screenshot_util(pkg),
                generate_excel_reader(pkg),
                generate_config_properties(req.app_url, req.browser),
                generate_log4j2_config(),
                generate_allure_properties(),
            ]
            for page in pages:
                files.append(generate_page_object(page, pkg, req.app_url, f"{page} page elements"))
                files.append(generate_test_class(page, page, pkg, scenarios))

        # ── TypeScript / JavaScript — Playwright ─────────────────────────────
        elif lang in ("typescript", "javascript") and fw == "playwright":
            from automation_agent.tools import (
                generate_ts_playwright_package_json, generate_ts_playwright_config,
                generate_ts_playwright_tsconfig, generate_ts_playwright_base_page,
                generate_ts_playwright_fixtures, generate_ts_playwright_env,
                generate_ts_playwright_utils, generate_ts_playwright_page_object,
                generate_ts_playwright_test,
            )
            files += [
                generate_ts_playwright_package_json(req.project_name, req.artifact_id),
                generate_ts_playwright_config(req.project_name, req.app_url, req.browser),
                generate_ts_playwright_tsconfig(),
                generate_ts_playwright_base_page(pkg),
                generate_ts_playwright_fixtures(pkg),
                generate_ts_playwright_env(),
                generate_ts_playwright_utils(),
            ]
            for page in pages:
                files.append(generate_ts_playwright_page_object(page, req.app_url, f"{page} page elements"))
                files.append(generate_ts_playwright_test(page, page, scenarios))

        # ── TypeScript / JavaScript — Cypress ────────────────────────────────
        elif lang in ("typescript", "javascript") and fw == "cypress":
            from automation_agent.tools import (
                generate_cypress_package_json, generate_cypress_config,
                generate_cypress_support_commands, generate_cypress_support_e2e,
                generate_cypress_page_object, generate_cypress_test,
            )
            files += [
                generate_cypress_package_json(req.project_name, req.artifact_id),
                generate_cypress_config(req.project_name, req.app_url),
                generate_cypress_support_commands(),
                generate_cypress_support_e2e(),
            ]
            for page in pages:
                files.append(generate_cypress_page_object(page, req.app_url, f"{page} page elements"))
                files.append(generate_cypress_test(page, page, scenarios))

        # ── Python ───────────────────────────────────────────────────────────
        elif lang == "python":
            from automation_agent.tools import (
                generate_python_pyproject_toml, generate_python_conftest,
                generate_python_base_page, generate_python_page_object, generate_python_test,
            )
            files += [
                generate_python_pyproject_toml(req.project_name, req.artifact_id, fw),
                generate_python_conftest(pkg, req.app_url, fw),
                generate_python_base_page(pkg, fw),
            ]
            for page in pages:
                files.append(generate_python_page_object(page, req.app_url, f"{page} page elements", fw))
                files.append(generate_python_test(page, page, scenarios, fw))

        # ── C# ───────────────────────────────────────────────────────────────
        elif lang == "csharp":
            from automation_agent.tools import (
                generate_csharp_csproj, generate_csharp_appsettings,
                generate_csharp_base_page, generate_csharp_base_test,
                generate_csharp_page_object, generate_csharp_test,
            )
            files += [
                generate_csharp_csproj(req.project_name, req.artifact_id, fw),
                generate_csharp_appsettings(req.app_url, req.browser),
                generate_csharp_base_page(f"{ns}.Automation", fw),
                generate_csharp_base_test(f"{ns}.Automation", fw),
            ]
            for page in pages:
                files.append(generate_csharp_page_object(page, f"{ns}.Automation", req.app_url, f"{page} elements", fw))
                files.append(generate_csharp_test(page, page, f"{ns}.Automation", scenarios, fw))

        else:
            return JSONResponse(
                status_code=422,
                content={"error": f"Unsupported combination: {lang} + {fw}. Supported: java+playwright/selenium, typescript+playwright/cypress, python+playwright/selenium, csharp+playwright/selenium."},
            )

        # ── CI/CD — shared for all stacks ────────────────────────────────────
        from automation_agent.tools import (
            generate_github_actions, generate_dockerfile,
            generate_docker_compose, generate_readme,
        )
        files += [
            generate_github_actions(req.project_name),
            generate_dockerfile(req.project_name),
            generate_docker_compose(req.project_name, req.app_url),
            generate_readme(req.project_name, pkg, req.artifact_id, req.app_url, req.author),
        ]

        # Filter out None/empty and deduplicate by filename
        seen: set[str] = set()
        unique: list[dict] = []
        for f in files:
            if f and f.get("filename") and f["filename"] not in seen:
                seen.add(f["filename"])
                unique.append(f)

        return {"files": unique, "total": len(unique), "language": lang, "framework": fw}

    except Exception as exc:
        import traceback
        return JSONResponse(status_code=500, content={"error": str(exc), "detail": traceback.format_exc()})


if __name__ == "__main__":
    # 3. Start the server!
    uvicorn.run(app, host="0.0.0.0", port=port)