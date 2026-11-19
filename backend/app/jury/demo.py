from pathlib import Path
from typing import Any

from ..core.model_api import ModelError, Output, RunMode


REPORT = (Path(__file__).parent / "examples" / "bottle-research.txt").read_text(encoding="utf-8").strip()
ORIGINAL = "100% Eco-Friendly. Meet the Everyday Bottle."
REVISED = "Meet the Everyday Bottle."
PERSONA_NAME = "日常通勤补水者"
BOTTLE_DIMENSIONS = [
    {"name": "接触渠道", "kind": "exposure", "values": ["地铁灯箱", "商品详情页", "手机信息流"]},
    {"name": "证据关注度", "kind": "trait", "values": ["低", "中", "高"]},
]


class DemoProvider:
    mode: RunMode = "demo"
    model = "jury-demo-fixture"

    def complete(
        self, *, step: str, instruction: str, context: dict[str, Any], output: type[Output],
    ) -> Output:
        if step == "jury_personas":
            return output.model_validate({"personas": [{
                "name": PERSONA_NAME,
                "traits": [
                    {
                        "attribute": "购买目标", "value": "上下班路上方便补水", "status": "grounded",
                        "source_quote": "购买便携水杯主要是为了在上下班路上方便补水。",
                    },
                    {
                        "attribute": "关注点", "value": "防漏、重量、清洗和价格", "status": "grounded",
                        "source_quote": "多数受访者关注防漏、重量以及是否容易清洗，成交前会参考价格。",
                    },
                    {
                        "attribute": "信任线索", "value": "希望看到环保宣称的适用范围或材料依据", "status": "grounded",
                        "source_quote": "需要知道宣称适用于哪一部分以及是否有材料依据。",
                    },
                ],
            }]})
        if step == "jury_theory_selection":
            return output.model_validate({"theory_ids": ["jtbd", "elm"]})
        if step == "jury_dimensions":
            return output.model_validate({"dimensions": BOTTLE_DIMENSIONS})
        if step == "jury_tinytroupe_dimensions":
            return output.model_validate({
                "sampling_space_description": "日常通勤补水者看到便携水杯广告时的渠道和证据关注度。",
                "dimensions": BOTTLE_DIMENSIONS,
            })
        if step == "jury_tinytroupe_plan":
            return output.model_validate({"sample_plan": [
                {
                    "id": 1, "subpopulation_description": "通勤路上快速扫过广告",
                    "sampled_values": {"接触渠道": "地铁灯箱", "证据关注度": "低"},
                    "quantity": context["N"] - 1,
                },
                {
                    "id": 2, "subpopulation_description": "进入商品页后核对依据",
                    "sampled_values": {"接触渠道": "商品详情页", "证据关注度": "高"},
                    "quantity": 1,
                },
            ]})
        if step == "jury_tinytroupe_person":
            values = context["sampled_values"]
            situation = f"在{values['接触渠道']}看到便携水杯的广告。"
            priority = "先看卖点和产品用途。" if values["证据关注度"] == "低" else "先核对环保承诺的范围和依据。"
            return output.model_validate({
                "situation": situation,
                "persona_prompt": f"你是一名日常通勤补水者。{situation}{priority}",
                "assumptions": [situation, priority],
            })
        if step == "jury_reaction":
            member = context["member"]
            return output.model_validate(demo_reaction(member, context["ad_copy"]))
        raise ModelError("未知的演示步骤。")


def demo_reaction(member: dict, ad_copy: str) -> dict:
    revised = ad_copy == REVISED
    quick = member["name"] == "地铁上快速浏览" or member["sampled_values"].get("证据关注度") == "低"
    would_consider = (revised and not quick) or (quick and not revised)
    return {
        "interpretation": "这是一只日常用水杯。" if revised else "品牌说这只水杯很环保，也适合日常使用。",
        "noticed": "产品用途" if revised else "绝对化的环保口号",
        "possible_misreading": None if revised else "可能以为所有部件的环保表现都得到了验证。",
        "evidence_needed": ["重量和价格"] if revised else ["环保指的具体属性与适用范围"],
        "trust_reason": "描述较克制。" if revised else "看不到环保承诺的具体依据。",
        "uncertainty": "暂时不知道水杯是否防漏。",
        "scores": {
            "clarity": 4 if revised else 2,
            "trust": 4 if revised else 2,
            "appeal": (2 if revised else 4) if quick else (4 if revised else 3),
            "purchase_interest": 4 if would_consider else 2,
        },
        "vote": "would_consider" if would_consider else "unsure",
        "vote_reason": "有兴趣了解规格和价格。" if would_consider else "卖点还不足以让我继续了解。",
    }
