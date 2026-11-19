from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ..core.model_api import ModelError

from .models import TheoryReference


@dataclass(frozen=True)
class Theory:
    theory_id: str
    title: str
    purpose: str
    content: str
    source: str

    def reference(self) -> TheoryReference:
        return TheoryReference(
            theory_id=self.theory_id,
            title=self.title,
            source=self.source,
            version=sha256(self.content.encode()).hexdigest()[:12],
        )

    def option(self) -> dict[str, str]:
        return {"theory_id": self.theory_id, "title": self.title, "purpose": self.purpose}

    def material(self) -> dict[str, str]:
        return {**self.option(), "content": self.content, "source": self.source}


BUILTIN_THEORIES = (
    Theory(
        "stp", "STP（细分、目标与定位）", "保持已确认客群的边界",
        "在用户确认的客群内做情境变体。根据实际购买需求识别差异，避免凭空给这些变体分配人群份额。",
        "AI Marketing Court v1.0 §6.3",
    ),
    Theory(
        "jtbd", "JTBD（待完成的任务）", "区分购买产品要解决的问题",
        "区分消费情境、要完成的任务、替代选择与购买动机。变化应和同一基础画像兼容。",
        "https://hbr.org/2016/09/know-your-customers-jobs-to-be-done",
    ),
    Theory(
        "elm", "ELM（精细加工可能性模型）", "按观看环境设置注意力和核查动机",
        "用动机和处理条件区分低注意力快速浏览与愿意核实证据的情境。把注意力和提供的信息一起考虑。",
        "https://doi.org/10.1016/S0065-2601(08)60214-2",
    ),
    Theory(
        "pkm", "PKM（说服知识模型）", "探索对商业说服和信任线索的反应",
        "模拟消费者如何察觉说服意图、回应夸张表达以及要求证据，把这种反应标为情境假设。",
        "https://doi.org/10.1086/209380",
    ),
)


class TheoryCatalog:
    def __init__(self, skill_path: Path | None = None):
        self.theories = {item.theory_id: item for item in BUILTIN_THEORIES}
        if skill_path is not None:
            with skill_path.expanduser().open(encoding="utf-8-sig") as file:
                content = file.read(24_001)
            if not content.strip() or len(content) > 24_000:
                raise ValueError("The configured marketing Skill must contain 1–24,000 characters.")
            self.theories["team_skill"] = Theory(
                "team_skill", "团队配置的营销理论 Skill",
                "本项目的营销画像和广告情境派生方法，优先考虑其适用性",
                content, skill_path.name,
            )

    def options(self) -> list[dict[str, str]]:
        return [theory.option() for theory in self.theories.values()]

    def lookup(self, theory_ids: list[str]) -> list[Theory]:
        if len(set(theory_ids)) != len(theory_ids) or set(theory_ids) - self.theories.keys():
            raise ModelError("主 Agent 选择了无效或重复的营销理论。")
        return [self.theories[theory_id] for theory_id in theory_ids]
