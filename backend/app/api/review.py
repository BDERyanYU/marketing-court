"""Review routes. All business changes are performed on the server."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..core.store import new_id, now
from ..models.court import CourtInput, PolicyCitation
from ..models.review import AssetVersion, Project, ProjectRequest, Review, Rewrite, Task
from ..services.demo import install_demo
from ..services.greenlint import install_example, list_examples
from ..services.parsing import MAX_UPLOAD_BYTES, inspect_image


def build_review_router(store, workflow, courts, storage: Path):
    router = APIRouter(prefix="/api", tags=["Review"])

    @router.get("/projects", response_model=list[Project])
    def projects():
        return store.list("project", Project)

    @router.post("/projects", response_model=Project, status_code=201)
    def create_project(request: ProjectRequest):
        project = Project(**request.model_dump(), project_id=new_id("project"), created_at=now())
        store.add("project", project.project_id, project.project_id, project)
        return project

    @router.post("/projects/{project_id}/assets", response_model=AssetVersion, status_code=201)
    async def upload(project_id: str, file: UploadFile | None = None,
                     text: str = Form(default="", max_length=8000)):
        store.get("project", project_id, Project)
        text = text.strip()
        if file is None:
            if not text:
                raise HTTPException(422, "请添加广告图片或输入广告文案，至少提供一项。")
            asset_id = new_id("asset")
            asset = AssetVersion(asset_version_id=asset_id, project_id=project_id, kind="text",
                original_filename="广告文案", sha256=hashlib.sha256(text.encode()).hexdigest(),
                width=0, height=0, image_url="", storage_name="", text=text, created_at=now())
            store.add("asset", asset_id, project_id, asset)
            return asset
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        await file.close()
        width, height, suffix, digest = inspect_image(content, file.content_type)
        asset_id = new_id("asset")
        filename = asset_id + suffix
        storage.mkdir(parents=True, exist_ok=True)
        (storage / filename).write_bytes(content)
        asset = AssetVersion(asset_version_id=asset_id, project_id=project_id,
            original_filename=Path(file.filename or "upload").name[:200], sha256=digest, width=width,
            height=height, storage_name=filename, image_url=f"/api/assets/{asset_id}/image",
            text=text or None, created_at=now())
        store.add("asset", asset_id, project_id, asset)
        return asset

    @router.get("/assets/{asset_id}", response_model=AssetVersion)
    def asset(asset_id: str):
        return store.get("asset", asset_id, AssetVersion)

    @router.get("/assets/{asset_id}/image")
    def image(asset_id: str):
        item = store.get("asset", asset_id, AssetVersion)
        if item.kind == "text" or not item.storage_name:
            raise HTTPException(404, "此案例仅包含文案，没有原始图片。")
        path = storage / item.storage_name
        if not path.is_file():
            raise HTTPException(404, "原图文件缺失。")
        return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})

    @router.get("/projects/{project_id}/reviews", response_model=list[Review])
    def reviews(project_id: str):
        store.get("project", project_id, Project)
        return store.list("review", Review, project_id)

    @router.post("/assets/{asset_id}/reviews", response_model=Task, status_code=202,
                 response_model_exclude={"checkpoints"})
    def start_review(asset_id: str, background: BackgroundTasks):
        item = store.get("asset", asset_id, AssetVersion)
        if item.kind == "copy" or item.parent_asset_version_id:
            raise HTTPException(409, "文案版本通过改写复核流程生成。")
        if workflow.provider.mode != "live":
            raise HTTPException(409, "新素材需要实时模式，请先配置 DeepSeek；图片审核还需 OCR。也可打开预设案例。")
        task, fresh = store.start_task("review", asset_id, workflow.provider.mode, workflow.provider.model)
        if fresh:
            background.add_task(workflow.run, task.task_id)
        return task

    @router.get("/tasks/{task_id}", response_model=Task, response_model_exclude={"checkpoints"})
    def task(task_id: str):
        return store.task(task_id)

    @router.post("/tasks/{task_id}/retry", response_model=Task, status_code=202, response_model_exclude={"checkpoints"})
    def retry(task_id: str, background: BackgroundTasks):
        previous = store.task(task_id)
        fixed_example = previous.kind == "rewrite" and previous.model == "greenlint-fixture-v1.2"
        task = store.retry(task_id, previous.mode if fixed_example else workflow.provider.mode,
                           previous.model if fixed_example else workflow.provider.model)
        background.add_task(workflow.run, task.task_id)
        return task

    @router.get("/reviews/{review_id}", response_model=Review)
    def read_review(review_id: str):
        return store.get("review", review_id, Review)

    @router.post("/reviews/{review_id}/risks/{risk_id}/rewrite", response_model=Task, status_code=202,
                 response_model_exclude={"checkpoints"})
    def rewrite(review_id: str, risk_id: str, background: BackgroundTasks):
        review = store.get("review", review_id, Review)
        if not any(r.risk_id == risk_id for r in review.risks):
            raise HTTPException(404, "风险不属于此审核版本。")
        if review.example is None and (review.mode != workflow.provider.mode or review.model != workflow.provider.model):
            raise HTTPException(409, "请使用原审核的模式与模型进行改写复核；预设案例请在固定演示模式使用。")
        task, fresh = store.start_task("rewrite", review_id + "/" + risk_id,
                                      review.mode if review.example else workflow.provider.mode,
                                      review.model if review.example else workflow.provider.model)
        if fresh:
            background.add_task(workflow.run, task.task_id)
        return task

    @router.get("/rewrites/{rewrite_id}", response_model=Rewrite)
    def read_rewrite(rewrite_id: str):
        return store.get("rewrite", rewrite_id, Rewrite)

    @router.get("/reviews/{review_id}/rewrites", response_model=list[Rewrite])
    def rewrites(review_id: str):
        store.get("review", review_id, Review)
        return store.list("rewrite", Rewrite, review_id)

    @router.post("/demo", response_model=Review)
    def demo():
        return install_demo(store, storage)

    @router.get("/demo-cases")
    def demo_cases():
        return list_examples()

    @router.post("/demo-cases/{case_id}", response_model=Review)
    def open_demo_case(case_id: str):
        return install_example(store, case_id)

    @router.get("/reviews/{review_id}/report")
    def report(review_id: str):
        review = store.get("review", review_id, Review)
        asset = store.get("asset", review.asset_version_id, AssetVersion)
        project = store.get("project", review.project_id, Project)
        rewrites = store.list("rewrite", Rewrite, review_id)
        cases = [c.model_dump(mode="json") for c in courts.list_cases() if c.snapshot.review_id == review_id]
        payload = {"project": project.model_dump(mode="json"), "asset": asset.model_dump(mode="json"),
            "review": review.model_dump(mode="json"), "rewrites": [], "court_cases": cases,
            "human_approval": "not_requested", "disclaimer": "AI 辅助审核与非正式复核，不构成法律意见或投放批准。"}
        payload["asset"].pop("storage_name", None)
        for item in rewrites:
            payload["rewrites"].append({"rewrite": item.model_dump(mode="json"),
                "recheck": store.get("review", item.review_id, Review).model_dump(mode="json")})
        return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="{review_id}.json"'})

    return router


def snapshot_for_risk(store, risk_id: str) -> CourtInput:
    for review in store.list("review", Review):
        risk = next((r for r in review.risks if r.risk_id == risk_id), None)
        if risk is None:
            continue
        citations = [PolicyCitation(source_id=s.source_id, excerpt=s.excerpt, url=s.url)
                     for s in review.sources if s.source_id in risk.source_ids]
        return CourtInput(risk_id=risk_id, review_id=review.review_id, asset_version_id=review.asset_version_id,
            original_text=review.original_text, claim_quote=risk.claim_quote, market=store.get("project", review.project_id, Project).market, assessment=risk.assessment,
            reason=risk.reason, rule_pack_version=review.rule_pack_version, citations=citations,
            product_evidence_status="not_supplied")
    raise HTTPException(404, "未找到该风险的审核记录。")
