import json
from html import unescape
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
NATIVE_DIMENSIONS = [
    {"name": "通勤携带优先项", "values": ["防漏", "轻便"]},
    {"name": "清洁偏好", "values": ["易拆洗", "好冲洗"]},
]
MARKETING_DIMENSION = {"name": "环保证据核对重点", "values": ["宣称适用范围", "材料依据"]}


class DemoProvider:
    mode: RunMode = "demo"
    model = "jury-demo-fixture"
    _names = 0

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
        if step == "jury_dimensions":
            return output.model_validate({"dimensions": BOTTLE_DIMENSIONS})
        if step == "jury_reaction":
            member = context["member"]
            return output.model_validate(demo_reaction(member, context["ad_copy"]))
        raise ModelError("未知的演示步骤。")

    def chat(self, messages, *, json_mode: bool, **_kwargs) -> dict[str, str]:
        system = messages[0]["content"]
        user = messages[1]["content"]
        if "Given a sampling description" in system:
            description = _factory_arguments(user)["sampling_space_description"]
            dimensions = NATIVE_DIMENSIONS.copy()
            if "团队营销 Skill\n" in description:
                dimensions.append(MARKETING_DIMENSION)
            result = {"sampling_space_description": "便携水杯访谈里的购买关注点", "dimensions": dimensions}
        elif "This function defines which and how many people" in system:
            arguments = _factory_arguments(user)
            quantities = [1] if arguments["N"] == 1 else [arguments["N"] - 1, 1]
            result = {"sample_plan": [
                {
                    "id": index + 1,
                    "subpopulation_description": "水杯演示组合 " + str(index + 1),
                    "sampled_values": {
                        dimension["name"]: dimension["values"][index]
                        for dimension in arguments["sampling_dimensions"]["dimensions"]
                    },
                    "quantity": quantity,
                }
                for index, quantity in enumerate(quantities)
            ]}
        elif "Generates a single full name" in system or "Generates a unique full name" in system:
            self._names += 1
            result = f"模拟成员 {self._names}"
        elif "# Agent Generator" in user:
            particularities = unescape(user.split("## Agent Particularities", 1)[1])
            values, _ = json.JSONDecoder().raw_decode(particularities[particularities.index("{"):])
            name = values.get("name", f"模拟成员 {self._names}")
            result = _bottle_persona(name, values)
        elif "given a short biography" in system:
            result = "通勤时随身带水，买杯子时会比较实际用途和价格。"
        else:
            raise ModelError("未知的 TinyTroupe 演示步骤。")
        if isinstance(result, str) and json_mode:
            result = {"value": result, "justification": "演示响应"}
        return {
            "role": "assistant",
            "content": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False),
        }


def _factory_arguments(user: str) -> dict:
    arguments = user.split("## Named parameters\n", 1)[1]
    return json.JSONDecoder().raw_decode(arguments)[0]


def _bottle_persona(name: str, values: dict) -> dict:
    priority = values.get("通勤携带优先项", "防漏和重量")
    evidence = values.get("环保证据核对重点")
    quick = values.get("证据关注度") == "低" or (priority == "防漏" and not evidence)
    return {
        "name": name, "age": 32, "gender": "未设定", "nationality": "未设定", "residence": "城市",
        "education": "未设定",
        "occupation": {"title": "办公室职员"},
        "long_term_goals": ["让通勤更省事"],
        "style": "说话务实，看广告时倾向快速浏览。" if quick else "说话务实，会核对产品的日常使用细节。",
        "personality": {
            "traits": ["购买日用品时会比较价格和功能"],
            "big_five": {
                "openness": "中等", "conscientiousness": "中等", "extraversion": "未设定",
                "agreeableness": "未设定", "neuroticism": "未设定",
            },
        },
        "preferences": {"likes": [str(priority), str(values.get("清洁偏好", "容易清洗"))]},
        "beliefs": [f"看见环保宣称时先核对{evidence}。"] if evidence else ["日用品要方便通勤携带。"],
        "skills": ["比较日用品规格"],
        "behaviors": {"routines": {"workday": ["上下班路上用水杯补水"]}},
        "health": "未设定",
        "relationships": [],
        "other_facts": ["本角色是水杯报告的演示派生样本。"],
    }


def demo_reaction(member: dict, ad_copy: str) -> dict:
    revised = ad_copy == REVISED
    if "specification" in member:
        quick = "快速浏览" in member["specification"]["persona"]["style"]
    else:
        quick = (
            member["name"] == "地铁上快速浏览"
            or member["sampled_values"].get("证据关注度") == "低"
        )
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
