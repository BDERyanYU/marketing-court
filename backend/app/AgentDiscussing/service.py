import json
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from fastapi import HTTPException
from moot.core import AIModerator, ModelRef, SessionConfig, SessionState, SessionStatus, SpeakerKind
from moot.core.round_plan import brainstorm
from moot.core.rules import RulePreset, SessionRules
from moot.engine.designer import MIN_AGENTS, DesignError, TeamDesigner
from moot.providers import ProviderError
from moot.server.sessions import SessionManager, SessionNotFound
from moot.storage import SessionStore

from ..core.model_api import ModelProvider
from .avatars import assign_avatars
from .invitees import SavedInvitee, guest_persona
from .models import DiscussionContext, DiscussionIssue, DiscussionSubject, DiscussionTurn, DiscussionView, StandaloneIssue
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

    async def start(
        self, issue: DiscussionSubject, *, guest: SavedInvitee | None,
        require_review: Callable[[], object] | None = None,
    ) -> DiscussionView:
        standalone = isinstance(issue, StandaloneIssue)
        generated_count = issue.participant_count - int(guest is not None) if standalone else 3
        designer_count = max(MIN_AGENTS, generated_count)
        goal = panel_goal(issue)
        with self.provider.scope(issue):
            try:
                proposal = await TeamDesigner().design(
                    goal, self.provider, self.model.model,
                    agents=designer_count,
                    # Moot's optional balance pass can shrink a user-sized panel.
                    balance_check=not standalone,
                )
            except (DesignError, ProviderError) as exc:
                raise HTTPException(502, "圆桌角色生成失败，请重试。") from exc
            if standalone and len(proposal.agents) < generated_count:
                raise HTTPException(502, "生成的讨论者人数不足，请重试。")
            if require_review is not None:
                require_review()
            context = DiscussionContext(
                issue=issue, mode=self.provider.provider.mode,
                rationale=proposal.rationale, balance_notes=proposal.balance_notes,
                invitee_name=guest[1].name if guest is not None else None,
            )
            moderator = AIModerator()
            agents = proposal.agents[:generated_count]
            if guest is not None:
                occupied_names = {agent.name.casefold() for agent in agents}
                occupied_names.add(moderator.name.casefold())
                agents.append(guest_persona(guest, occupied_names))
            config = SessionConfig(
                topic=issue.question, background=context.model_dump_json(),
                agents=agents, moderator=moderator, default_model=self.model, allow_alliances=False,
                round_plan=discussion_rounds(standalone=standalone),
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


def panel_goal(issue: DiscussionSubject) -> str:
    if isinstance(issue, StandaloneIssue):
        prompt = (
            "请围绕用户给定的议题组织圆桌。按议题配置有不同关注点的专业角色，"
            "讨论已知信息、合理分歧和可验证的下一步。以下 JSON 是议题。\n"
        )
        return prompt + json.dumps({"question": issue.question}, ensure_ascii=False)
    prompt = (
        "请为一项环保营销审核的证据争议组成一个圆桌讨论小组。"
        "以不同专业视角审视规则适用、证据缺口及可能的改写或补证。"
        "角色按本次争议生成，保留合理分歧。以下 JSON 是审核材料。\n"
    )
    return prompt + json.dumps({
        "sources": [{"id": source.source_id, "excerpt": source.excerpt[:120]} for source in issue.sources],
        "market": issue.market,
        "question": issue.question[:600],
        "claim": issue.risk.claim_quote[:300],
        "reason": issue.risk.reason[:220],
    }, ensure_ascii=False)


def discussion_rounds(*, standalone: bool):
    plan = brainstorm()
    opening, discussion, closing = plan.rounds
    discussion.turns_per_agent = 1
    if standalone:
        opening.instruction = "从你的角色出发说明对议题的初步看法，并交代所依据的信息。"
        discussion.instruction = "回应前序的一个具体观点，指出分歧、假设和可验证的办法。"
        closing.instruction = "说明你的最终建议和仍须验证的问题。"
    else:
        opening.instruction = "说明你对这条审核证据及其适用范围的初步解读。"
        discussion.instruction = "回应前序的一个具体观点，核对材料能支持什么，并指出缺口。"
        closing.instruction = "说明你的最终意见、仍有的分歧及建议的下一步复核动作。"
    return plan


def view(state: SessionState) -> DiscussionView:
    context = DiscussionContext.model_validate_json(state.config.background)
    reason = "error" if state.end_reason == "completed" and not state.report else state.end_reason
    allowed = {source.source_id for source in context.issue.sources}
    report = visible_citations(state.report, allowed) if state.report else None
    display_names = {}
    if context.issue.invitee is not None and context.invitee_name is not None:
        display_names[str(context.issue.invitee.member_id)] = context.invitee_name
    participants = [
        dict(
            agent.model_dump(mode="json", exclude={"model", "knowledge", "tools", "prompt_override"}),
            name=display_names.get(agent.id, agent.name),
        )
        for agent in state.config.agents
    ]
    turns = []
    for message in state.messages:
        if message.speaker_kind is SpeakerKind.SYSTEM:
            continue
        text = visible_citations(message.text, allowed)
        turns.append(DiscussionTurn(
            speaker_id=message.speaker_id,
            speaker_name=display_names.get(message.speaker_id, state.config.speaker_label(message.speaker_id)),
            speaker_kind=message.speaker_kind.value, round_index=message.round_index,
            text=text, source_ids=citation_ids(text),
        ))
    assert state.config.default_model is not None
    return DiscussionView(
        discussion_id=state.id, issue=context.issue, mode=context.mode, model=state.config.default_model.model,
        status=state.status.value, end_reason=reason, created_at=state.created_at,
        participants=participants,
        avatar_indices=assign_avatars(state.config.agents, state.id),
        panel_rationale=context.rationale, panel_balance_notes=context.balance_notes,
        rounds=[step.name for step in state.config.round_plan.rounds],
        turns=turns, report=report, report_source_ids=citation_ids(report or ""),
        error="会议未能形成完整纪要，已保存生成的发言。" if reason == "error" else None,
    )
