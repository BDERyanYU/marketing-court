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
    for length in range(1, min(len(anchors), 8) + 1):
        for start in range(len(anchors) - length + 1):
            end = start + length
            candidate = normalized(" ".join(a.text for a in anchors[start:end]))
            if target in candidate and all(a.score >= 0.8 for a in anchors[start:end]):
                selected = anchors[start:end]
                break
        if selected:
            break
    return Claim(**item.model_dump(), claim_id=new_id("claim"), anchor_ids=[a.anchor_id for a in selected],
                 location_status="located" if selected else "needs_confirmation")
