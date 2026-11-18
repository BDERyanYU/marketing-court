"""Factory prompt excerpts from Microsoft TinyTroupe.

Source: microsoft/TinyTroupe@7ce8be378a37ee73f9745d6781452712318afa04,
tinytroupe/factory/tiny_person_factory.py and
tinytroupe/factory/prompts/generate_person.mustache.
Copyright (c) Microsoft Corporation. See LICENSE-TinyTroupe.

The original @llm decorator uses the two planning method docstrings as
system instructions. These excerpts keep the dimension and quota rules.
The person prompt keeps the context, particularities and generation rules.
"""

SOURCE_COMMIT = "7ce8be378a37ee73f9745d6781452712318afa04"

SAMPLING_DIMENSIONS = """+Given a sampling description, computes the dimensions of the sampling space (and output them formated as a valid JSON specification). The sampling space offers a way to sample from a population of people,
so each dimension contains values that could be an attribute of a **specific** person.
- you can be very creative with the dimensions and values provided that they are consistent with the sampling space description.
- values are **not** distributions, probabilities or other statistics, but rather concrete, specific, people attributes.

## On your input
- JSON: Do not use the JSON directly, but rather abstract the dimensions from it. Input JSONs can be obtained from various sources, and you should do your best to interpret them and produce a clean list of dimensions and their values, regardless of how complex the input JSON is. In particular, never use the JSON formatting itself as dimension names or values, but rather abstract the actual dimensions and values from them.

## On your output:
You output a JSON containing a list of dimensions.
"""

SAMPLE_PLAN = """+This function defines which and how many people to sample from the sampling space defined by the given dimensions.
Given a number N of people to sample, and the dimensions of the sampling space, computes a *sample plan* of N people from that space as a JSON object (rooted on the "sample_plan" key).

The *sample plan* to be generated is a list of M *sampling directives*. Each *sampling directive* **always** consists of:
- "id": a unique identifier for the *sampling directive*, just an incrementing integer starting from 1.
- "subpopulation_description": a short description of the sub-population that this *sampling directive* represents, based on the sampling space description and the sampled values.
- "sampled_values": a map from of dimensions from the sampling space to concrete values, value ranges or value options.
- "quantity": to how many elements with those values should be sampled in total (from 1 to max_quantity_per_sample_directive if specified).

Rules and principles:
- Each *sampling directive* is a **combination** of values from the sampling dimensions that represent a specific segment of the target population. Its richness and variety must reflect the desired sub-population.
- If `enforce_usage_of_all_dimensions` is True, then **all** dimensions must be represented in the sampled_values of **every** sampling directive, in order to ensure that **all** samples are complete and accurate points from the sampling space.
- If a context parameter is specified, you must use it to guide the sampling plan construction, so that the sampled population is consistent with it.
- All values chosen from the sampling dimensions must be copied IN FULL in the "sampled_values" map, so that the sampled values are concrete and specific.
- The sum of all quantities in the output **must** be equal to N, the number of people to sample in total.
"""

GENERATE_PERSON = """+# Agent Generator

Please generate a highly detailed agent specification based on a general context and the particularities of the agent (if any). The generated agent specification will be used in a simulation to realistically represent a real person. Therefore, it must include a wide range of nuanced details that are consistent with the provided context and agent particularities.

## General Context
Use the given base persona and selected marketing theories.

## Agent Particularities
Use the supplied sampled values. A concrete scalar value for a field must be preserved in the specification.

## Generation Rules
- If a general context is provided, you must ensure the generated agent has relevant details that will allow the a realistic simulation of a real person in that context. To do so, you should include nunanced details that could be relevant for the simulation in that context.
- There are many ways to instantiate the context and agent particularities into a specific concrete agent, so avoid common stereotypes and cliches. Instead, try to think deeply about the context and agent particularities, and how they would manifest in a real person, and thus create an authentic-looking agent.
"""
