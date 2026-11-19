from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .models import TheoryReference


@dataclass(frozen=True)
class MarketingSkill:
    content: str
    source: str

    def reference(self) -> TheoryReference:
        return TheoryReference(
            theory_id="team_skill",
            title="团队配置的营销理论 Skill",
            source=self.source,
            version=sha256(self.content.encode()).hexdigest()[:12],
        )


class TheoryCatalog:
    def __init__(self, skill_path: Path | None = None):
        self.marketing_skill: MarketingSkill | None = None
        if skill_path is not None:
            with skill_path.expanduser().open(encoding="utf-8-sig") as file:
                content = file.read(24_001)
            if not content.strip() or len(content) > 24_000:
                raise ValueError("The configured marketing Skill must contain 1–24,000 characters.")
            self.marketing_skill = MarketingSkill(content, skill_path.name)
