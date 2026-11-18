from ..core.model_api import ModelProvider

from .models import CourtStep, TurnOutput


INSTRUCTION = (
    "你是环保广告模拟庭审的辩方。围绕控方刚提出的争点质疑解释、适用范围或证据充分性。"
    "可以让步、提出条件化解释或请求补证。将假设标为假设。"
    "具体回应 reply_to 对应的发言，并将该 ID 写进 responds_to。"
    "引证只填案卷 citations 中的 source_id。用中文简短解释，保留必要英文原句。"
    '示例 JSON：{"position":"challenge","argument":"质疑及理由","source_ids":[],'
    '"responds_to":"prosecution_1","evidence_requested":[]}'
)


def speak(provider: ModelProvider, step: CourtStep, context: dict) -> TurnOutput:
    return provider.complete(step=step, instruction=INSTRUCTION, context=context, output=TurnOutput)
