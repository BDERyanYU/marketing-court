"""User-supplied example inputs, independent of generated test results."""
from pathlib import Path

DIRECTORY = Path(__file__).parent / "examples"
PAPER_REPORT = (DIRECTORY / "copier-paper-research.txt").read_text(encoding="utf-8").strip()
PAPER_ORIGINAL = (DIRECTORY / "copier-paper-a.txt").read_text(encoding="utf-8").strip()
PAPER_REVISED = (DIRECTORY / "copier-paper-b.txt").read_text(encoding="utf-8").strip()
PAPER_NOTICE = "调研报告与 A/B 文案由用户提供，产品属性、认证及法规表述未核验。"


def paper_personas():
    profiles = [
        ("德国中小微企业/律所行政采购员", "打印海量合同草稿、税务单据、内部流转文件、快递面单", "极其讨厌卡纸（会打断办公流）"),
        ("公共机构与非营利组织采购者", "大批量印制试卷、讲义、活动传单、合唱团乐谱", "价格透明且支持合规电子发票是核心门槛"),
        ("环保居家办公者", "希望减少包裹配送次数（买大箱装减少碳足迹）", "逐字核对产品详情页的认证编号"),
        ("重度打印家庭与高校学生", "儿童日常涂鸦绘画", "对品牌无忠诚度"),
    ]
    return [{"name": name, "traits": [
        {"attribute": attribute, "value": quote, "status": "grounded", "source_quote": quote}
        for attribute, quote in [("使用场景", use), ("购买关注点", concern)]
    ]} for name, use, concern in profiles]


PAPER_DIMENSIONS = [
    {"name": "打印场景", "values": ["办公室黑白草稿", "家庭学习打印"]},
    {"name": "购买关注点", "values": ["设备适配", "认证与单张价格"]},
]


def paper_persona(name, values):
    use = values.get("打印场景", "日常黑白打印")
    concern = values.get("购买关注点", "设备适配与价格")
    return {
        "name": name, "age": 35, "gender": "未设定", "nationality": "未设定", "residence": "德国",
        "education": "未设定", "occupation": {"title": "日常打印耗材采购者"},
        "long_term_goals": ["按使用需求采购再生复印纸"],
        "style": f"务实比较纸张用途，重点关注{concern}。",
        "personality": {"traits": ["购买耗材前核对规格"], "big_five": {
            key: "未设定" for key in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]}},
        "preferences": {"likes": [use, concern]}, "beliefs": ["认证与设备兼容性需要核实"],
        "skills": ["比较纸张规格与单张价格"], "behaviors": {"routines": {"workday": [use]}},
        "health": "未设定", "relationships": [], "other_facts": ["本角色是复印纸报告的固定演示样本，非真实受访者。"],
    }


def paper_reaction(ad_copy):
    revised = ad_copy == PAPER_REVISED
    return {
        "interpretation": "自然色再生纸，B 版明确说明偏暗及黑白打印用途。" if revised else "自然白再生复印纸，适合日常打印。",
        "noticed": "色差、黑白用途及粉尘提示" if revised else "再生纤维、规格与认证编号",
        "possible_misreading": None if revised else "可能把 Natural White 理解为接近普通白纸。",
        "evidence_needed": ["实际纸色样张", "打印机适用规格", "FSC 及蓝天使认证原件" if revised else "FSC 认证原件"],
        "trust_reason": "使用限制更明确，但新增认证及粉尘表述仍需核验。" if revised else "给出了白度参数，但缺少直观的色差对照。",
        "uncertainty": "未知实际价格、设备表现与认证真实性；这是预设反馈。",
        "scores": {"clarity": 4 if revised else 3, "trust": 3, "appeal": 3, "purchase_interest": 3},
        "vote": "unsure", "vote_reason": "先核对价格、样张及设备适配再决定。",
    }
