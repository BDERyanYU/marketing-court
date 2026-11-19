"""Exact and normalized mapping without speculative fuzzy coordinates."""

import re
import unicodedata

from ..core.store import new_id
from ..models.review import Claim, ExtractedClaim, TextAnchor


def normalized(text: str):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())


def map_claim(item: ExtractedClaim, anchors: list[TextAnchor]) -> Claim:
    target = normalized(item.claim_text)
    selected = []
    for start in range(len(anchors)):
        for end in range(start + 1, min(len(anchors), start + 8) + 1):
            candidate = normalized(" ".join(a.text for a in anchors[start:end]))
            if target in candidate:
                selected = anchors[start:end]
                break
        if selected:
            break
    return Claim(**item.model_dump(), claim_id=new_id("claim"), anchor_ids=[a.anchor_id for a in selected],
                 location_status="located" if selected else "needs_confirmation")
