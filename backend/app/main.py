import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.mcp_app import mcp
from app.oauth import router as oauth_router
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_db()
    async with mcp.session_manager.run():  # remote MCP server for demos (app/mcp_app.py)
        yield


app = FastAPI(title="Sponsr", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(router)
app.include_router(oauth_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Last, so the API routes win: /mcp plus the OAuth endpoints (/.well-known/*, /authorize, /token, /register,
# /revoke) that claude.ai expects at the site root.
app.mount("/", mcp.streamable_http_app())
