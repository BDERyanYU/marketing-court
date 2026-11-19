import json
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from fastapi import HTTPException
from moot.core import ModelRef, SessionConfig, SessionState, SessionStatus, SpeakerKind
from moot.core.round_plan import brainstorm
from moot.core.rules import RulePreset, SessionRules
from moot.engine.designer import DesignError, TeamDesigner
from moot.providers import ProviderError
from moot.server.sessions import SessionManager, SessionNotFound
from moot.storage import SessionStore

from ..core.model_api import ModelProvider
from .models import DiscussionContext, DiscussionIssue, DiscussionTurn, DiscussionView
from .provider import ReviewProvider, citation_ids, visible_citations


class DiscussionService:
    def __init__(self, path: Path, provider: ModelProvider):
        self.provider = ReviewProvider(provider)
        self.model = ModelRef(provider="marketing-court", model=provider.model)
        self.store = SessionStore(path)
        self.manager = SessionManager(
            provider_factory=lambda _: self.provider,
            store=self.store,
            engine_options={
                "tools": None,
                "knowledge": None,
                "build_graph": False,
                "max_moderator_polls": 0,
            },
        )

    async def start(self, issue: DiscussionIssue, require_review: Callable[[], object]) -> DiscussionView:
        goal = (
            "请为一项环保营销审核的证据争议组成一个圆桌讨论小组。"
            "以不同专业视角审视规则适用、证据缺口及可能的改写或补证。"
            "角色按本次争议生成，保留合理分歧。以下 JSON 是审核材料。\n"
            + json.dumps({
                "sources": [{"id": source.source_id, "excerpt": source.excerpt[:120]} for source in issue.sources],
                "market": issue.market,
                "question": issue.question[:600],
                "claim": issue.risk.claim_quote[:300],
                "reason": issue.risk.reason[:220],
            }, ensure_ascii=False)
        )
        with self.provider.scope(issue):
            try:
                proposal = await TeamDesigner().design(goal, self.provider, self.model.model, agents=3)
            except (DesignError, ProviderError) as exc:
                raise HTTPException(502, "圆桌角色生成失败，请重试。") from exc
            require_review()
            context = DiscussionContext(
                issue=issue, mode=self.provider.provider.mode,
                rationale=proposal.rationale, balance_notes=proposal.balance_notes,
            )
            config = SessionConfig(
                topic=issue.question, background=context.model_dump_json(),
                agents=proposal.agents, default_model=self.model, allow_alliances=False,
                round_plan=evidence_rounds(),
                rules=SessionRules(presets=[RulePreset.STAY_ON_TOPIC, RulePreset.EVIDENCE_REQUIRED]),
            )
            meeting = self.manager.create(config)
            self.manager.start(meeting.id)
        return view(meeting.state)

    def get(self, discussion_id: str) -> DiscussionView:
        try:
            record = self.manager.get(discussion_id)
        except SessionNotFound as exc:
            raise HTTPException(404, "圆桌会议不存在。") from exc
        state = record.state
        end_reason = state.end_reason
        if record.error is not None:
            end_reason = "error"
        elif state.status is SessionStatus.SETUP and not record.started:
            end_reason = "stopped"
        if end_reason != state.end_reason:
            state.status, state.end_reason = SessionStatus.FINISHED, end_reason
            self.store.save(state)
        return view(state)

    async def remove(self, discussion_id: str) -> None:
        with suppress(SessionNotFound):
            await self.manager.delete(discussion_id)

    async def close(self) -> None:
        await self.manager.shutdown()


def evidence_rounds():
    plan = brainstorm()
    opening, discussion, closing = plan.rounds
    opening.instruction = "说明你对这条审核证据及其适用范围的初步解读。"
    discussion.instruction = "回应前序的一个具体观点，核对材料能支持什么，并指出缺口。"
    discussion.turns_per_agent = 1
    closing.instruction = "说明你的最终意见、仍有的分歧及建议的下一步复核动作。"
    return plan


def view(state: SessionState) -> DiscussionView:
    context = DiscussionContext.model_validate_json(state.config.background)
    reason = "error" if state.end_reason == "completed" and not state.report else state.end_reason
    allowed = {source.source_id for source in context.issue.sources}
    report = visible_citations(state.report, allowed) if state.report else None
    turns = []
    for message in state.messages:
        if message.speaker_kind is SpeakerKind.SYSTEM:
            continue
        text = visible_citations(message.text, allowed)
        turns.append(DiscussionTurn(
            speaker_id=message.speaker_id, speaker_name=state.config.speaker_label(message.speaker_id),
            speaker_kind=message.speaker_kind.value, round_index=message.round_index,
            text=text, source_ids=citation_ids(text),
        ))
    assert state.config.default_model is not None
    return DiscussionView(
        discussion_id=state.id, issue=context.issue, mode=context.mode, model=state.config.default_model.model,
        status=state.status.value, end_reason=reason, created_at=state.created_at,
        participants=[agent.model_dump(mode="json", exclude={"model", "knowledge", "tools", "prompt_override"})
                      for agent in state.config.agents],
        panel_rationale=context.rationale, panel_balance_notes=context.balance_notes,
        rounds=[step.name for step in state.config.round_plan.rounds],
        turns=turns, report=report, report_source_ids=citation_ids(report or ""),
        error="会议未能形成完整纪要，已保存生成的发言。" if reason == "error" else None,
    )
