from pathlib import Path
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse

from .core.config import database_path_from_env, provider_from_env
from .core.llm import ModelError, ModelProvider
from .api.review import build_review_router
from .core.store import Store
from .services.ocr import ocr_from_env
from .workflows.review import ReviewWorkflow
from .jury.main import register_jury_routes
from .api.workspace import build_workspace_router
from .services.workspace import recover_meetings

# uvicorn loads .env before importing the app; Paddle models remain local to this project.
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(Path(__file__).resolve().parents[2] / "data" / "paddle-cache"))


def create_app(*, database_path: Path | None = None, provider: ModelProvider | None = None,
               storage_path: Path | None = None, ocr=None,
               jury_database_path: Path | None = None) -> FastAPI:
    path = database_path or database_path_from_env()
    store = Store(path)
    storage = storage_path or Path(os.environ.get("STORAGE_DIR", str(path.parent / "uploads")))
    provider = provider if provider is not None else provider_from_env()
    workflow = ReviewWorkflow(store, provider, ocr if ocr is not None else ocr_from_env(), storage)

    @asynccontextmanager
    async def lifespan(_app):
        store.recover()
        recover_meetings(store)
        yield

    app = FastAPI(
        title="AI Marketing Court · P0",
        description="营销素材审核、改写复核与消费者模拟。投放审批由人工负责。",
        lifespan=lifespan,
    )
    app.include_router(build_review_router(store, workflow, storage))
    app.include_router(build_workspace_router(store, workflow))
    jury_path = jury_database_path or Path(os.environ.get("JURY_DB_PATH", str(path.parent / "consumer-jury.sqlite3")))
    register_jury_routes(app, database_path=jury_path)

    @app.get("/", include_in_schema=False)
    def docs():
        return FileResponse(Path(__file__).with_name("index.html"), media_type="text/html")

    @app.get("/health", tags=["Service"])
    def health():
        return {"status": "ok", "mode": provider.mode, "model": provider.model}

    @app.exception_handler(ModelError)
    async def model_error(_request: Request, error: ModelError):
        return JSONResponse(status_code=502, content={"detail": str(error)})

    return app
