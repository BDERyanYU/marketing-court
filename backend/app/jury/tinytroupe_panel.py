from random import Random
from uuid import uuid4

from ..core.model_api import ModelError, ModelProvider

from .models import Member, MemberProfile, SamplePlan, TinyTroupePlan, TinyTroupeSpace
from .vendor import tinytroupe_prompts as prompts
from .vendor.tinytroupe_sampling import flatten_sampling_plan


PANEL_SCOPE = (
    "保留用户确认的基础画像特征，使用取回的营销理论作为背景。只派生会影响广告理解、信任或购买考虑的"
    "特征和接触情境。新特征是模拟假设，避免推断敏感身份。使用简短中文。"
)


def derive_tinytroupe_panel(
    provider: ModelProvider, context: dict, member_count: int, theory_ids: list[str],
) -> tuple[list[Member], TinyTroupePlan]:
    space = provider.complete(
        step="jury_tinytroupe_dimensions",
        instruction=(
            f"{prompts.SAMPLING_DIMENSIONS}\n{PANEL_SCOPE}"
            "列出一到三个维度。每个维度包含 name、kind（trait 或 exposure）和两到三个不同的"
            "简短字符串 values。sampling_space_description 概述这些维度适用的客群和目的。"
        ),
        context=context,
        output=TinyTroupeSpace,
    )
    plan = provider.complete(
        step="jury_tinytroupe_plan",
        instruction=(
            f"{prompts.SAMPLE_PLAN}\n{PANEL_SCOPE}"
            "按 N 位成员设计有区分度的跨维度组合，每个维度取一个已有的完整字符串。"
            "quantity 是本次模拟的席位数，禁止推断现实市场的群体大小或百分比。"
        ),
        context={
            **context, "N": member_count, "enforce_usage_of_all_dimensions": True,
            "sampling_dimensions": space.model_dump(mode="json"),
        },
        output=SamplePlan,
    )
    options = {dimension.name: set(dimension.values) for dimension in space.dimensions}
    if sum(quota.quantity for quota in plan.sample_plan) != member_count:
        raise ModelError("TinyTroupe 联合抽样的席位总数与请求人数不符。")
    if len({quota.id for quota in plan.sample_plan}) != len(plan.sample_plan):
        raise ModelError("TinyTroupe 联合抽样计划含有重复的组合编号。")
    if any(
        quota.sampled_values.keys() != options.keys()
        or any(value not in options[name] for name, value in quota.sampled_values.items())
        for quota in plan.sample_plan
    ):
        raise ModelError("TinyTroupe 联合抽样计划缺少维度或使用了未定义的取值。")

    samples = flatten_sampling_plan(
        [{"sampled_values": quota.sampled_values, "quantity": quota.quantity} for quota in plan.sample_plan],
        Random(42),
    )
    members = []
    for index, values in enumerate(samples, start=1):
        spec = provider.complete(
            step="jury_tinytroupe_person",
            instruction=(
                f"{prompts.GENERATE_PERSON}\n{PANEL_SCOPE}"
                "依据固定组合独立生成人物规格。situation 是看到广告的场景。persona_prompt 描述"
                "该成员会留意什么、如何判断承诺和考虑购买，控制在 160 字内。"
                "新增细节写入 assumptions。不要预设对任何文案的好恶、评分或投票。"
            ),
            context={**context, "sampled_values": values, "member_index": index},
            output=MemberProfile,
        )
        members.append(Member(
            member_id=uuid4(), name=f"模拟成员 {index}", theory_ids=theory_ids,
            sampled_values=values, **spec.model_dump(),
        ))
    return members, TinyTroupePlan(
        source_commit=prompts.SOURCE_COMMIT, sampling_space=space, sample_plan=plan.sample_plan,
    )
