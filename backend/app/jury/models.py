from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, field_validator, model_validator

from ..core.model_api import RunMode


Brief = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
Detail = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Copy = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Vote = Literal["would_consider", "unsure", "would_pass"]
Variant = Literal["A", "B"]
Rating = Annotated[int, Field(ge=1, le=5, strict=True)]
DimensionLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Trait(StrictModel):
    attribute: Brief
    value: Detail
    status: Literal["grounded", "inferred", "unknown", "user_supplied"]
    source_quote: str | None = Field(default=None, min_length=1, max_length=900)


class PersonaDraft(StrictModel):
    name: Brief
    traits: list[Trait] = Field(min_length=1, max_length=8)


class ReportFindings(StrictModel):
    personas: list[PersonaDraft] = Field(max_length=6)


class Persona(PersonaDraft):
    persona_id: UUID


class Report(StrictModel):
    report_id: UUID
    filename: str
    mode: RunMode
    model: str
    personas: list[Persona]


class StoredReport(Report):
    source_text: str | None = None


class SamplingDimension(StrictModel):
    name: DimensionLabel
    kind: Literal["trait", "exposure"]
    values: list[DimensionLabel] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def validate_values(self):
        if len({value.casefold() for value in self.values}) != len(self.values):
            raise ValueError("Dimension values must be distinct.")
        return self


class SamplingSpace(StrictModel):
    dimensions: list[SamplingDimension] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_dimensions(self):
        if len({dimension.name.casefold() for dimension in self.dimensions}) != len(self.dimensions):
            raise ValueError("Dimension names must be distinct.")
        return self


class SamplingRequest(StrictModel):
    mode: Literal["random", "full"]
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)
    space: SamplingSpace | None = None


class TinyTroupePlan(StrictModel):
    source_commit: str
    sampling_space: dict[str, JsonValue]
    sample_plan: list[dict[str, JsonValue]]


class PanelRequest(StrictModel):
    report_id: UUID
    persona_id: UUID | None = None
    manual_persona: Detail | None = None
    member_count: int = Field(default=3, ge=1, strict=True)
    sampling: SamplingRequest | None = None

    @model_validator(mode="after")
    def validate_choice(self):
        if self.persona_id is not None and self.manual_persona is not None:
            raise ValueError("Choose at most one extracted or manually supplied persona.")
        return self


class TheoryReference(StrictModel):
    theory_id: str
    title: str
    source: str
    version: str


class LegacyMember(StrictModel):
    """Older saved panels retain the profile used for their original A/B reactions."""

    situation: Detail
    persona_prompt: Detail
    assumptions: list[Detail] = Field(min_length=1, max_length=5)
    member_id: UUID
    name: Brief
    theory_ids: list[Brief] = Field(min_length=1, max_length=3)
    sampled_values: dict[str, str] = Field(default_factory=dict)


class TinyPersonSpecification(StrictModel):
    type: Literal["TinyPerson"]
    persona: dict[str, JsonValue]

    @field_validator("persona")
    @classmethod
    def require_name(cls, value: dict) -> dict:
        name = value.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("TinyPerson must have a name.")
        return value


class PanelSeat(StrictModel):
    member_id: UUID
    specification: TinyPersonSpecification
    sampled_values: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def name(self) -> str:
        return str(self.specification.persona["name"])


class Panel(StrictModel):
    panel_id: UUID
    report_id: UUID
    mode: RunMode
    model: str
    base_persona: Persona | None
    theories: list[TheoryReference]
    members: list[PanelSeat | LegacyMember]
    sampling: SamplingRequest | None = None
    tinytroupe_plan: TinyTroupePlan | None = None


class Scores(StrictModel):
    clarity: Rating
    trust: Rating
    appeal: Rating
    purchase_interest: Rating


class Reaction(StrictModel):
    interpretation: Detail
    noticed: Detail
    possible_misreading: Detail | None
    evidence_needed: list[Detail] = Field(max_length=4)
    trust_reason: Detail
    uncertainty: Detail
    scores: Scores
    vote: Vote
    vote_reason: Detail


class ComparisonRequest(StrictModel):
    panel_id: UUID
    original_text: Copy
    revised_text: Copy


class AdvanceRequest(StrictModel):
    expected_index: int = Field(ge=0, strict=True)


class Exposure(StrictModel):
    member_id: UUID
    variant: Variant
    reaction: Reaction


class Comparison(ComparisonRequest):
    comparison_id: UUID
    mode: RunMode
    model: str
    exposures: list[Exposure] = Field(default_factory=list)


class Pair(StrictModel):
    member_id: UUID
    member_name: str
    original: Reaction
    revised: Reaction


class MetricChange(StrictModel):
    higher: int
    same: int
    lower: int


class ComparisonView(Comparison):
    next_index: int | None
    total_exposures: int
    pairs: list[Pair] = Field(default_factory=list)
    vote_counts: dict[Variant, dict[Vote, int]] | None = None
    metric_changes: dict[str, MetricChange] | None = None
    notice: str = "这些票数和分数来自模拟成员，只用于比较文案反应与发现待验证的假设。"
