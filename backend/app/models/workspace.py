"""Versioned project context and review-linked roundtables."""
from datetime import datetime
from typing import Literal

from pydantic import Field

from .court import StrictModel
from .review import Market, Review

Role = Literal["consumer", "brand", "legal", "creative", "media", "localizer"]
Trigger = Literal["unsatisfied", "high_risk", "disputed"]


class PersonaInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=1600)
    market: Market = "GB"
    needs: list[str] = Field(default_factory=list, max_length=8)
    concerns: list[str] = Field(default_factory=list, max_length=8)


class Persona(PersonaInput):
    persona_id: str
    family_id: str
    version: int
    provenance: Literal["user_supplied", "inferred_from_material"]
    source_project_id: str | None = None
    source_review_id: str | None = None
    parent_id: str | None = None
    created_at: datetime


class ProjectContext(StrictModel):
    persona_ids: list[str] = Field(default_factory=list, max_length=6)
    language: str = Field(default="英语", max_length=80)
    brand_notes: str = Field(default="", max_length=1600)
    market_notes: str = Field(default="", max_length=1600)
    archived: bool = False


class ReviewDecision(StrictModel):
    trigger: Trigger


class MeetingRequest(StrictModel):
    review_id: str
    title: str = Field(min_length=1, max_length=140)
    issue_ids: list[str] = Field(min_length=1, max_length=20)
    roles: list[Role] = Field(min_length=2, max_length=6)
    trigger: Trigger
    goal: Literal["direction", "risk", "consensus", "copy"] = "direction"
    include_personas: bool = True
    include_market: bool = True


class MeetingTurnContent(StrictModel):
    viewpoint: str = Field(min_length=1, max_length=2000)
    proposal: str = Field(min_length=1, max_length=1600)
    vote: Literal["support", "revise", "disagree", "need_evidence"]
    source_ids: list[str] = Field(default_factory=list, max_length=8)


class MeetingTurn(MeetingTurnContent):
    role: Role
    round: int
    created_at: datetime


class MeetingConclusion(StrictModel):
    consensus: list[str] = Field(max_length=6)
    disagreements: list[str] = Field(max_length=6)
    recommendations: list[str] = Field(min_length=1, max_length=8)
    todos: list[str] = Field(max_length=8)
    risk_notes: list[str] = Field(max_length=6)
    revised_copy: str | None = Field(default=None, max_length=8000)
    source_ids: list[str] = Field(default_factory=list, max_length=8)


class Meeting(MeetingRequest):
    meeting_id: str
    project_id: str
    project_name: str
    channel: str
    market: Market | None
    personas: list[Persona]
    project_context: ProjectContext | None
    review_snapshot: Review
    mode: str
    model: str
    status: Literal["active", "generating", "interrupted", "completed"] = "active"
    turns: list[MeetingTurn] = Field(default_factory=list)
    host_notes: list[dict] = Field(default_factory=list)
    conclusion: MeetingConclusion | None = None
    written_back: bool = False
    error: str | None = None
    created_at: datetime


class AdvanceMeeting(StrictModel):
    expected_index: int = Field(ge=0, strict=True)
    instruction: str = Field(default="", max_length=1000)


class ReportAddendum(StrictModel):
    addendum_id: str
    meeting_id: str
    review_id: str
    project_id: str
    conclusion: MeetingConclusion
    created_at: datetime


class RecheckRequest(StrictModel):
    text: str = Field(min_length=1, max_length=8000)


class DerivePersona(StrictModel):
    project_id: str
    review_id: str


class AudienceFit(StrictModel):
    status: Literal["aligned", "mixed", "unknown"]
    reason: str = Field(min_length=1, max_length=1600)
    suggestions: list[str] = Field(max_length=5)
