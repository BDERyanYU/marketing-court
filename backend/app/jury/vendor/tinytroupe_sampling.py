"""Sampling-plan expansion adapted from Microsoft TinyTroupe.

Source: microsoft/TinyTroupe@7ce8be378a37ee73f9745d6781452712318afa04,
tinytroupe/factory/tiny_person_factory.py::_flatten_sampling_plan.
Copyright (c) Microsoft Corporation. See LICENSE-TinyTroupe in this directory.

This adaptation removes the factory and cache dependencies and takes a
caller-provided random generator.
"""

import copy
import logging
from random import Random
from typing import NotRequired, TypedDict


logger = logging.getLogger(__name__)


class SamplingDirective(TypedDict):
    sampled_values: dict[str, str]
    quantity: NotRequired[int]


def flatten_sampling_plan(sampling_plan: list[SamplingDirective], rng: Random) -> list[dict[str, str]]:
    samples = []
    for sample in sampling_plan:
        if "quantity" not in sample:
            logger.warning(
                f"Sample in sampling plan does not have a 'quantity' field: {sample}. Assuming 1."
            )
            qty = 1
        else:
            qty = int(sample["quantity"])

        for _ in range(qty):
            # Copy each sample so individual member fields can be changed independently.
            cc_sample = copy.deepcopy(sample["sampled_values"])
            samples.append(cc_sample)

    rng.shuffle(samples)
    return samples
