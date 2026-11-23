"""One ASGI app on $PORT for Railway.

Upstream runs the web app and API on 8000 and the MCP server (SSE) plus chart
pictures on 8001. Railway gives a service one public port, so this serves both:
  /mcp, /mcp/messages/ and /images/  -> SQLBot's MCP app
  /healthz                           -> health check (app started, database answers)
  everything else                    -> SQLBot's web app and API
It also blocks /api/v1/mcp/mcp_assistant, an upstream endpoint that needs no
login, asks the default LLM (your API key) and calls any URL the caller gives.
"""
import re

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

import main  # SQLBot's backend (/opt/sqlbot/app/main.py)

BLOCKED = {"/api/v1/mcp/mcp_assistant"}


class BlockEndpoints:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = re.sub(r"/{2,}", "/", scope.get("path", "")).rstrip("/").lower()
            if path in BLOCKED:
                resp = JSONResponse(
                    {"code": 403, "data": None, "msg": "This endpoint is disabled on this deployment."},
                    status_code=403,
                )
                await resp(scope, receive, send)
                return
        await self.app(scope, receive, send)


# Outermost middleware: also applies to MCP tool calls, which reach the API in-process.
main.app.add_middleware(BlockEndpoints)


def _db_ok():
    from sqlalchemy import text
    from common.core.db import engine

    with engine.connect() as c:
        c.execute(text("SELECT 1"))


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        await main.app(scope, receive, send)
        return
    path = scope.get("path", "")
    if scope["type"] == "http" and path == "/healthz":
        try:
            await run_in_threadpool(_db_ok)
            resp = JSONResponse({"status": "ok"})
        except Exception:  # noqa: BLE001
            resp = JSONResponse({"status": "database unavailable"}, status_code=503)
        await resp(scope, receive, send)
        return
    if path == "/mcp" or path.startswith("/mcp/") or path.startswith("/images/"):
        await main.mcp_app(scope, receive, send)
        return
    await main.app(scope, receive, send)
