"""Project context snapshots and resumable multi-role deliberation."""
from fastapi import HTTPException

from ..core.llm import ModelError
from ..core.store import now
from ..models.workspace import (Meeting, MeetingConclusion, MeetingTurn, MeetingTurnContent,
                                Persona, ProjectContext)

ROLES = [
    {"role_id": "consumer", "name": "目标消费者代表", "focus": "从所选画像出发，解释理解、信任与购买顾虑；不冒充真实消费者调研。"},
    {"role_id": "brand", "name": "品牌方", "focus": "守住品牌表达与可核实的产品事实，说明品牌需要提供的证明。"},
    {"role_id": "legal", "name": "法务合规", "focus": "仅据冻结的规则来源讨论风险；区分缺少证明、风险与违法认定。"},
    {"role_id": "creative", "name": "创意策划", "focus": "提出明确可执行的表达方向，不虚构产品属性、认证或检测结果。"},
    {"role_id": "media", "name": "投放顾问", "focus": "结合渠道讨论信息呈现与验证步骤；未提供的平台政策不能冒充已核实规定。"},
    {"role_id": "localizer", "name": "本地化专家", "focus": "检查语言理解和市场语境，不将文化假设当成已证实事实。"},
]


def context_for(store, project_id):
    try:
        return store.get("project_context", project_id, ProjectContext)
    except HTTPException as error:
        if error.status_code != 404:
            raise
        return ProjectContext()


def audience_snapshot(store, project_id):
    context = context_for(store, project_id)
    return {"context": context.model_dump(), "personas": [store.get("persona", p, Persona).model_dump(mode="json")
                                                           for p in context.persona_ids]}


def upsert(store, kind, identifier, parent, value):
    with store.connection() as db:
        db.execute("INSERT INTO records VALUES (?, ?, ?, ?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload",
                   (kind, identifier, parent, value.model_dump_json()))


def recover_meetings(store):
    for meeting in store.list("meeting", Meeting):
        if meeting.status == "generating":
            meeting.status = "interrupted"
            meeting.error = "服务已重启，已完成发言保留，可继续当前步骤。"
            upsert(store, "meeting", meeting.meeting_id, meeting.project_id, meeting)


class RoundtableService:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider

    def advance(self, meeting_id, request):
        # Claim a step under a SQLite write lock before spending a model call.
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM records WHERE kind='meeting' AND id=?", (meeting_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "圆桌会议不存在。")
            meeting = Meeting.model_validate_json(row["payload"])
            index = len(meeting.turns)
            if request.expected_index < index or (meeting.status == "completed" and request.expected_index == index):
                return meeting
            if request.expected_index != index:
                raise HTTPException(409, "会议进度已变化，请刷新后继续。")
            if meeting.status == "generating":
                raise HTTPException(409, "当前角色正在发言，请稍候。")
            if (meeting.mode, meeting.model) != (self.provider.mode, self.provider.model):
                raise HTTPException(409, "请使用创建会议时的模型与模式继续。")
            meeting.status, meeting.error = "generating", None
            db.execute("UPDATE records SET payload=? WHERE kind='meeting' AND id=?", (meeting.model_dump_json(), meeting_id))
        try:
            if request.instruction.strip() and not any(n["before_turn"] == index and n["text"] == request.instruction.strip() for n in meeting.host_notes):
                meeting.host_notes.append({"before_turn": index, "text": request.instruction.strip()})
                upsert(self.store, "meeting", meeting_id, meeting.project_id, meeting)
            context = {"project": meeting.project_name, "channel": meeting.channel,
                       "market": meeting.market, "project_context": meeting.project_context.model_dump() if meeting.project_context else None,
                       "personas": [p.model_dump(mode="json") for p in meeting.personas],
                       "goal": meeting.goal, "issues": meeting.issue_ids,
                       "review": meeting.review_snapshot.model_dump(mode="json"),
                       "turns": [t.model_dump(mode="json") for t in meeting.turns], "host_notes": meeting.host_notes}
            if not meeting.include_market:
                # Keep rule jurisdiction as evidence, but omit optional project market context.
                context["review"].pop("market", None)
                context["review"].pop("audience_context", None)
                context["review"].pop("audience_fit", None)
            if not meeting.include_personas:
                context["review"].pop("audience_context", None)
                context["review"].pop("audience_fit", None)
            if index < 2 * len(meeting.roles):
                role = meeting.roles[index % len(meeting.roles)]
                if self.provider.mode == "demo":
                    output = MeetingTurnContent(viewpoint=f"预设讨论：围绕所选问题复核证据范围。{next(r['focus'] for r in ROLES if r['role_id'] == role)}",
                        proposal="先删除缺乏证明的绝对化表述，再核对原始产品材料；将修改稿重新送审。", vote="need_evidence",
                        source_ids=[s.source_id for s in meeting.review_snapshot.sources][:2])
                else:
                    output = self.provider.complete(step="roundtable_turn",
                        instruction=(f"你是{next(r['name'] for r in ROLES if r['role_id'] == role)}。"
                                     f"{next(r['focus'] for r in ROLES if r['role_id'] == role)}"
                                     "用中文回应前序观点并提出行动建议，只讨论选中 issues。画像是用户假设或派生假设。"
                                     "只能引用 review.sources 的 source_id；规则缺失必须说明，不得批准投放。"),
                        context={**context, "round": index // len(meeting.roles) + 1}, output=MeetingTurnContent)
                self.validate_sources(meeting, output.source_ids)
                meeting.turns.append(MeetingTurn(**output.model_dump(), role=role,
                                    round=index // len(meeting.roles) + 1, created_at=now()))
                meeting.status = "active"
            else:
                if self.provider.mode == "demo":
                    conclusion = MeetingConclusion(consensus=["预设共识：先补证或收窄宣称，再复审。"],
                        disagreements=["素材表现与信任提升效果尚未通过真实受众验证。"],
                        recommendations=["删除缺乏证明的整体环保承诺，保留可核实的普通产品介绍。"],
                        todos=["品牌方提供材料与认证原件。", "将修改文案提交复审。"],
                        risk_notes=["这是固定演示讨论，不构成法律意见或投放批准。"], revised_copy=None, source_ids=[])
                else:
                    conclusion = self.provider.complete(step="roundtable_conclusion",
                        instruction=("作为圆桌主持人，用中文整理真实发言中的共识、分歧、修改建议、待办和风险。"
                                     "不得虚构共识、证据或产品事实。可提供仅删除或收窄原文的修改稿，否则 revised_copy 为 null。"
                                     "只能引用 review.sources 内的 source_id；模拟讨论不构成批准。"),
                        context=context, output=MeetingConclusion)
                self.validate_sources(meeting, conclusion.source_ids)
                meeting.conclusion, meeting.status = conclusion, "completed"
            upsert(self.store, "meeting", meeting_id, meeting.project_id, meeting)
            return meeting
        except Exception as error:
            meeting.status = "interrupted"
            meeting.error = str(error) if isinstance(error, ModelError) else "本步生成失败，已保留此前发言，请重试。"
            upsert(self.store, "meeting", meeting_id, meeting.project_id, meeting)
            if isinstance(error, (ModelError, HTTPException)):
                raise
            raise ModelError(meeting.error) from None

    @staticmethod
    def validate_sources(meeting, identifiers):
        if set(identifiers) - {s.source_id for s in meeting.review_snapshot.sources}:
            raise ModelError("发言引用了冻结规则之外的来源，当前步骤未保存，请重试。")
