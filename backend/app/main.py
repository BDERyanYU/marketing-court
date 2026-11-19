from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .api.court import build_router
from .core.config import database_path_from_env, provider_from_env
from .court.controller import CourtConflict, CourtController, CourtNotFound
from .court.demo import DEMO_INPUT
from .core.llm import ModelError, ModelProvider
from .court.repository import CourtRepository, InputConflict


def create_app(*, database_path: Path | None = None, provider: ModelProvider | None = None) -> FastAPI:
    repository = CourtRepository(database_path or database_path_from_env())
    provider = provider if provider is not None else provider_from_env()
    repository.register_input(DEMO_INPUT, keep_existing=True)
    controller = CourtController(repository, provider)
    app = FastAPI(
        title="AI Marketing Court · P0",
        description="模拟庭审与风险复核建议。投放审批由人工负责。",
    )
    app.include_router(build_router(repository, controller))

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
