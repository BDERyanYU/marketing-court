"""Bounded, offline text examples from the supplied GreenLint v1.2 archive.

Only the three named samples are supported. Imported rules remain reference data;
they never extend the live review policy pack or establish a legal finding.
"""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from ..core.store import now
from ..models.court import CourtInput, PolicyCitation
from ..models.review import AssetVersion, Claim, DemoCaseInfo, DemoRule, Project, Review, RiskItem
from .retrieval import retrieve

DATA = Path(__file__).resolve().parents[1] / "data" / "examples"
VERSION = "greenlint-v1.2"
SENTENCES = re.compile(r"(?<=[.!?;])\s+|\n+|\s*[—–|•·]\s*")
EXCLUDES = {
    "green": ["greenhouse", "green tea", "green card", "green bean", "green light", "greenfield", "green belt",
              "colour: green", "color: green", "colour green", "color green", "colour : green", "color : green", "green colour", "green color"],
    "natural": ["natural flavor", "natural flavour", "natural gas"],
    "eco": ["economic", "economy", "economics", "ecosystem"],
}
CERTS = ("fsc", "grs", "gots", "oeko-tex", "bluesign", "cradle to cradle", "iso 14001", "iso 14021", "eu ecolabel", "roundtable", "rspo")
MATERIALS = ("recycled", "organic", "cotton", "polyester", "paper", "content", "material")


@lru_cache
def package():
    data = json.loads((DATA / "greenlint-v1.2.json").read_text(encoding="utf-8"))
    rules = (DATA / "greenlint-v1.2-rules.json").read_bytes()
    canonical = json.dumps(json.loads(rules), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != data["rules_sha256"]:
        raise ValueError("GreenLint reference rules hash mismatch")
    return data, json.loads(rules)


def case_data(case_id):
    return next((c for c in package()[0]["cases"] if c["case_id"] == case_id), None)


def case_info(case):
    return DemoCaseInfo(**{key: case[key] for key in DemoCaseInfo.model_fields if key != "provenance"},
        provenance=package()[0]["sample_source"])


def list_examples():
    return [case_info(c) for c in package()[0]["cases"]]


def split_sentences(text):
    result = []
    for part in (s.strip() for s in SENTENCES.split(text) if s.strip()):
        pieces = [s.strip() for s in part.split(",") if s.strip()]
        is_list = len(pieces) >= 3 and all(len(s) <= 45 for s in pieces) and "(" not in part and ")" not in part
        result.extend(pieces if is_list else [part])
    return result


def hit(term, text):
    return term in text and not any(ex in text for ex in EXCLUDES.get(term, []))


def evaluate(case, text, *, review_id=None, asset_id=None):
    """Reproduce the package's sentence/rule matches, without its AI or server code."""
    claims, risks = [], []
    namespace = review_id or f'greenlint-{case["case_id"]}'
    for index, sentence in enumerate(split_sentences(text)):
        low = sentence.lower()
        matched = []
        for rule in package()[1]:
            market = "UK" if case["market"] == "GB" else "EU"
            if rule["market"] not in (market, "Both"):
                continue
            context = rule.get("context_terms", [])
            if isinstance(context, str):
                context = [c.strip() for c in context.split(",") if c.strip()]
            if context and not any(hit(c, low) for c in context):
                continue
            if any(hit(t.lower(), low) for t in rule["triggers"]):
                matched.append(rule)
        fallback = not matched and any(hit(t, low) for t in ["environment", "planet", "eco", "green", "sustain"])
        if not matched and not fallback:
            continue
        claim_id = f'{namespace}-claim-{index}'
        claim = Claim(claim_id=claim_id, claim_text=sentence, claim_type="environmental",
                      anchor_ids=[], location_status="needs_confirmation")
        claims.append(claim)
        markers = any(c in low for c in CERTS) or (re.search(r"\d+\s*%", sentence) and any(m in low for m in MATERIALS))
        high = not markers and any(r["severity"] == "high" for r in matched)
        gaps = list(dict.fromkeys(r["evidence_needed"] for r in matched)) or ["检测报告、供应商声明或认证证书"]
        prefix = "文案中有数字或认证线索，但尚未核对凭证。" if markers else "未收到可核查的产品证明。"
        explanations = "；".join(dict.fromkeys(r["explanation_cn"] for r in matched))
        if case["case_id"] == "apple-watch":
            explanations = "Carbon Neutral 未说明碳核算范围、实际减排与抵消的关系，需补证确认；单凭该词不能推定基于抵消或认定违法。"
        else:
            explanations = "包内规则的关注点：" + (explanations or "环保相关表达需要证据支持。")
        risks.append(RiskItem(risk_id=f'{namespace}-risk-{index}',
            claim_id=claim_id, claim_quote=sentence, assessment="requires_substantiation",
            severity="high" if high else "medium", reason=prefix + explanations,
            source_ids=["G1", "G2"] if case["market"] == "GB" else [], evidence_gaps=gaps[:5],
            anchor_ids=[], location_status="needs_confirmation", demo_rule_ids=[r["id"] for r in matched] or ["LR-000"]))
    return Review(market=case["market"], product_category={"apple-watch": "electronics", "eco-dog-bed": "pet_supplies", "copier-paper": "office_supplies"}[case["case_id"]],
        review_id=review_id or f'greenlint-{case["case_id"]}-review',
        asset_version_id=asset_id or f'greenlint-{case["case_id"]}-asset',
        project_id=f'greenlint-{case["case_id"]}-project', mode="demo", model="greenlint-fixture-v1.2",
        original_text=text, anchors=[], claims=claims, risks=risks,
        sources=retrieve("GB", "environmental") if case["market"] == "GB" else [],
        rule_pack_version=VERSION, example=case_info(case),
        example_rules=[DemoRule(rule_id=r["id"], market=r["market"], citation=r["citation"], excerpt=r["quote_en"], explanation=r["explanation_cn"]) for r in package()[1] if any(r["id"] in risk.demo_rule_ids for risk in risks)],
        created_at=now(), limitations=[
            "导入预设文案案例；判定按 GreenLint v1.2 本地演示规则重现，不是实时 OCR 或模型审核。",
            "压缩包未包含广告原图、商品页链接或采集日期，文字定位不代表原图坐标。",
            "LR 编号仅用于说明包内规则匹配；包内 EU 条款不能直接作为英国法律依据，英国引用单独使用现有 CMA 指引。",
            "未核验产品、材料比例或认证真实性；负面案例是风险示例，不是对品牌的违法认定。",
            "正面案例仅表示在包内欧盟演示规则下未命中风险，不代表完整合规或投放批准。",
        ])


def install_example(store, case_id):
    case = case_data(case_id)
    if case is None:
        raise HTTPException(404, "预设案例不存在。")
    review = evaluate(case, case["original_text"])
    project = Project(project_id=review.project_id, name=case["title"], market=case["market"],
        product_category={"apple-watch": "electronics", "eco-dog-bed": "pet_supplies", "copier-paper": "office_supplies"}[case_id], created_at=now())
    asset = AssetVersion(asset_version_id=review.asset_version_id, project_id=project.project_id,
        kind="text", original_filename=case["title"], sha256=hashlib.sha256(review.original_text.encode()).hexdigest(),
        width=0, height=0, image_url="", storage_name="", text=review.original_text, created_at=now())
    with store.connection() as db:
        for kind, identifier, value in [("project", project.project_id, project), ("asset", asset.asset_version_id, asset), ("review", review.review_id, review)]:
            db.execute("INSERT OR IGNORE INTO records VALUES (?, ?, ?, ?)", (kind, identifier, project.project_id, value.model_dump_json()))
    return store.get("review", review.review_id, Review)


def scripted_input(risk_id):
    for case in package()[0]["cases"]:
        review = evaluate(case, case["original_text"])
        for risk in review.risks:
            if risk.risk_id == risk_id:
                return CourtInput(risk_id=risk_id, review_id=review.review_id, asset_version_id=review.asset_version_id,
                    original_text=review.original_text, claim_quote=risk.claim_quote, market=case["market"],
                    assessment=risk.assessment, reason=risk.reason, rule_pack_version=VERSION,
                    citations=[PolicyCitation(source_id=s.source_id, excerpt=s.excerpt, url=s.url) for s in review.sources if s.source_id in risk.source_ids],
                    product_evidence_status="not_supplied")
    return None
