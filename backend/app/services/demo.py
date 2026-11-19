"""Explicitly labeled fixture imported through a separate endpoint."""

import shutil
from pathlib import Path

from ..core.store import now
from ..court.demo import DEMO_INPUT
from ..models.review import AssetVersion, Claim, Project, Review, RiskItem, TextAnchor
from .parsing import inspect_image
from .retrieval import RULE_VERSION, retrieve


def install_demo(store, storage: Path):
    existing = store.list("review", Review, "demo-project")
    if existing:
        return next(r for r in existing if r.review_id == DEMO_INPUT.review_id)
    project = Project(project_id="demo-project", name="Everyday Bottle · 英国环保案例", created_at=now())
    path = Path(__file__).resolve().parents[3] / "examples" / "eco-bottle.png"
    width, height, _, digest = inspect_image(path.read_bytes(), "image/png")
    storage.mkdir(parents=True, exist_ok=True)
    filename = "demo-eco-bottle.png"
    shutil.copyfile(path, storage / filename)
    asset = AssetVersion(asset_version_id=DEMO_INPUT.asset_version_id, project_id=project.project_id,
        original_filename=filename, storage_name=filename, sha256=digest, width=width, height=height,
        image_url=f"/api/assets/{DEMO_INPUT.asset_version_id}/image", created_at=now())
    anchors = [TextAnchor(anchor_id="demo-anchor-1", text="100% Eco-Friendly.",
                    polygon=[(.07,.16),(.74,.16),(.74,.23),(.07,.23)], score=1, method="fixture"),
               TextAnchor(anchor_id="demo-anchor-2", text="Meet the Everyday Bottle.",
                    polygon=[(.07,.24),(.53,.24),(.53,.29),(.07,.29)], score=1, method="fixture")]
    claim = Claim(claim_id="demo-claim-1", claim_text=DEMO_INPUT.claim_quote, claim_type="environmental",
                  anchor_ids=[anchors[0].anchor_id], location_status="located")
    risk = RiskItem(risk_id=DEMO_INPUT.risk_id, claim_id=claim.claim_id, claim_quote=claim.claim_text,
        assessment="requires_substantiation", severity="high", reason=DEMO_INPUT.reason,
        source_ids=["G1", "G2"], evidence_gaps=["与整体环保宣称范围匹配的证明材料"],
        anchor_ids=claim.anchor_ids, location_status="located")
    review = Review(review_id=DEMO_INPUT.review_id, project_id=project.project_id,
        asset_version_id=asset.asset_version_id, mode="demo", model="demo-fixture", original_text=DEMO_INPUT.original_text,
        anchors=anchors, claims=[claim], risks=[risk], sources=retrieve("GB", "environmental"),
        rule_pack_version=RULE_VERSION, created_at=now(), limitations=[
            "预设案例：文字、坐标与审核结论为人工准备；不是本次实时 OCR 或审核结果。",
            "仅演示英国环保宣称；产品证明未提供；审核与裁判不构成法律意见。"])
    with store.connection() as db:
        for kind, identifier, value in [("project", project.project_id, project), ("asset", asset.asset_version_id, asset),
                                         ("review", review.review_id, review)]:
            db.execute("INSERT OR IGNORE INTO records VALUES (?, ?, ?, ?)",
                       (kind, identifier, project.project_id, value.model_dump_json()))
    return review
