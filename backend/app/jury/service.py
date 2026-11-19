from threading import Lock
from uuid import UUID, uuid4

from ..core.model_api import ModelProvider

from . import demo
from .aggregate import comparison_view
from .models import Comparison, ComparisonRequest, ComparisonView, Panel, PanelRequest, Persona, Report, Trait
from .planner import derive_panel, extract_personas
from .repository import JuryRepository
from .sampling import SamplingError
from .simulation import next_exposure
from .theories import TheoryCatalog


class JuryError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


class JuryService:
    def __init__(self, repo: JuryRepository, provider: ModelProvider, catalog: TheoryCatalog):
        self.repo = repo
        self.provider = provider
        self.catalog = catalog
        self._lock = Lock()
        self._in_progress: set[UUID] = set()

    def upload_report(self, filename: str, text: str) -> Report:
        if self.provider.mode == "demo" and text != demo.REPORT:
            raise JuryError("演示模式使用预置报告。运行真实模式可分析自己的报告。")
        report = extract_personas(self.provider, filename, text)
        self.repo.create("report", report.report_id, report)
        return report

    def get_report(self, report_id: UUID) -> Report:
        report = self.repo.get("report", report_id, Report)
        if report is None:
            raise JuryError("找不到已上传的报告。", 404)
        return report

    def create_panel(self, request: PanelRequest) -> Panel:
        report = self.get_report(request.report_id)
        self._check_model(report)
        if request.manual_persona is not None:
            if self.provider.mode == "demo":
                raise JuryError("演示模式使用样例中已提取的画像。")
            persona = Persona(
                persona_id=uuid4(), name="用户确认画像",
                traits=[Trait(attribute="用户填写", value=request.manual_persona, status="user_supplied")],
            )
        else:
            persona = next((p for p in report.personas if p.persona_id == request.persona_id), None)
            if persona is None:
                raise JuryError("所选画像不属于这份报告。", 404)
        try:
            panel = derive_panel(
                self.provider, self.catalog, report.report_id, persona, request.member_count, request.sampling,
            )
        except SamplingError as error:
            raise JuryError(str(error), 422) from None
        self.repo.create("panel", panel.panel_id, panel)
        return panel

    def get_panel(self, panel_id: UUID) -> Panel:
        panel = self.repo.get("panel", panel_id, Panel)
        if panel is None:
            raise JuryError("找不到模拟面板。", 404)
        return panel

    def start_comparison(self, request: ComparisonRequest) -> ComparisonView:
        panel = self.get_panel(request.panel_id)
        self._check_model(panel)
        if self.provider.mode == "demo" and (request.original_text, request.revised_text) != (demo.ORIGINAL, demo.REVISED):
            raise JuryError("演示模式使用预置的两版文案。")
        comparison = Comparison(
            **request.model_dump(), comparison_id=uuid4(), mode=panel.mode, model=panel.model,
        )
        self.repo.create("comparison", comparison.comparison_id, comparison)
        return comparison_view(comparison, panel)

    def get_comparison(self, comparison_id: UUID) -> ComparisonView:
        comparison = self._get_comparison(comparison_id)
        return comparison_view(comparison, self.get_panel(comparison.panel_id))

    def advance(self, comparison_id: UUID, expected_index: int) -> ComparisonView:
        with self._lock:
            if comparison_id in self._in_progress:
                raise JuryError("该比较正在评估一个成员，请稍后重试。")
            self._in_progress.add(comparison_id)
        try:
            return self._advance(comparison_id, expected_index)
        finally:
            with self._lock:
                self._in_progress.remove(comparison_id)

    def _advance(self, comparison_id: UUID, expected_index: int) -> ComparisonView:
        comparison = self._get_comparison(comparison_id)
        panel = self.get_panel(comparison.panel_id)
        completed = len(comparison.exposures)
        if expected_index < completed:
            return comparison_view(comparison, panel)
        if expected_index != completed or completed == 2 * len(panel.members):
            raise JuryError("请根据当前比较返回的 next_index 继续。")
        self._check_model(comparison)
        exposure = next_exposure(self.provider, panel, comparison, expected_index)
        updated = comparison.model_copy(update={"exposures": [*comparison.exposures, exposure]})
        if self.repo.advance(updated, expected_index):
            return comparison_view(updated, panel)
        return self.get_comparison(comparison_id)

    def _get_comparison(self, comparison_id: UUID) -> Comparison:
        comparison = self.repo.get("comparison", comparison_id, Comparison)
        if comparison is None:
            raise JuryError("找不到该文案比较。", 404)
        return comparison

    def _check_model(self, record: Report | Panel | Comparison) -> None:
        if (record.mode, record.model) != (self.provider.mode, self.provider.model):
            raise JuryError("请使用该记录创建时的模型和运行模式。")
