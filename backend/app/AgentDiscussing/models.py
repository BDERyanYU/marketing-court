from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import JsonValue, StringConstraints

from ..models.common import StrictModel
from ..models.review import PolicySource, RiskItem


class InviteeReference(StrictModel):
    panel_id: UUID
    member_id: UUID


class InviteeOption(StrictModel):
    member_id: UUID
    name: str


class InviteePanel(StrictModel):
    panel_id: UUID
    report_name: str | None
    base_persona_name: str | None
    members: list[InviteeOption]


class DiscussionRequest(StrictModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    invitee: InviteeReference | None = None


class DiscussionIssue(DiscussionRequest):
    review_id: str
    project_id: str
    asset_version_id: str
    market: str
    rule_pack_version: str
    risk: RiskItem
    sources: list[PolicySource]


class DiscussionContext(StrictModel):
    issue: DiscussionIssue
    mode: Literal["demo", "live"]
    rationale: str
    balance_notes: list[str]


class DiscussionTurn(StrictModel):
    speaker_id: str
    speaker_name: str
    speaker_kind: str
    round_index: int | None
    text: str
    source_ids: list[str]


class DiscussionView(StrictModel):
    discussion_id: str
    engine: Literal["moot"] = "moot"
    issue: DiscussionIssue
    mode: Literal["demo", "live"]
    model: str
    status: Literal["setup", "running", "paused", "finished"]
    end_reason: Literal["completed", "stopped", "error"] | None
    participants: list[dict[str, JsonValue]]
    avatar_indices: dict[str, int]
    panel_rationale: str
    panel_balance_notes: list[str]
    rounds: list[str]
    turns: list[DiscussionTurn]
    report: str | None
    report_source_ids: list[str]
    error: str | None
    created_at: datetime
