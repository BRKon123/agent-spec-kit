"""FastAPI app factory and SPA static mount."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent_spec_kit.result_store import LocalResultStore
from agent_spec_kit.storage_records import StorageConfig
from agent_spec_kit.web.api import install_problem_handlers, problem_response, router

DIST_DIR = Path(__file__).resolve().parent / "dist"


def create_app(
    *,
    storage: StorageConfig | None = None,
    cors_origins: list[str] | None = None,
    serve_frontend: bool = True,
) -> FastAPI:
    """Build the FastAPI application.

    Parameters
    ----------
    storage:
        Override the storage location (defaults to ``StorageConfig()`` which
        resolves to ``.agent_spec_kit/`` in the current working directory).
    cors_origins:
        Allowed origins. Defaults to common Vite dev ports so ``npm run dev``
        works without extra config. Pass ``[]`` to disable.
    serve_frontend:
        If ``True`` (default) and the bundled SPA is built, mount it at ``/``.
        If the dist directory has no ``index.html``, ``/`` returns a helpful
        message instead of 404.
    """
    app = FastAPI(title="agent-spec-kit results", version="0.1.0")
    app.state.store = LocalResultStore(storage or StorageConfig())

    origins = cors_origins if cors_origins is not None else [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    install_problem_handlers(app)
    app.include_router(router)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return problem_response(
            status=500,
            title="Internal server error",
            detail=f"{type(exc).__name__}: {exc}",
            instance=str(request.url.path),
        )

    if serve_frontend:
        _mount_spa(app)
    return app


def _mount_spa(app: FastAPI) -> None:
    index = DIST_DIR / "index.html"
    if not index.exists():
        @app.get("/")
        def _missing_dist() -> dict[str, Any]:
            return {
                "status": "ui_not_built",
                "detail": (
                    "The SPA bundle is missing. Build it with: "
                    "`npm --prefix frontend install && npm --prefix frontend run build`. "
                    "API endpoints under /api are still available."
                ),
                "expected_path": str(DIST_DIR),
            }
        return

    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def _spa_fallback(full_path: str) -> Any:
        # Serve real files (favicon, vite.svg, etc.) directly...
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # ...otherwise let the SPA router handle it.
        return FileResponse(index)


__all__ = ["DIST_DIR", "create_app"]
