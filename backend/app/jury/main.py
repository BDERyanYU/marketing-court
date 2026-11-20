import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..core.model_api import ModelError, ModelProvider, configured_provider
from ..core.paths import PROJECT_ROOT
from ..core.route_errors import model_error_response

from . import demo
from .examples import PAPER_REPORT, PAPER_ORIGINAL, PAPER_REVISED, PAPER_NOTICE
from .models import AdvanceRequest, ComparisonRequest, ComparisonView, Panel, PanelRequest, Report
from .parsing import MAX_FILE_BYTES, ReportError, read_report
from .repository import JuryRepository
from .service import DEFAULT_MAX_CONCURRENT_MEMBERS, JuryError, JuryService
from .theories import TheoryCatalog


MODULE = Path(__file__).resolve().parent


def provider_from_env() -> ModelProvider:
    return configured_provider(
        demo.DemoProvider, mode_variable="JURY_MODE", model_variable="JURY_DEEPSEEK_MODEL", max_tokens=2000,
    )


def register_jury_routes(
    app: FastAPI,
    *,
    database_path: Path | None = None,
    provider: ModelProvider | None = None,
    skill_path: Path | None = None,
    page_path: str = "/jury",
) -> JuryRepository:
    provider = provider if provider is not None else provider_from_env()
    configured_skill = os.environ.get("JURY_THEORY_SKILL_FILE")
    if skill_path is None and configured_skill:
        skill_path = Path(configured_skill)
    if database_path is None:
        default_path = PROJECT_ROOT / "var" / "consumer-jury.sqlite3"
        database_path = Path(os.environ.get("JURY_DB_PATH", str(default_path))).expanduser()

    try:
        member_limit = int(os.environ.get("JURY_MAX_CONCURRENT_MEMBERS", str(DEFAULT_MAX_CONCURRENT_MEMBERS)))
        if member_limit < 1:
            raise ValueError
    except ValueError:
        raise RuntimeError("JURY_MAX_CONCURRENT_MEMBERS must be a positive integer.") from None
    service = JuryService(
        JuryRepository(database_path), provider, TheoryCatalog(skill_path), max_concurrent_members=member_limit,
    )
    router = APIRouter(prefix="/api/jury", tags=["Consumer Jury"])

    @app.get(page_path, include_in_schema=False)
    def index():
        return FileResponse(MODULE / "index.html", media_type="text/html")

    @router.get("/demo")
    def demo_example():
        return {"report_text": demo.REPORT, "original_text": demo.ORIGINAL, "revised_text": demo.REVISED,
                "mode": provider.mode, "model": provider.model}

    @router.get("/examples/{example_id}")
    def example(example_id: str):
        if example_id != "copier-paper":
            raise HTTPException(404, "找不到这个数字人像测试样例。")
        return {"report_text": PAPER_REPORT, "original_text": PAPER_ORIGINAL, "revised_text": PAPER_REVISED,
                "filename": "复印纸-用户画像调研报告.txt", "notice": PAPER_NOTICE,
                "mode": provider.mode, "model": provider.model}

    @router.post("/reports", status_code=201, response_model=Report)
    def upload_report(file: UploadFile) -> Report:
        filename = Path((file.filename or "report.txt").replace("\\", "/")).name
        text = read_report(filename, file.file.read(MAX_FILE_BYTES + 1))
        return service.upload_report(filename, text)

    @router.get("/reports/{report_id}", response_model=Report)
    def get_report(report_id: UUID) -> Report:
        return service.get_report(report_id)

    @router.post("/panels", status_code=201, response_model=Panel)
    def create_panel(request: PanelRequest) -> Panel:
        return service.create_panel(request)

    @router.get("/panels/{panel_id}", response_model=Panel)
    def get_panel(panel_id: UUID) -> Panel:
        return service.get_panel(panel_id)

    @router.post("/comparisons", status_code=201, response_model=ComparisonView)
    def start_comparison(request: ComparisonRequest) -> ComparisonView:
        return service.start_comparison(request)

    @router.get("/comparisons/{comparison_id}", response_model=ComparisonView)
    def get_comparison(comparison_id: UUID) -> ComparisonView:
        return service.get_comparison(comparison_id)

    @router.post("/comparisons/{comparison_id}/advance", response_model=ComparisonView)
    def advance(comparison_id: UUID, request: AdvanceRequest) -> ComparisonView:
        return service.advance(comparison_id, request.expected_index)

    @router.post("/comparisons/{comparison_id}/advance-members", response_model=ComparisonView)
    def advance_members(comparison_id: UUID, request: AdvanceRequest) -> ComparisonView:
        return service.advance(comparison_id, request.expected_index, parallel=True)

    @app.exception_handler(ReportError)
    @app.exception_handler(JuryError)
    async def input_error(_request: Request, error: ReportError | JuryError):
        return JSONResponse(status_code=error.status, content={"detail": str(error)})

    app.include_router(router)
    return service.repo


def create_app(
    *, database_path: Path | None = None,
    provider: ModelProvider | None = None,
    skill_path: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="AI Marketing Court · 营销模拟", description="用户画像驱动的配对文案模拟。")
    app.add_exception_handler(ModelError, model_error_response)
    register_jury_routes(app, database_path=database_path, provider=provider, skill_path=skill_path, page_path="/")
    return app
