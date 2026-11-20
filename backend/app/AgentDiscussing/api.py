import logging
import sqlite3
from collections.abc import Callable
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import TYPE_CHECKING

from anyio import from_thread
from fastapi import APIRouter, HTTPException

from ..core.model_api import ModelProvider
from ..core.store import Store
from ..jury.repository import JuryRepository
from ..models.review import Review
from .invitees import resolve_invitee
from .models import (
    DiscussionIssue, DiscussionRequest, DiscussionView, InviteeOption, InviteePanel,
    StandaloneIssue, StandaloneRequest,
)

if TYPE_CHECKING:
    from .service import DiscussionService


def build_discussion_routes(
    store: Store, provider: ModelProvider, app_database: Path, jury: JuryRepository,
) -> tuple[APIRouter, Callable[[str], bool]]:
    service: DiscussionService | None = None
    database_path = app_database.with_name(f"{app_database.name}.agent-discussions.sqlite3")

    @asynccontextmanager
    async def lifespan(_app):
        nonlocal service
        try:
            yield
        finally:
            if service is not None:
                await service.close()
                service = None

    router = APIRouter(prefix="/api", tags=["AgentDiscussing"], lifespan=lifespan)

    def runtime() -> "DiscussionService":
        nonlocal service
        if service is None:
            try:
                from .service import DiscussionService
            except ModuleNotFoundError as exc:
                raise HTTPException(503, "请运行 uv sync --locked --inexact --extra roundtable 安装圆桌依赖。") from exc
            service = DiscussionService(database_path, provider)
        return service

    @router.post("/reviews/{review_id}/risks/{risk_id}/discussions",
                 response_model=DiscussionView, status_code=202)
    async def start(review_id: str, risk_id: str, request: DiscussionRequest):
        """Design the panel and start a discussion about one frozen review risk."""
        review = store.get("review", review_id, Review)
        risk = next((risk for risk in review.risks if risk.risk_id == risk_id), None)
        if risk is None:
            raise HTTPException(404, "所选风险不属于该次审核。")
        issue = DiscussionIssue(
            question=request.question, invitee=request.invitee, review_id=review.review_id, project_id=review.project_id,
            asset_version_id=review.asset_version_id, market=review.market, rule_pack_version=review.rule_pack_version,
            risk=risk, sources=[source for source in review.sources if source.source_id in risk.source_ids],
        )
        guest = resolve_invitee(jury, request.invitee) if request.invitee else None
        return await runtime().start(issue, guest=guest, require_review=lambda: store.get("review", review_id, Review))

    @router.post("/discussions", response_model=DiscussionView, status_code=202)
    async def start_standalone(request: StandaloneRequest):
        """Start a roundtable on a user-supplied topic."""
        issue = StandaloneIssue(**request.model_dump())
        guest = resolve_invitee(jury, request.invitee) if request.invitee else None
        return await runtime().start(issue, guest=guest)

    @router.get("/discussions/invitees", response_model=list[InviteePanel])
    def invitees():
        """List the saved digital personas available to this workspace."""
        return [
            InviteePanel(
                panel_id=panel.panel_id, report_name=report_name,
                base_persona_name=panel.base_persona.name if panel.base_persona else None,
                members=[InviteeOption(member_id=member.member_id, name=member.name) for member in panel.members],
            )
            for panel, report_name in jury.panels_with_report_names() if panel.members
        ]

    @router.get("/discussions/{discussion_id}", response_model=DiscussionView)
    async def discussion(discussion_id: str):
        """Read saved evidence, participants, turns and the moderator’s report."""
        meeting = runtime().get(discussion_id)
        if isinstance(meeting.issue, DiscussionIssue):
            store.get("review", meeting.issue.review_id, Review)
        return meeting

    async def purge_project(project_id: str) -> None:
        # The pinned Moot store cascades a session deletion to its events and progress.
        owner = "json_extract(json_extract(state, '$.config.background'), '$.issue.project_id')"
        with closing(sqlite3.connect(database_path)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            if service is not None:
                rows = db.execute(f"SELECT id FROM sessions WHERE {owner} = ?", (project_id,)).fetchall()
                for (discussion_id,) in rows:
                    await service.remove(discussion_id)
            with db:
                db.execute(f"DELETE FROM sessions WHERE {owner} = ?", (project_id,))

    def delete_project_discussions(project_id: str) -> bool:
        if not database_path.is_file():
            return True
        try:
            from_thread.run(purge_project, project_id)
        except (OSError, sqlite3.Error):
            logging.getLogger(__name__).warning("Could not clean up project discussions", exc_info=True)
            return False
        return True

    return router, delete_project_discussions
