"""Isolated, blind consumer response boundary."""

from ..core.model_api import ModelProvider

from .models import Comparison, Exposure, Member, Panel, Persona, Reaction, Variant


REACT = (
    "你是营销模拟中的一位消费者。按照 base_persona 和 member 的用户特征及购买情境，"
    "只阅读这一次给定的 ad_copy，形成第一次反应。先用自己的话复述广告承诺，再说明注意到什么、"
    "可能的误读、需要核实的事实、信任原因和未知信息。没有可指出的误读时 possible_misreading 填 null。"
    "对清晰度、信任、吸引力、购买考虑分别按 1 至 5 整数评分，1 为最低，5 为最高。"
    "回答是否愿意进一步了解产品，以 would_consider、unsure、would_pass 三选一投票并给出理由。"
    "不猜测真实转化率，不假定文案承诺已得到证实。使用简短中文，返回 JSON。"
)


def next_exposure(
    provider: ModelProvider, panel: Panel, comparison: Comparison, index: int,
) -> Exposure:
    member, variant = exposure_at(panel, index)
    copy = comparison.original_text if variant == "A" else comparison.revised_text
    return Exposure(
        member_id=member.member_id,
        variant=variant,
        reaction=react(provider, panel.base_persona, member, copy),
    )


def exposure_at(panel: Panel, index: int) -> tuple[Member, Variant]:
    member_index, position = divmod(index, 2)
    variant: Variant = "A" if (member_index + position) % 2 == 0 else "B"
    return panel.members[member_index], variant


def pending_exposures(panel: Panel, comparison: Comparison) -> list[int]:
    saved = {(exposure.member_id, exposure.variant) for exposure in comparison.exposures}
    pending = []
    for index in range(2 * len(panel.members)):
        member, variant = exposure_at(panel, index)
        if (member.member_id, variant) not in saved:
            pending.append(index)
    return pending


def react(provider: ModelProvider, persona: Persona, member: Member, copy: str) -> Reaction:
    return provider.complete(
        step="jury_reaction",
        instruction=REACT,
        context={
            "base_persona": {
                "name": persona.name,
                "traits": [trait.model_dump(exclude={"source_quote"}) for trait in persona.traits],
            },
            "member": member.model_dump(exclude={"member_id", "theory_ids"}),
            "ad_copy": copy,
        },
        output=Reaction,
    )
