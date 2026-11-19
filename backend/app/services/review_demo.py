"""Review-only fixture, independent of removed deliberation features."""
from dataclasses import dataclass

from ..core.model_api import ModelError


@dataclass(frozen=True)
class ExampleInput:
    risk_id: str = "demo-eco-bottle"
    review_id: str = "demo-review-1"
    asset_version_id: str = "demo-asset-1"
    original_text: str = "100% Eco-Friendly. Meet the Everyday Bottle."
    claim_quote: str = "100% Eco-Friendly"
    reason: str = "整体环保宣称缺少可核验的适用范围与产品证明，需要补证或收窄表达。"


DEMO_INPUT = ExampleInput()


class DemoProvider:
    mode = "demo"
    model = "demo-fixture"

    def complete(self, **_kwargs):
        raise ModelError("固定演示模式仅支持预设审核案例，请配置实时模式处理新素材。")
