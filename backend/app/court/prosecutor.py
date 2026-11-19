from ..core.llm import ModelProvider
from ..models import CourtStep, TurnOutput


INSTRUCTION = (
    "你是环保广告模拟庭审的控方。用案卷事实和规则说明风险，必要时收窄或撤回主张。"
    "如果收到 reply_to，具体回应这条辩方发言，并把同一 ID 写进 responds_to。"
    "第一轮开场的 responds_to 为 null。引证只填案卷 citations 中的 source_id。"
    "把待补材料写进 evidence_requested。用中文简短解释，保留必要英文原句。"
    '示例 JSON：{"position":"maintain","argument":"主张及理由","source_ids":[],'
    '"responds_to":null,"evidence_requested":[]}'
)


def speak(provider: ModelProvider, step: CourtStep, context: dict) -> TurnOutput:
    return provider.complete(step=step, instruction=INSTRUCTION, context=context, output=TurnOutput)
