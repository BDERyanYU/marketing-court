"""Use the vendored TinyTroupe factory through the shared model connection."""

import json
import re
from contextlib import contextmanager
from threading import Lock
from uuid import uuid4

from ..core.model_api import ModelError, ModelProvider
from .models import PanelSeat, TinyTroupePlan


SOURCE_COMMIT = "7ce8be378a37ee73f9745d6781452712318afa04"
_CLIENT_NAME = "marketing-court"
_FACTORY_LOCK = Lock()
_FACTORY_INSTRUCTION = (
    "在本应用中，画像工厂只刻画看到广告前已有的消费者特征。"
    "保留与产品决策有关的抽样维度，从报告中提取依据，新增差异作为假设。"
    "待测文案的反应、版本偏好、评分、投票和购买结论不进入抽样维度、组合或人设。"
    "通用模板中的政治信念和族裔等细节须有报告依据且与产品相关，否则省略这些抽样维度。"
    "生成人设时沿用原版字段类型。"
)
_EXPOSURE_OUTCOME_AXIS = re.compile(
    r"(?:两版|各版|待测文案|A\s*[/／]\s*B|[AB]\s*版).*?(?:反应|偏好|倾向|投票|评分|选择)"
    r"|\b(?:a\s*/\s*b|(?:copy|ad)\s+variants?|variants?)[\s_-]+(?:reaction|preference|vote|rating|score)\b",
    re.IGNORECASE,
)


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
        messages = [
            {**message, "content": message["content"] + "\n\n" + _FACTORY_INSTRUCTION}
            if message.get("role") == "system" else message
            for message in messages
        ]
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
                    if self.expected_plan_size is not None and isinstance(data, dict):
                        if "sample_plan" in data:
                            self._check_quotas(data["sample_plan"])
                            self.expected_plan_size = None
                        elif "dimensions" in data:
                            self._check_dimensions(data["dimensions"])
                    # Pass literal Unicode to the original parser, which mishandles \u escapes.
                    reply = {**reply, "content": json.dumps(data, ensure_ascii=False, allow_nan=False)}
                except ValueError:
                    raise ModelError("TinyTroupe 模型未返回有效 JSON。") from None
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
        dimensions[:] = [dimension for dimension in dimensions if not _EXPOSURE_OUTCOME_AXIS.search(dimension["name"])]
        if not dimensions:
            raise ModelError("TinyTroupe 未返回接触文案前的画像维度。请重试。")
        self.dimension_names = {dimension["name"] for dimension in dimensions}

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
