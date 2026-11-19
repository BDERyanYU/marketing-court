"""Checkpointed review and bounded rewrite workflow."""

import logging
from pathlib import Path

from ..core.llm import ModelError
from ..core.store import Store, new_id, now
from ..court.demo import DEMO_INPUT
from ..models.review import (AssetVersion, ClaimExtraction, Project, Review, Rewrite,
                             RiskAssessment, RiskItem, TextAnchor)
from ..services.claims import map_claim
from ..services.retrieval import RULE_VERSION, retrieve
from ..services.rewrite import remove_claim

logger = logging.getLogger(__name__)


class ReviewWorkflow:
    def __init__(self, store: Store, provider, ocr, storage: Path):
        self.store, self.provider, self.ocr, self.storage = store, provider, ocr, storage

    def checkpoint(self, task, stage, **values):
        task.stage, task.status = stage, "running"
        if stage not in task.events:
            task.events.append(stage)
        task.checkpoints.update(values)
        self.store.save_task(task)

    def analyze(self, text, anchors, asset, project, task, prefix=""):
        def key(name):
            return prefix + name

        if len(text) > 8000:
            raise ModelError("识别文字超过演示版 8000 字符上限，请裁剪素材后重试。")
        cached = task.checkpoints.get(key("claims"))
        if cached is None:
            if self.provider.mode == "demo":
                if text not in (DEMO_INPUT.original_text, "Meet the Everyday Bottle."):
                    raise ModelError("固定演示模式只支持预设案例，请配置实时模式审核新素材。")
                payload = {"claims": ([{"claim_text": DEMO_INPUT.claim_quote, "claim_type": "environmental"}]
                                      if DEMO_INPUT.claim_quote in text else [])}
                extraction = ClaimExtraction.model_validate(payload)
            else:
                extraction = self.provider.complete(
                    step="claim_extraction",
                    instruction=("提取广告中的可审核宣称。claim_text 必须逐字复制 original_text 的连续片段，不得改写。"
                                 "环保相关标 environmental，其余为 other；不要为普通产品名称制造宣称。"),
                    context={"original_text": text, "market": project.market}, output=ClaimExtraction)
            if any(c.claim_text not in text for c in extraction.claims):
                raise ModelError("模型宣称未逐字对应原文，未保存审核结论，请重试。")
            claims = [map_claim(c, anchors) for c in extraction.claims]
            self.checkpoint(task, key("claims_extracted"), **{key("claims"): [c.model_dump() for c in claims]})
        else:
            from ..models.review import Claim
            claims = [Claim.model_validate(c) for c in cached]
        sources = retrieve(project.market, "environmental")
        self.checkpoint(task, key("retrieval_completed"))
        risks = []
        for claim in claims:
            applicable = retrieve(project.market, claim.claim_type)
            if not applicable:
                continue
            assessment_key = key("assessment:" + claim.claim_id)
            assessment = task.checkpoints.get(assessment_key)
            if assessment is None:
                if self.provider.mode == "demo":
                    assessment = RiskAssessment(assessment="requires_substantiation", severity="high",
                        reason=DEMO_INPUT.reason, source_ids=["G1", "G2"],
                        evidence_gaps=["与整只水杯环保宣称范围匹配的证明材料"])
                else:
                    assessment = self.provider.complete(step="risk_assessment",
                        instruction=("依据提供的 CMA 监管指引审核该环保宣称。产品证据未提供，不得认定事实已被推翻。"
                                     "必须引用 sources 内的 source_id。仅给风险复核意见，不能批准投放或断言违法。"),
                        context={"original_text": text, "claim": claim.model_dump(), "market": project.market,
                                 "sources": [s.model_dump() for s in applicable], "product_evidence_status": "not_supplied"},
                        output=RiskAssessment)
                allowed = {s.source_id for s in applicable}
                if set(assessment.source_ids) - allowed:
                    raise ModelError("审核引用了规则库中不存在的来源，结论已拒绝保存。")
                assessment = assessment.model_dump()
                self.checkpoint(task, key("risk_validated"), **{assessment_key: assessment})
            if assessment["assessment"] != "no_issue_identified":
                risks.append(RiskItem(**assessment, risk_id=new_id("risk"), claim_id=claim.claim_id,
                    claim_quote=claim.claim_text, anchor_ids=claim.anchor_ids, location_status=claim.location_status))
        return Review(review_id=new_id("review"), asset_version_id=asset.asset_version_id,
            project_id=project.project_id, mode=self.provider.mode, model=self.provider.model,
            original_text=text, anchors=anchors, claims=claims, risks=risks, sources=sources,
            rule_pack_version=RULE_VERSION, created_at=now(), limitations=[
                "仅覆盖英国普通消费品环保文字宣称；不覆盖视觉暗示、其他风险类别或平台专项政策。",
                "产品证明未提供；没有识别到本主题风险不代表素材已获准投放。",
                *( ["改写为文案版本，原始图片未被修改；定位沿用原图，仅作参考。"] if asset.kind == "copy" else []),
                *( ["含超出当前环保规则范围的宣称，需人工审核。"] if any(c.claim_type == "other" for c in claims) else []),
                *( ["固定案例演示，文字与坐标来自人工预设，不代表实时 OCR 或模型输出。"] if self.provider.mode == "demo" else []),
            ])

    def run(self, task_id: str):
        task = self.store.task(task_id)
        try:
            if task.kind == "rewrite":
                self.run_rewrite(task)
                return
            asset = self.store.get("asset", task.resource_id, AssetVersion)
            project = self.store.get("project", asset.project_id, Project)
            if self.provider.mode != "live":
                raise ModelError("新上传图片需要实时模式；固定演示请使用预设案例。")
            cached = task.checkpoints.get("anchors")
            if cached is None:
                self.checkpoint(task, "asset_parsing")
                anchors = self.ocr.extract(self.storage / asset.storage_name, asset.width, asset.height)
                self.checkpoint(task, "asset_parsed", anchors=[a.model_dump() for a in anchors])
            else:
                anchors = [TextAnchor.model_validate(a) for a in cached]
            text = "\n".join(a.text for a in anchors)
            review = self.analyze(text, anchors, asset, project, task)
            task.result_id = review.review_id
            self.store.finish(task, [("review", review.review_id, project.project_id, review)])
        except Exception as error:
            task.status = "failed"
            if isinstance(error, ModelError):
                task.error = str(error)
            else:
                task.error = "处理失败，已保留完成步骤，请检查服务状态后重试。"
                logger.error("Workflow failed: %s", type(error).__name__)
            self.store.save_task(task)

    def run_rewrite(self, task):
        original_review_id, risk_id = task.resource_id.split("/", 1)
        original = self.store.get("review", original_review_id, Review)
        risk = next(r for r in original.risks if r.risk_id == risk_id)
        source_asset = self.store.get("asset", original.asset_version_id, AssetVersion)
        project = self.store.get("project", original.project_id, Project)
        revised = remove_claim(original.original_text, risk.claim_quote)
        self.checkpoint(task, "rewrite_completed")
        asset = source_asset.model_copy(update={"asset_version_id": new_id("copy"), "kind": "copy",
            "text": revised, "parent_asset_version_id": source_asset.asset_version_id, "created_at": now()})
        reviewed = self.analyze(revised, original.anchors, asset, project, task, "recheck_")
        rewrite = Rewrite(rewrite_id=new_id("rewrite"), source_review_id=original.review_id,
            source_risk_id=risk_id, source_asset_version_id=source_asset.asset_version_id,
            asset_version_id=asset.asset_version_id, review_id=reviewed.review_id,
            original_text=original.original_text, revised_text=revised, removed_text=risk.claim_quote,
            reason="谨慎改写：删除选中的待补证宣称，保留其余原文，不增加产品事实；已完成一次自动复核。", created_at=now())
        task.result_id = rewrite.rewrite_id
        self.store.finish(task, [("asset", asset.asset_version_id, project.project_id, asset),
            ("review", reviewed.review_id, project.project_id, reviewed),
            ("rewrite", rewrite.rewrite_id, original.review_id, rewrite)])
