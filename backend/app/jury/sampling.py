from itertools import product
from random import Random
from .models import SamplingRequest, SamplingSpace


class SamplingError(ValueError):
    """The requested number of distinct combinations exceeds the sampling space."""


def sample_values(space: SamplingSpace, settings: SamplingRequest, member_count: int) -> list[dict[str, str]]:
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

    rng.shuffle(combinations)
    return combinations
