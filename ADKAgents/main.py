#def main():
#    print("Hello from adkagents!")


import os
import uvicorn
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
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


if __name__ == "__main__":
    # 3. Start the server!
    uvicorn.run(app, host="0.0.0.0", port=port)