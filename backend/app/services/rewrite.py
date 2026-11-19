"""Conservative deletion preserves product facts; review is a separate step."""

import re

from ..core.llm import ModelError


def remove_claim(original: str, quote: str) -> str:
    if quote not in original:
        raise ModelError("风险原句无法在素材文字中精确找到，暂不能自动改写。")
    revised = original.replace(quote, "", 1)
    revised = re.sub(r"(?m)^\s*[.,;:!?。；，！]+\s*", "", revised).strip()
    revised = re.sub(r"[ \t]{2,}", " ", revised)
    if not revised:
        raise ModelError("删除风险宣称后没有剩余文案，请人工补充真实的产品介绍。")
    return revised
