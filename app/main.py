"""FastAPI app: a small JSON API plus the static front end."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .cache import SimpleTTLCache
from .config import Settings
from .models import FeedbackIn, SuggestRequest, SuggestResponse
from .service import ServiceError, suggest
from .store import Store

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(
    settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    """Build the app. `transport` lets tests replace every outgoing HTTP call."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cfg = settings or Settings.from_env()
        app.state.settings = cfg
        app.state.store = Store(cfg.db_path)
        app.state.weather_cache = SimpleTTLCache(ttl_seconds=600.0)
        app.state.places_cache = SimpleTTLCache(ttl_seconds=600.0)
        async with httpx.AsyncClient(
            headers={"User-Agent": cfg.user_agent}, timeout=25.0, transport=transport
        ) as client:
            app.state.client = client
            yield

    app = FastAPI(title="Touch Grass Planner", version=__version__, lifespan=lifespan)

    @app.get("/api/health")
    async def health(request: Request) -> dict:
        cfg: Settings = request.app.state.settings
        client: httpx.AsyncClient = request.app.state.client
        status = {"ollama": False, "model": cfg.ollama_model, "model_available": False}
        try:
            response = await client.get(f"{cfg.ollama_url}/api/tags", timeout=3.0)
            response.raise_for_status()
            names = {m.get("name", "") for m in response.json().get("models", [])}
            status["ollama"] = True
            status["model_available"] = (
                cfg.ollama_model in names or f"{cfg.ollama_model}:latest" in names
            )
        except (httpx.HTTPError, ValueError):
            pass
        return status

    @app.post("/api/suggest", response_model=SuggestResponse)
    async def api_suggest(req: SuggestRequest, request: Request) -> SuggestResponse:
        try:
            return await suggest(
                request.app.state.client,
                request.app.state.settings,
                request.app.state.store,
                req,
                weather_cache=getattr(request.app.state, "weather_cache", None),
                places_cache=getattr(request.app.state, "places_cache", None),
            )
        except ServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    @app.post("/api/feedback", status_code=204)
    async def api_feedback(body: FeedbackIn, request: Request) -> Response:
        request.app.state.store.record(**body.model_dump())
        return Response(status_code=204)

    @app.get("/api/history")
    async def get_history(request: Request) -> dict:
        events = request.app.state.store.list_recent(limit=10)
        return {"events": events}

    @app.delete("/api/history", status_code=204)
    async def delete_history(request: Request) -> Response:
        request.app.state.store.clear()
        return Response(status_code=204)

    # Mounted last so the API routes above take priority.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
