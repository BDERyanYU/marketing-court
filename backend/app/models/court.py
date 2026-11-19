from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, computed_field, model_validator


Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1600)]
RunMode = Literal["demo", "live"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyCitation(StrictModel):
    source_id: Identifier
    excerpt: ShortText
    url: HttpUrl


class CourtInput(StrictModel):
    risk_id: Identifier
    review_id: Identifier
    asset_version_id: Identifier
    original_text: str = Field(min_length=1, max_length=8000)
    claim_quote: str = Field(min_length=1, max_length=1600)
    market: str = Field(pattern=r"^[A-Z]{2}$", examples=["GB"])
    assessment: ShortText
    reason: ShortText
    rule_pack_version: Identifier
    citations: list[PolicyCitation] = Field(min_length=1, max_length=8)
    product_evidence_status: Literal["not_supplied"]

    @model_validator(mode="after")
    def validate_snapshot(self):
        if not self.claim_quote.strip() or self.claim_quote not in self.original_text:
            raise ValueError("claim_quote must occur verbatim in original_text")
        if len({item.source_id for item in self.citations}) != len(self.citations):
            raise ValueError("source_id must be unique within citations")
        return self


class CourtStep(StrEnum):
    PROSECUTION_1 = "prosecution_1"
    DEFENSE_1 = "defense_1"
    PROSECUTION_2 = "prosecution_2"
    DEFENSE_2 = "defense_2"
    JUDGMENT = "judgment"


COURT_STEPS = tuple(CourtStep)


class AdvanceRequest(StrictModel):
    expected_step: CourtStep


class TurnOutput(StrictModel):
    position: Literal["maintain", "challenge", "narrow", "concede", "withdraw", "request_evidence"]
    argument: ShortText
    source_ids: list[Identifier] = Field(max_length=8)
    responds_to: CourtStep | None
    evidence_requested: list[ShortText] = Field(max_length=4)


class DebateTurn(TurnOutput):
    step: CourtStep
    round: Literal[1, 2]
    role: Literal["prosecutor", "defense"]


class Judgment(StrictModel):
    disposition: Literal["upheld", "partially_revised", "recommend_revoke", "insufficient_evidence"]
    reason: ShortText
    source_ids: list[Identifier] = Field(min_length=1, max_length=8)
    evidence_requested: list[ShortText] = Field(max_length=4)


class CourtCase(StrictModel):
    case_id: UUID
    mode: RunMode
    model: str
    created_at: datetime
    snapshot: CourtInput
    next_step: CourtStep | None
    turns: list[DebateTurn] = Field(default_factory=list)
    judgment: Judgment | None = None

    @computed_field
    @property
    def status(self) -> Literal["open", "in_progress", "completed"]:
        if self.judgment is not None:
            return "completed"
        return "in_progress" if self.turns else "open"
