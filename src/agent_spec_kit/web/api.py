"""REST routes for the read-only results browser.

All endpoints return JSON. Errors return ``application/problem+json``
(RFC 7807) so the frontend can render consistent toasts and error pages.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from agent_spec_kit.result_store import LocalResultStore
from agent_spec_kit.storage_records import StorageConfig
from agent_spec_kit.web import loaders
from agent_spec_kit.web.schemas import (
    CompareResponse,
    ExperimentSummary,
    ProblemDetail,
    RepeatTrace,
    RunDetail,
    RunListItem,
    RunListPage,
    ScenarioRow,
)


def get_store(request: Request) -> LocalResultStore:
    """FastAPI dependency: per-app shared :class:`LocalResultStore`.

    Configured in ``server.create_app`` via ``app.state.store``.
    """
    store = getattr(request.app.state, "store", None)
    if store is None:
        store = LocalResultStore(StorageConfig())
        request.app.state.store = store
    return store


def problem_response(
    *, status: int, title: str, detail: str | None = None, instance: str | None = None
) -> JSONResponse:
    payload = ProblemDetail(
        title=title, status=status, detail=detail, instance=instance
    ).model_dump()
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type="application/problem+json",
    )


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments(
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> list[dict[str, Any]]:
    return store.list_experiments()


@router.get("/runs", response_model=RunListPage)
def list_runs(
    store: Annotated[LocalResultStore, Depends(get_store)],
    experiment_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = store.list_runs(
        limit=limit, offset=offset, experiment_id=experiment_id, status=status
    )
    total = store.count_runs(experiment_id=experiment_id, status=status)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/runs/{run_id}",
    response_model=RunDetail,
    responses={404: {"model": ProblemDetail}},
)
def get_run_detail(
    run_id: str,
    request: Request,
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> Any:
    row = store.get_run(run_id)
    if row is None:
        return problem_response(
            status=404,
            title="Run not found",
            detail=f"No run with id {run_id!r}",
            instance=str(request.url.path),
        )
    # `get_run` doesn't include all the metadata fields we want — re-fetch from the
    # connection for the full picture.
    with store._connect() as conn:  # noqa: SLF001 - intentional internal access
        full = conn.execute(
            """
            SELECT r.*, e.name AS experiment_name
            FROM runs r
            JOIN experiments e ON e.experiment_id = r.experiment_id
            WHERE r.run_id = ?
            """,
            (run_id,),
        ).fetchone()
    import json as _json

    return RunDetail(
        run_id=full["run_id"],
        experiment_id=full["experiment_id"],
        experiment_name=full["experiment_name"],
        status=full["status"],
        started_at=full["started_at"],
        finished_at=full["finished_at"],
        command=full["command"],
        notes=full["notes"],
        git_commit=full["git_commit"],
        git_branch=full["git_branch"],
        git_dirty=bool(full["git_dirty"]) if full["git_dirty"] is not None else None,
        python_version=full["python_version"],
        package_version=full["package_version"],
        summary=_json.loads(full["summary_json"]) if full["summary_json"] else {},
        metadata=_json.loads(full["metadata_json"]) if full["metadata_json"] else {},
    )


@router.get(
    "/runs/{run_id}/scenarios",
    response_model=list[ScenarioRow],
    responses={404: {"model": ProblemDetail}},
)
def list_scenarios_for_run(
    run_id: str,
    request: Request,
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> Any:
    if store.get_run(run_id) is None:
        return problem_response(
            status=404,
            title="Run not found",
            detail=f"No run with id {run_id!r}",
            instance=str(request.url.path),
        )
    return store.list_scenarios_for_run(run_id)


@router.get(
    "/runs/{run_id}/fuzz-trials",
    responses={404: {"model": ProblemDetail}},
)
def list_fuzz_trials_for_run_api(
    run_id: str,
    request: Request,
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> Any:
    if store.get_run(run_id) is None:
        return problem_response(
            status=404,
            title="Run not found",
            detail=f"No run with id {run_id!r}",
            instance=str(request.url.path),
        )
    return store.list_fuzz_trials_for_run(run_id)


@router.get(
    "/fuzz-trials/{trial_id}",
    responses={404: {"model": ProblemDetail}},
)
def get_fuzz_trial_detail(
    trial_id: str,
    request: Request,
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> Any:
    row = store.get_fuzz_trial(trial_id)
    if row is None:
        return problem_response(
            status=404,
            title="Fuzz trial not found",
            detail=f"No fuzz trial with id {trial_id!r}",
            instance=str(request.url.path),
        )
    return loaders.build_fuzz_trial_detail(row)


@router.get(
    "/runs/{run_id}/regressions",
    responses={404: {"model": ProblemDetail}},
)
def list_regressions_api(
    run_id: str,
    request: Request,
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> Any:
    if store.get_run(run_id) is None:
        return problem_response(
            status=404,
            title="Run not found",
            detail=f"No run with id {run_id!r}",
            instance=str(request.url.path),
        )
    return store.list_regressions_for_run(run_id)


@router.get(
    "/repeats/{repeat_result_id}/trace",
    response_model=RepeatTrace,
    responses={404: {"model": ProblemDetail}},
)
def get_repeat_trace(
    repeat_result_id: str,
    request: Request,
    store: Annotated[LocalResultStore, Depends(get_store)],
) -> Any:
    payload = loaders.build_repeat_trace(store, repeat_result_id)
    if payload is None:
        return problem_response(
            status=404,
            title="Repeat not found",
            detail=f"No repeat with id {repeat_result_id!r}",
            instance=str(request.url.path),
        )
    return payload


@router.get(
    "/compare",
    response_model=CompareResponse,
    responses={422: {"model": ProblemDetail}},
)
def compare_experiments(
    store: Annotated[LocalResultStore, Depends(get_store)],
    request: Request,
    experiments: str = Query(
        ..., description="comma-separated experiment ids; min 2"
    ),
    strategy: str = Query(default="most_recent"),
) -> Any:
    ids = [x.strip() for x in experiments.split(",") if x.strip()]
    if len(ids) < 2:
        return problem_response(
            status=422,
            title="At least two experiments required",
            detail="Pass `experiments=A,B[,C,...]` with two or more ids.",
            instance=str(request.url.path),
        )
    if len(set(ids)) != len(ids):
        return problem_response(
            status=422,
            title="Duplicate experiment ids",
            detail="Each experiment id must appear only once in `experiments=`.",
            instance=str(request.url.path),
        )
    if strategy != "most_recent":
        return problem_response(
            status=422,
            title="Unsupported compare strategy",
            detail=f"strategy={strategy!r} is not supported (only 'most_recent').",
            instance=str(request.url.path),
        )
    known = {e["experiment_id"] for e in store.list_experiments()}
    missing = [e for e in ids if e not in known]
    if missing:
        return problem_response(
            status=422,
            title="Unknown experiment id(s)",
            detail=f"Unknown experiment_ids: {', '.join(missing)}",
            instance=str(request.url.path),
        )
    return store.compare_experiments_most_recent(ids)


def install_problem_handlers(app: Any) -> None:
    """Register handlers that turn 404/422/etc. into ``application/problem+json``."""

    @app.exception_handler(HTTPException)
    def _http_exc(request: Request, exc: HTTPException) -> JSONResponse:
        return problem_response(
            status=exc.status_code,
            title=str(exc.detail) if exc.detail else "HTTP error",
            instance=str(request.url.path),
        )
