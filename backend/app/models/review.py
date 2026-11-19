"""Typed contracts for the local review workflow."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from .court import Identifier, StrictModel


class ProjectRequest(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    market: Literal["GB"] = "GB"
    product_category: Literal["reusable_bottle"] = "reusable_bottle"
    channel: Literal["general_advertising"] = "general_advertising"


class Project(ProjectRequest):
    project_id: str
    created_at: datetime


class AssetVersion(StrictModel):
    asset_version_id: str
    project_id: str
    kind: Literal["image", "copy"] = "image"
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
    risk_id: str
    claim_id: str
    claim_quote: str
    category: Literal["substantiation_gap"] = "substantiation_gap"
    anchor_ids: list[str]
    location_status: Literal["located", "needs_confirmation"]
    workflow_status: Literal["open"] = "open"
    product_evidence_status: Literal["not_supplied"] = "not_supplied"


class Review(StrictModel):
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
