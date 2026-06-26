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


if __name__ == "__main__":
    # 3. Start the server!
    uvicorn.run(app, host="0.0.0.0", port=port)