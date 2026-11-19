from pathlib import Path
from typing import Any

from ..core.llm import ModelError, Output
from ..models import CourtInput, CourtStep, RunMode


DEMO_INPUT_PATH = Path(__file__).resolve().parents[3] / "examples" / "court-input.json"
DEMO_INPUT = CourtInput.model_validate_json(DEMO_INPUT_PATH.read_text(encoding="utf-8"))

RESPONSES = {
    CourtStep.PROSECUTION_1: {
        "position": "maintain",
        "argument": "G1 提到泛化及绝对化宣称的风险。读者可能把 100% Eco-Friendly 理解为针对整只水杯。",
        "source_ids": ["G1"],
        "responds_to": None,
        "evidence_requested": [],
    },
    CourtStep.DEFENSE_1: {
        "position": "challenge",
        "argument": "可能的较窄解释是商家在描述某个部件。应检查完整文案是否给了消费者可见的范围限定。",
        "source_ids": [],
        "responds_to": CourtStep.PROSECUTION_1,
        "evidence_requested": [],
    },
    CourtStep.PROSECUTION_2: {
        "position": "maintain",
        "argument": "回应部件解释，第二句只是介绍产品，没有限定具体部件。G2 要求有证明，本案未收到能覆盖整体宣称的资料。",
        "source_ids": ["G1", "G2"],
        "responds_to": CourtStep.DEFENSE_1,
        "evidence_requested": ["与整只水杯环保宣称范围匹配的证明材料"],
    },
    CourtStep.DEFENSE_2: {
        "position": "concede",
        "argument": "现有文案无法支持部件限定。建议先保留产品介绍句，取得部件材料后再审查更具体的宣称。",
        "source_ids": ["G2"],
        "responds_to": CourtStep.PROSECUTION_2,
        "evidence_requested": ["若改用部件宣称，补充涉及该部件的规格或核验材料"],
    },
    CourtStep.JUDGMENT: {
        "disposition": "insufficient_evidence",
        "reason": "广告未明确限定环保宣称的范围。本案未收到相应证明，建议保留待补证提示。",
        "source_ids": ["G1", "G2"],
        "evidence_requested": ["可核对的证明来源、适用范围和适用条件"],
    },
}


class DemoProvider:
    mode: RunMode = "demo"
    model = "demo-fixture"

    def complete(
        self,
        *,
        step: CourtStep,
        instruction: str,
        context: dict[str, Any],
        output: type[Output],
    ) -> Output:
        if context["risk_id"] != DEMO_INPUT.risk_id:
            from ..services.greenlint import scripted_input
            snapshot = scripted_input(context["risk_id"])
            if snapshot is None:
                raise ModelError("Demo mode only has scripted responses for predefined example risks.")
            quote = snapshot.claim_quote
            responses = {
                CourtStep.PROSECUTION_1: dict(position="maintain", argument=f"G1 提醒泛化或绝对化宣称可能误导。本案的‘{quote}’需要明确适用范围，并依据 G2 提供相应证明。", source_ids=["G1", "G2"], responds_to=None, evidence_requested=[]),
                CourtStep.DEFENSE_1: dict(position="challenge", argument="现有材料只是文案摘录，不能仅因缺少附件就断定产品属性不实。应先核对商品页完整限定、适用部件和可提供的证明。", source_ids=["G2"], responds_to=CourtStep.PROSECUTION_1, evidence_requested=[]),
                CourtStep.PROSECUTION_2: dict(position="request_evidence", argument="同意不能推定属性虚假，但当前案卷没有证明可覆盖消费者理解的宣称范围。应继续保留待核查项，补齐资料后再判断。", source_ids=["G1", "G2"], responds_to=CourtStep.DEFENSE_1, evidence_requested=["产品属性依据及宣称范围说明"]),
                CourtStep.DEFENSE_2: dict(position="narrow", argument="建议先删除当前待补证句，保留其他产品介绍；其余环保宣称仍须分别检查，不应由单句改写推定整篇合规。", source_ids=["G2"], responds_to=CourtStep.PROSECUTION_2, evidence_requested=["与实际材料或碳核算范围一致的证明"]),
                CourtStep.JUDGMENT: dict(disposition="insufficient_evidence", reason="当前仅有预设文案，无法核实属性、认证或排放依据。保留待补证意见，不认定品牌违法；补齐材料后再复核。", source_ids=["G1", "G2"], evidence_requested=["完整广告上下文、适用范围与可核验的产品证明"]),
            }
            return output.model_validate(responses[step])
        return output.model_validate(RESPONSES[step])
