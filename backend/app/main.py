from pathlib import Path
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .api.court import build_router
from .core.config import database_path_from_env, provider_from_env
from .court.controller import CourtConflict, CourtController, CourtNotFound
from .court.demo import DEMO_INPUT
from .core.llm import ModelError, ModelProvider
from .court.repository import CourtRepository, InputConflict
from .api.review import build_review_router, snapshot_for_risk
from .core.store import Store
from .services.ocr import PaddleOCRService
from .workflows.review import ReviewWorkflow

# uvicorn loads .env before importing the app; Paddle models remain local to this project.
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(Path(__file__).resolve().parents[2] / "data" / "paddle-cache"))


def create_app(*, database_path: Path | None = None, provider: ModelProvider | None = None,
               storage_path: Path | None = None, ocr=None) -> FastAPI:
    path = database_path or database_path_from_env()
    repository = CourtRepository(path)
    store = Store(path)
    storage = storage_path or Path(os.environ.get("STORAGE_DIR", str(path.parent / "uploads")))
    provider = provider if provider is not None else provider_from_env()
    repository.register_input(DEMO_INPUT, keep_existing=True)
    controller = CourtController(repository, provider)
    workflow = ReviewWorkflow(store, provider, ocr if ocr is not None else PaddleOCRService(), storage)

    @asynccontextmanager
    async def lifespan(_app):
        store.recover()
        yield

    app = FastAPI(
        title="AI Marketing Court · P0",
        description="模拟庭审与风险复核建议。投放审批由人工负责。",
        lifespan=lifespan,
    )
    app.include_router(build_router(repository, controller, lambda risk: snapshot_for_risk(store, risk)))
    app.include_router(build_review_router(store, workflow, repository, storage))

    @app.get("/", include_in_schema=False)
    def docs():
        return RedirectResponse("/docs")

    @app.get("/health", tags=["Service"])
    def health():
        return {"status": "ok", "mode": provider.mode, "model": provider.model}

    @app.exception_handler(CourtNotFound)
    async def missing_case(_request: Request, error: CourtNotFound):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(InputConflict)
    @app.exception_handler(CourtConflict)
    async def conflict(_request: Request, error: InputConflict | CourtConflict):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(ModelError)
    async def model_error(_request: Request, error: ModelError):
        return JSONResponse(status_code=502, content={"detail": str(error)})

    return app
