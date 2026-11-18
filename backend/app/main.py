"""FastAPI entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .court.main import register_court_routes
from .jury.main import register_jury_routes

from .core.model_api import ModelError
from .core.route_errors import model_error_response


def create_app(
    *, court_database_path: Path | None = None, jury_database_path: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="AI Marketing Court", version="0.1.0", description="庭审与消费者文案模拟。")
    app.add_exception_handler(ModelError, model_error_response)
    register_court_routes(app, database_path=court_database_path)
    register_jury_routes(app, database_path=jury_database_path)

    @app.get("/health", tags=["Service"])
    def health() -> dict[str, str]:
        """Confirm that the API process is running."""
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).with_name("index.html"), media_type="text/html")

    return app


app = create_app()
