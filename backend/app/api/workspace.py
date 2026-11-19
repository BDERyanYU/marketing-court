"""Project-oriented workspace, persona versions and deliberation endpoints."""
import hashlib

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..core.store import new_id, now
from ..models.review import AssetVersion, Project, Review, Task
from ..models.workspace import (AdvanceMeeting, DerivePersona, Meeting, MeetingRequest, Persona,
                                PersonaInput, ProjectContext, RecheckRequest, ReportAddendum, ReviewDecision)
from ..services.retrieval import RULE_VERSION, retrieve
from ..services.workspace import ROLES, RoundtableService, audience_snapshot, context_for, upsert


def _has_decision(store, review_id):
    with store.connection() as db:
        return db.execute("SELECT 1 FROM records WHERE kind='review_decision' AND id=?", (review_id,)).fetchone() is not None


def build_workspace_router(store, workflow):
    router = APIRouter(prefix="/api/workspace", tags=["Project workspace"])
    service = RoundtableService(store, workflow.provider)

    def detail(project_id):
        project = store.get("project", project_id, Project)
        context = context_for(store, project_id)
        reviews = store.list("review", Review, project_id)
        assets = store.list("asset", AssetVersion, project_id)
        meetings = store.list("meeting", Meeting, project_id)
        with store.connection() as db:
            tasks = [Task.model_validate_json(row["payload"]) for row in db.execute("SELECT payload FROM review_tasks ORDER BY rowid DESC").fetchall()]
        asset_ids = {a.asset_version_id for a in assets}
        tasks = [t for t in tasks if (t.kind == "review" and t.resource_id in asset_ids) or
                 (t.kind == "rewrite" and t.resource_id.split('/')[0] in {r.review_id for r in reviews})]
        state = ("archived" if context.archived else
                 "reviewing" if any(t.status in ("running", "queued") for t in tasks) else
                 "roundtable" if any(m.status != "completed" for m in meetings) else
                 "concluded" if meetings and meetings[0].status == "completed" and
                 (not reviews or reviews[0].created_at <= meetings[0].created_at) else
                 "decision" if reviews else "draft")
        return {"project": project, "context": context, "status": state, "reviews": reviews,
                "assets": assets, "meetings": meetings, "tasks": tasks,
                "personas": audience_snapshot(store, project_id)["personas"],
                "addenda": store.list("report_addendum", ReportAddendum, project_id),
                "decisions": {r.review_id: store.get("review_decision", r.review_id, ReviewDecision).trigger
                              for r in reviews if _has_decision(store, r.review_id)}}

    @router.get("/projects")
    def projects():
        return [{"project": p, "status": (d := detail(p.project_id))["status"],
                 "review_count": len(d["reviews"]), "meeting_count": len(d["meetings"])}
                for p in store.list("project", Project)]

    @router.get("/projects/{project_id}")
    def project_detail(project_id: str):
        return detail(project_id)

    @router.put("/projects/{project_id}/context", response_model=ProjectContext)
    def update_context(project_id: str, request: ProjectContext):
        store.get("project", project_id, Project)
        if len(request.persona_ids) != len(set(request.persona_ids)):
            raise HTTPException(422, "请勿重复选择画像。")
        for identifier in request.persona_ids:
            store.get("persona", identifier, Persona)
        upsert(store, "project_context", project_id, project_id, request)
        return request

    @router.post("/reviews/{review_id}/decision")
    def decision(review_id: str, request: ReviewDecision):
        review = store.get("review", review_id, Review)
        upsert(store, "review_decision", review_id, review.project_id, request)
        return request

    @router.get("/personas", response_model=list[Persona])
    def personas():
        return store.list("persona", Persona)

    @router.post("/personas", response_model=Persona, status_code=201)
    def create_persona(request: PersonaInput):
        identifier = new_id("persona")
        persona = Persona(**request.model_dump(), persona_id=identifier, family_id=identifier, version=1,
                          provenance="user_supplied", created_at=now())
        store.add("persona", identifier, identifier, persona)
        return persona

    @router.post("/personas/{persona_id}/versions", response_model=Persona, status_code=201)
    def edit_persona(persona_id: str, request: PersonaInput):
        original = store.get("persona", persona_id, Persona)
        with store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            versions = [Persona.model_validate_json(r["payload"]) for r in db.execute(
                "SELECT payload FROM records WHERE kind='persona' AND parent=?", (original.family_id,)).fetchall()]
            persona = Persona(**request.model_dump(), persona_id=new_id("persona"), family_id=original.family_id,
                              version=max(p.version for p in versions) + 1, parent_id=persona_id,
                              provenance="user_supplied", created_at=now())
            store.write(db, "persona", persona.persona_id, persona.family_id, persona)
        return persona

    @router.post("/personas/derive/from-review", response_model=Persona, status_code=201)
    def derive_persona(request: DerivePersona):
        project = store.get("project", request.project_id, Project)
        review = store.get("review", request.review_id, Review)
        if review.project_id != request.project_id:
            raise HTTPException(422, "审核记录不属于所选项目。")
        if workflow.provider.mode == "demo":
            draft = PersonaInput(name="关注环保表述的消费者（演示假设）", market=project.market,
                summary="从环保广告主题派生的假设受众；真实人口属性、规模与购买行为均未知。",
                needs=["清楚理解产品的环保范围", "能查证的产品说明"], concerns=["笼统环保承诺缺少证据"])
        else:
            draft = workflow.provider.complete(step="persona_derivation",
                instruction=("根据素材派生一个可供验证的目标受众假设，用中文。不要虚构研究数据或人口统计事实。"
                             "明确哪些偏好只是从文案推断，未知项保持未知。market 必须与输入一致。"),
                context={"original_text": review.original_text, "market": project.market,
                         "product_category": project.product_category}, output=PersonaInput)
            draft.market = project.market
        identifier = new_id("persona")
        persona = Persona(**draft.model_dump(), persona_id=identifier, family_id=identifier, version=1,
            provenance="inferred_from_material", source_project_id=project.project_id,
            source_review_id=review.review_id, created_at=now())
        store.add("persona", identifier, identifier, persona)
        return persona

    @router.get("/roles")
    def roles():
        return {"roles": ROLES, "rule_version": RULE_VERSION, "sources": retrieve("GB", "environmental")}

    @router.get("/meetings", response_model=list[Meeting])
    def meetings():
        return store.list("meeting", Meeting)

    @router.post("/projects/{project_id}/meetings", response_model=Meeting, status_code=201)
    def create_meeting(project_id: str, request: MeetingRequest):
        project = store.get("project", project_id, Project)
        review = store.get("review", request.review_id, Review)
        if review.project_id != project_id:
            raise HTTPException(422, "审核结果不属于该项目。")
        valid = {r.risk_id for r in review.risks} | {c.claim_id for c in review.claims} | {f"report:{review.review_id}"}
        if not set(request.issue_ids) <= valid or len(set(request.issue_ids)) != len(request.issue_ids):
            raise HTTPException(422, "议题必须引用该审核报告的风险或宣称，且不能重复。")
        if len(set(request.roles)) != len(request.roles):
            raise HTTPException(422, "请勿重复选择角色。")
        context = context_for(store, project_id)
        # A meeting freezes current project choices; the review retains its earlier audit context.
        snapshot = audience_snapshot(store, project_id)
        selected_personas = [Persona.model_validate(p) for p in snapshot.get("personas", [])] if request.include_personas else []
        meeting = Meeting(**request.model_dump(), meeting_id=new_id("meeting"), project_id=project_id,
            project_name=project.name, channel=project.channel, market=project.market if request.include_market else None,
            personas=selected_personas,
            project_context=ProjectContext.model_validate(snapshot.get("context", context.model_dump())) if request.include_market else None,
            review_snapshot=review, mode=workflow.provider.mode, model=workflow.provider.model, created_at=now())
        if meeting.project_context and not request.include_personas:
            meeting.project_context.persona_ids = []
        store.add("meeting", meeting.meeting_id, project_id, meeting)
        if context.archived:
            context.archived = False
            upsert(store, "project_context", project_id, project_id, context)
        upsert(store, "review_decision", review.review_id, project_id, ReviewDecision(trigger=request.trigger))
        return meeting

    @router.get("/meetings/{meeting_id}", response_model=Meeting)
    def meeting(meeting_id: str):
        return store.get("meeting", meeting_id, Meeting)

    @router.post("/meetings/{meeting_id}/advance", response_model=Meeting)
    def advance(meeting_id: str, request: AdvanceMeeting):
        return service.advance(meeting_id, request)

    @router.post("/meetings/{meeting_id}/writeback", response_model=ReportAddendum)
    def writeback(meeting_id: str):
        with store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM records WHERE kind='meeting' AND id=?", (meeting_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "会议不存在。")
            meeting = Meeting.model_validate_json(row["payload"])
            if meeting.status != "completed" or not meeting.conclusion:
                raise HTTPException(409, "会议形成结论后才能回写。")
            identifier = "addendum-" + meeting_id
            prior = db.execute("SELECT payload FROM records WHERE kind='report_addendum' AND id=?", (identifier,)).fetchone()
            if prior:
                return ReportAddendum.model_validate_json(prior["payload"])
            addendum = ReportAddendum(addendum_id=identifier, meeting_id=meeting_id, project_id=meeting.project_id,
                review_id=meeting.review_id, conclusion=meeting.conclusion, created_at=now())
            store.write(db, "report_addendum", identifier, meeting.project_id, addendum)
            meeting.written_back = True
            db.execute("UPDATE records SET payload=? WHERE kind='meeting' AND id=?", (meeting.model_dump_json(), meeting_id))
        return addendum

    @router.post("/meetings/{meeting_id}/recheck", response_model=Task, status_code=202,
                 response_model_exclude={"checkpoints"})
    def recheck(meeting_id: str, request: RecheckRequest, background: BackgroundTasks):
        meeting = store.get("meeting", meeting_id, Meeting)
        if meeting.status != "completed":
            raise HTTPException(409, "请先完成圆桌讨论。")
        if workflow.provider.mode != "live":
            raise HTTPException(409, "新修改稿需要实时模式复审。演示模式可回写结论或使用预设改写复核。")
        text = request.text.strip()
        if not text:
            raise HTTPException(422, "请输入修改后文案。")
        digest = hashlib.sha256(text.encode()).hexdigest()
        asset_id = "recheck-" + hashlib.sha256((meeting_id + digest).encode()).hexdigest()[:32]
        asset = AssetVersion(asset_version_id=asset_id, project_id=meeting.project_id, kind="text", text=text,
            language=context_for(store, meeting.project_id).language,
            origin_meeting_id=meeting_id, original_filename="圆桌修改稿", sha256=digest,
            width=0, height=0, image_url="", storage_name="", created_at=now())
        with store.connection() as db:
            db.execute("INSERT OR IGNORE INTO records VALUES (?, ?, ?, ?)", ("asset", asset_id, meeting.project_id, asset.model_dump_json()))
        task, fresh = store.start_task("review", asset_id, workflow.provider.mode, workflow.provider.model)
        if fresh:
            background.add_task(workflow.run, task.task_id)
        return task

    return router
