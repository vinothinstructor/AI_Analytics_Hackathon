"""FastAPI application entry point (B3).

Routes carry NO /api prefix — the Vite dev proxy strips /api before forwarding
(/api/health -> /health). Runs on port 8003.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .llm.cached_client import CacheMissError
from .llm.live_client import AzureCredentialsMissingError
from .routers import chat, debug, health, overview

app = FastAPI(title="Solution 3 — IQVIA AI Analytics", version="0.1.0")

# Permissive CORS for local dev (frontend on a Vite-picked port).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AzureCredentialsMissingError)
def _azure_missing_handler(request: Request, exc: AzureCredentialsMissingError):
    # Fail loud: LIVE without creds surfaces a readable 500, never a silent fallback.
    return JSONResponse(status_code=500, content={"error": "live_unavailable", "detail": str(exc)})


@app.exception_handler(CacheMissError)
def _cache_miss_handler(request: Request, exc: CacheMissError):
    return JSONResponse(status_code=500, content={"error": "cache_miss", "detail": str(exc)})


app.include_router(health.router)
app.include_router(debug.router)
app.include_router(chat.router)
app.include_router(overview.router)
