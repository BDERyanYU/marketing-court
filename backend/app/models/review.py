"""Typed contracts for the local review workflow."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from .court import Identifier, StrictModel


Market = Literal["GB", "EU", "US", "CA", "AU", "CN", "JP", "KR", "SG"]
ProductCategory = Literal["reusable_bottle", "household", "electronics", "clothing", "beauty",
                          "food", "pet_supplies", "office_supplies", "packaging", "other"]


class ProjectRequest(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    market: Market = "GB"
    product_category: ProductCategory = "reusable_bottle"
    channel: Literal["general_advertising", "meta", "google", "tiktok", "amazon", "website", "email"] = "general_advertising"


class Project(ProjectRequest):
    project_id: str
    created_at: datetime


class AssetVersion(StrictModel):
    language: str = "英语"
    origin_meeting_id: str | None = None
    asset_version_id: str
    project_id: str
    kind: Literal["image", "copy", "text"] = "image"
    original_filename: str
    sha256: str
    width: int
    height: int
    image_url: str
    storage_name: str
    text: str | None = None
    parent_asset_version_id: str | None = None
    created_at: datetime


class TextAnchor(StrictModel):
    anchor_id: str
    text: str
    polygon: list[tuple[float, float]] = Field(min_length=4, max_length=4)
    score: float = Field(ge=0, le=1)
    method: Literal["paddleocr", "fixture"]


class ExtractedClaim(StrictModel):
    claim_text: str = Field(min_length=1, max_length=1600)
    claim_type: Literal["environmental", "other"]


class ClaimExtraction(StrictModel):
    claims: list[ExtractedClaim] = Field(max_length=20)


class Claim(ExtractedClaim):
    input_origin: Literal["image", "text", "both"] = "image"
    claim_id: str
    anchor_ids: list[str]
    location_status: Literal["located", "needs_confirmation"]


class PolicySource(StrictModel):
    source_id: Identifier
    title: str
    issuer: str
    market: str
    product_scope: str
    platform: str | None = None
    source_kind: Literal["regulator_guidance"] = "regulator_guidance"
    published_on: str
    effective_from: str | None = None
    effective_to: str | None = None
    checked_at: str
    version: str
    excerpt: str
    url: str
    content_hash: str


class RiskAssessment(StrictModel):
    assessment: Literal["requires_substantiation", "insufficient_information", "no_issue_identified"]
    severity: Literal["high", "medium", "low"]
    reason: str = Field(min_length=1, max_length=1600)
    source_ids: list[Identifier] = Field(min_length=1, max_length=8)
    evidence_gaps: list[str] = Field(max_length=5)


class RiskItem(RiskAssessment):
    input_origin: Literal["image", "text", "both"] = "image"
    risk_id: str
    claim_id: str
    claim_quote: str
    category: Literal["substantiation_gap"] = "substantiation_gap"
    anchor_ids: list[str]
    location_status: Literal["located", "needs_confirmation"]
    workflow_status: Literal["open"] = "open"
    product_evidence_status: Literal["not_supplied"] = "not_supplied"
    demo_rule_ids: list[str] = Field(default_factory=list)


class DemoCaseInfo(StrictModel):
    case_id: str
    title: str
    market: Literal["GB", "EU"]
    category: str
    polarity: Literal["negative", "positive"]
    expected_risks: int
    description: str
    provenance: str


class DemoRule(StrictModel):
    rule_id: str
    market: str
    citation: str
    excerpt: str
    explanation: str


class Review(StrictModel):
    audience_context: dict = Field(default_factory=dict)
    audience_fit: dict | None = None
    image_text: str = ""
    supplied_text: str = ""
    market: Market = "GB"
    product_category: ProductCategory = "reusable_bottle"
    coverage_status: Literal["limited", "unsupported"] = "limited"
    review_id: str
    asset_version_id: str
    project_id: str
    mode: Literal["demo", "live"]
    model: str
    original_text: str
    anchors: list[TextAnchor]
    claims: list[Claim]
    risks: list[RiskItem]
    sources: list[PolicySource]
    rule_pack_version: str
    limitations: list[str]
    created_at: datetime
    example: DemoCaseInfo | None = None
    example_rules: list[DemoRule] = Field(default_factory=list)


class Task(StrictModel):
    task_id: str
    kind: Literal["review", "rewrite"]
    resource_id: str
    mode: Literal["demo", "live"]
    model: str
    status: Literal["queued", "running", "completed", "failed", "interrupted"]
    stage: str
    events: list[str] = Field(default_factory=list)
    error: str | None = None
    result_id: str | None = None
    checkpoints: dict = Field(default_factory=dict)
    created_at: datetime


class Rewrite(StrictModel):
    rewrite_id: str
    source_review_id: str
    source_risk_id: str
    source_asset_version_id: str
    asset_version_id: str
    review_id: str
    original_text: str
    revised_text: str
    removed_text: str
    reason: str
    created_at: datetime
