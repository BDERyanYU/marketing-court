"""Versioned, bounded regulator guidance. No automatic cross-market fallback."""

import hashlib
import json
from pathlib import Path

from ..models.review import PolicySource

POLICY_PATH = Path(__file__).resolve().parents[1] / "data" / "policies" / "gb-cma-demo-1.json"
RULE_VERSION = "gb-cma-demo-1"


def retrieve(market: str, claim_type: str) -> list[PolicySource]:
    if market != "GB" or claim_type != "environmental":
        return []
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    sources = [PolicySource(**s) for s in payload["sources"]]
    for source in sources:
        if hashlib.sha256(source.excerpt.encode()).hexdigest() != source.content_hash:
            raise ValueError("Rule excerpt hash mismatch")
    return sources
