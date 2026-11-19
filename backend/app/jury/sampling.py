from itertools import product
from random import Random
from uuid import uuid4

from .models import Member, SamplingRequest, SamplingSpace
from .vendor.tinytroupe_sampling import SamplingDirective, flatten_sampling_plan


class SamplingError(ValueError):
    """The requested number of distinct combinations exceeds the sampling space."""


def sample_members(
    space: SamplingSpace, settings: SamplingRequest, member_count: int, theory_ids: list[str],
) -> list[Member]:
    names = [dimension.name for dimension in space.dimensions]
    combinations = [
        dict(zip(names, values, strict=True))
        for values in product(*(dimension.values for dimension in space.dimensions))
    ]
    rng = Random(settings.seed)
    if settings.mode == "random":
        if member_count > len(combinations):
            raise SamplingError(f"当前维度只有 {len(combinations)} 个不同组合，请调低随机抽样人数。")
        combinations = rng.sample(combinations, member_count)

    plan: list[SamplingDirective] = [
        {"sampled_values": values, "quantity": 1} for values in combinations
    ]
    return [
        member_from_sample(space, values, theory_ids)
        for values in flatten_sampling_plan(plan, rng)
    ]


def member_from_sample(space: SamplingSpace, values: dict[str, str], theory_ids: list[str]) -> Member:
    conditions = [f"{name}为{value}" for name, value in values.items()]
    exposure = [
        f"{dimension.name}为{values[dimension.name]}"
        for dimension in space.dimensions if dimension.kind == "exposure"
    ]
    return Member(
        member_id=uuid4(),
        name=" · ".join(values.values()),
        situation="、".join(exposure) or "按基础画像理解接触情境。",
        persona_prompt="沿用基础画像，并采用这些新增条件。" + "、".join(conditions) + "。",
        assumptions=conditions,
        theory_ids=theory_ids,
        sampled_values=values,
    )
