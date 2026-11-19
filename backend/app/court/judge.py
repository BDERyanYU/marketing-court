from ..core.llm import ModelProvider
from ..models import CourtStep, Judgment


INSTRUCTION = (
    "你独立复核一场模拟庭审中的环保广告风险。按原文、市场、案卷规则摘录和证据状态评估双方主张。"
    "将控辩说法视为待检查的论点，区分材料未提供与事实已被推翻。"
    "用中文给出风险复核建议及适用理由。只引用案卷 citations 中的 source_id。"
    "如需补证，写明所需资料。你的意见只处理本案风险提示，投放审批由人工负责。"
    '示例 JSON：{"disposition":"insufficient_evidence","reason":"本案材料不足以支持该宣称",'
    '"source_ids":["G1"],"evidence_requested":["与宣称范围匹配的材料"]}'
)


def review(provider: ModelProvider, context: dict) -> Judgment:
    return provider.complete(
        step=CourtStep.JUDGMENT,
        instruction=INSTRUCTION,
        context=context,
        output=Judgment,
    )
