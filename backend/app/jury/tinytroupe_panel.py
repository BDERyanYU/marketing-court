"""Use the vendored TinyTroupe factory through the shared model connection."""

import json
from contextlib import contextmanager
from threading import Lock
from uuid import uuid4

from ..core.model_api import ModelError, ModelProvider
from .models import PanelSeat, TinyTroupePlan


SOURCE_COMMIT = "7ce8be378a37ee73f9745d6781452712318afa04"
_CLIENT_NAME = "marketing-court"
_FACTORY_LOCK = Lock()


class _SharedClient:
    def __init__(self, provider: ModelProvider, expected_plan_size: int | None):
        self.chat = getattr(provider, "chat", None)
        if self.chat is None:
            raise ModelError("The jury model must support TinyTroupe chat messages.")
        self.error: ModelError | None = None
        self.expected_plan_size = expected_plan_size
        self.dimension_names: set[str] = set()

    def send_message(self, messages, *, response_format=None, temperature=None, **_kwargs):
        if self.error is not None:
            raise self.error
        try:
            reply = self.chat(
                messages,
                temperature=0.3 if temperature is None else temperature,
                max_tokens=8192 if response_format is not None else 400,
                json_mode=response_format is not None,
            )
            if response_format is not None:
                try:
                    data = json.loads(reply["content"])
                    # Pass literal Unicode to the original parser, which mishandles \u escapes.
                    reply = {**reply, "content": json.dumps(data, ensure_ascii=False, allow_nan=False)}
                except ValueError:
                    raise ModelError("TinyTroupe 模型未返回有效 JSON。") from None
                if self.expected_plan_size is not None and isinstance(data, dict):
                    if "sample_plan" in data:
                        self._check_quotas(data["sample_plan"])
                        self.expected_plan_size = None
                    elif "dimensions" in data:
                        self._check_dimensions(data["dimensions"])
            return reply
        except ModelError as error:
            self.error = error
            raise

    def _check_dimensions(self, dimensions):
        if not isinstance(dimensions, list) or not dimensions:
            raise ModelError("TinyTroupe 未返回可用的抽样维度。")
        names = [item.get("name") if isinstance(item, dict) else None for item in dimensions]
        if any(not isinstance(name, str) or not name.strip() for name in names) or len(set(names)) != len(names):
            raise ModelError("TinyTroupe 返回了缺少名称或重名的抽样维度。")
        self.dimension_names = set(names)

    def _check_quotas(self, plan):
        # Validate before the original factory expands the quotas and names each seat.
        if not isinstance(plan, list) or not plan:
            raise ModelError("TinyTroupe 未返回有效的联合抽样计划。")
        total = 0
        ids = set()
        for group in plan:
            if not isinstance(group, dict) or not isinstance(group.get("sampled_values"), dict):
                raise ModelError("TinyTroupe 的抽样计划缺少有效的组合。")
            if self.dimension_names and group["sampled_values"].keys() != self.dimension_names:
                raise ModelError("TinyTroupe 的抽样组合与已规划的维度不一致。")
            directive_id = group.get("id")
            if type(directive_id) is not int or directive_id in ids:
                raise ModelError("TinyTroupe 的抽样计划包含无效或重复的组合编号。")
            ids.add(directive_id)
            quantity = group.get("quantity", 1)
            if type(quantity) is not int or quantity < 1:
                raise ModelError("TinyTroupe 的抽样计划包含无效的席位数。")
            total += quantity
        if total != self.expected_plan_size:
            raise ModelError("TinyTroupe 的抽样计划席位数与请求人数不一致。请重试。")


@contextmanager
def _native_factory(provider: ModelProvider, **options):
    from tinytroupe import config_manager
    from tinytroupe.agent import TinyPerson
    from tinytroupe.clients import force_api_type, register_client
    from tinytroupe.factory import TinyPersonFactory
    from tinytroupe.factory.tiny_factory import TinyFactory

    # Upstream keeps process-wide client, factory and name registries.
    with _FACTORY_LOCK:
        config_manager.update("loglevel_file", "NONE")
        config_manager.update("loglevel_console", "WARNING")
        client = _SharedClient(provider, options.get("total_population_size"))
        used_agent_names = set(TinyPerson.all_agents)
        used_factory_names = set(TinyFactory.all_factories)
        precomputed_names = TinyPersonFactory.all_unique_names.copy()
        register_client(_CLIENT_NAME, client)
        force_api_type(_CLIENT_NAME)
        try:
            yield TinyPersonFactory(**options)
            if client.error is not None:
                raise client.error
        except ModelError:
            raise
        except (AssertionError, AttributeError, KeyError, RuntimeError, TypeError, UnboundLocalError, ValueError):
            if client.error is not None:
                raise client.error from None
            raise ModelError("TinyTroupe 返回了不完整的抽样计划或角色。请重试。") from None
        finally:
            force_api_type(None)
            register_client(_CLIENT_NAME, None)
            for name in set(TinyPerson.all_agents) - used_agent_names:
                TinyPerson.all_agents.pop(name, None)
            for name in set(TinyFactory.all_factories) - used_factory_names:
                TinyFactory.all_factories.pop(name, None)
            TinyPersonFactory.all_unique_names = precomputed_names


def _seat(person, sampled_values: dict) -> PanelSeat:
    return PanelSeat(
        member_id=uuid4(),
        sampled_values=sampled_values,
        specification=person.to_json(include=["_persona"], serialization_type_field_name="type"),
    )


def derive_tinytroupe_panel(
    provider: ModelProvider,
    description: str,
    member_count: int,
    *,
    explicit_samples: list[dict[str, str]] | None = None,
) -> tuple[list[PanelSeat], TinyTroupePlan | None]:
    if explicit_samples is not None:
        with _native_factory(provider, context=description) as factory:
            seats = []
            for sample in explicit_samples:
                person = factory.generate_person(
                    agent_particularities="沿用以下固定抽样条件。\n" + json.dumps(sample, ensure_ascii=False),
                    attempts=1,
                )
                if person is None:
                    raise ModelError("TinyTroupe 未能根据指定组合生成角色。")
                seats.append(_seat(person, sample))
            return seats, None

    with _native_factory(
        provider,
        sampling_space_description=description,
        total_population_size=member_count,
        enforce_usage_of_all_dimensions=True,
        context=description,
    ) as factory:
        factory.initialize_sampling_plan()
        samples = factory.remaining_characteristics_sample
        if len(samples) != member_count:
            raise ModelError("TinyTroupe 的抽样计划席位数与请求人数不一致。请重试。")
        # Sequential generation consumes the original factory's sample stack from the end.
        selections = [{key: value for key, value in sample.items() if key != "name"} for sample in reversed(samples)]
        people = factory.generate_people(number_of_people=member_count, parallelize=False, attempts=1)
        if len(people) != member_count:
            raise ModelError("TinyTroupe 生成的角色数量不足。请重试。")
        return [_seat(person, values) for person, values in zip(people, selections, strict=True)], TinyTroupePlan(
            source_commit=SOURCE_COMMIT,
            sampling_space=factory.sampling_dimensions,
            sample_plan=factory.sampling_plan,
        )
