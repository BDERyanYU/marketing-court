from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..core.model_api import ModelError, ModelProvider
from ..core.route_errors import model_error_response

from .api import build_router
from .config import database_path_from_env, provider_from_env
from .controller import CourtConflict, CourtController, CourtNotFound
from .demo import DEMO_INPUT
from .repository import CourtRepository, InputConflict


def register_court_routes(
    app: FastAPI, *, database_path: Path | None = None, provider: ModelProvider | None = None,
) -> None:
    repository = CourtRepository(database_path or database_path_from_env())
    provider = provider if provider is not None else provider_from_env()
    repository.register_input(DEMO_INPUT, keep_existing=True)
    controller = CourtController(repository, provider)
    app.include_router(build_router(repository, controller))

    @app.exception_handler(CourtNotFound)
    async def missing_case(_request: Request, error: CourtNotFound):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(InputConflict)
    @app.exception_handler(CourtConflict)
    async def conflict(_request: Request, error: InputConflict | CourtConflict):
        return JSONResponse(status_code=409, content={"detail": str(error)})


def create_app(*, database_path: Path | None = None, provider: ModelProvider | None = None) -> FastAPI:
    app = FastAPI(
        title="AI Marketing Court · P0",
        description="模拟庭审与风险复核建议。投放审批由人工负责。",
    )
    app.add_exception_handler(ModelError, model_error_response)
    provider = provider if provider is not None else provider_from_env()
    register_court_routes(app, database_path=database_path, provider=provider)

    @app.get("/health", tags=["Service"])
    def health():
        return {"status": "ok", "mode": provider.mode, "model": provider.model}

    @app.get("/", include_in_schema=False)
    def docs():
        return RedirectResponse("/docs")

    return app
