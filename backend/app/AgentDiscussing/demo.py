"""Sample model replies. The original Moot engine still runs the demonstration."""

import json
import re

from moot.engine.moderator import OPENING_TASK, REPORT_TASK, SELECTION_TASK, SUMMARY_TASK
from moot.providers import ChatRequest

from .models import DiscussionIssue


_PARTICIPANTS = (
    ("Lin", "法规解释", "指出指引的适用范围，保留解释上的不确定性。"),
    ("Sam", "证据核对", "核对材料是否支持整句宣称，并说明缺少哪份证明。"),
    ("Jo", "文案复核", "提出可核查的较窄表述，等待补证后重新审核。"),
)


def reply(request: ChatRequest, issue: DiscussionIssue) -> str:
    system, prompt = request.messages[0].content, request.messages[-1].content
    citation = f" [source:{issue.sources[0].source_id}]" if issue.sources else ""
    if system.startswith("You design panels for Moot"):
        return json.dumps({
            "topic": issue.question, "format": "brainstorm", "options": [],
            "agents": [{"name": name, "role": role, "viewpoint": stance} for name, role, stance in _PARTICIPANTS],
            "rationale": "演示角色从适用范围、证明材料和文案修改三个视角讨论。",
        }, ensure_ascii=False)
    if system.startswith("You review discussion panels for Moot"):
        return '{"balanced":true,"notes":["演示角色分配覆盖三个不同视角。"]}'
    if "the moderator of a discussion" in system:
        if OPENING_TASK in prompt:
            return (
                "这是一次演示复核。请分别说明规则适用范围和目前缺少的证明。"
                '<plan>{"subquestions":["规则能覆盖整句宣称吗？","还需要哪份证据？"]}</plan>'
            )
        if SELECTION_TASK in prompt:
            match = re.search(r"Who still has turns in this round:\n- ([^:]+):", prompt)
            return json.dumps({"next": match[1] if match else "Lin", "reason": "听取尚未发言的视角"})
        if SUMMARY_TASK in prompt:
            return f"演示小结：已指出规则覆盖范围与产品证明是两个需要分别核对的问题。{citation}"
        if REPORT_TASK in prompt:
            return (
                "演示纪要：各方同意先核对规则的适用范围及产品证明。"
                f"当前材料能否支持整句承诺仍有待确认，建议补证后复审。{citation}"
            )
    for name, role, stance in _PARTICIPANTS:
        if system.startswith(f"You are {name}"):
            return f"从{role}角度，{stance}{citation}"
    return f"演示发言：当前证据仍有待核对。{citation}"
