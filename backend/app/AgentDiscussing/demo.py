"""Sample model replies. The original Moot engine still runs the demonstration."""

import json
import re

from moot.engine.moderator import OPENING_TASK, REPORT_TASK, SELECTION_TASK, SUMMARY_TASK
from moot.providers import ChatRequest

from .invitees import GUEST_PROFILE_MARKER, GUEST_PROMPT, brief
from .models import DiscussionSubject, StandaloneIssue


_PARTICIPANTS = (
    ("Lin", "法规解释", "指出指引的适用范围，保留解释上的不确定性。"),
    ("Sam", "证据核对", "核对材料是否支持整句宣称，并说明缺少哪份证明。"),
    ("Jo", "文案复核", "提出可核查的较窄表述，等待补证后重新审核。"),
)

_STANDALONE_PARTICIPANTS = (
    ("Lin", "议题分析", "先明确目标和判断标准，再比较不同方案。"),
    ("Sam", "事实核对", "指出还缺哪些事实，以及可以怎么核实。"),
    ("Jo", "受众理解", "从使用者的理解和实际需求看方案。"),
    ("Ari", "执行方案", "提出一个可以小范围验证的行动方案。"),
    ("Mei", "反方视角", "找出最可能影响结论的假设，试着从反例验证。"),
    ("Kai", "风险评估", "说明方案在什么条件下可能失效。"),
    ("Noa", "效果验证", "提出可以观察和比较的指标。"),
    ("Yu", "资源评估", "比较不同方案需要的时间与投入。"),
)


def reply(request: ChatRequest, issue: DiscussionSubject) -> str:
    system, prompt = request.messages[0].content, request.messages[-1].content
    standalone = isinstance(issue, StandaloneIssue)
    participants = _STANDALONE_PARTICIPANTS if standalone else _PARTICIPANTS
    citation = f" [source:{issue.sources[0].source_id}]" if issue.sources else ""
    if system.startswith("You design panels for Moot"):
        requested = re.search(r'"agents": exactly (\d+) participants', system)
        count = int(requested[1]) if requested else 3
        rationale = "演示角色从议题和待验证问题出发。" if standalone else "演示角色从适用范围、证明材料和文案修改三个视角讨论。"
        return json.dumps({
            "topic": issue.question, "format": "brainstorm", "options": [],
            "agents": [{"name": name, "role": role, "viewpoint": stance} for name, role, stance in participants[:count]],
            "rationale": rationale,
        }, ensure_ascii=False)
    if system.startswith("You review discussion panels for Moot"):
        return '{"balanced":true,"notes":["演示角色具有不同的讨论视角。"]}'
    if system.startswith(GUEST_PROMPT):
        raw = system.split(GUEST_PROFILE_MARKER, 1)[1].split("\n", 1)[0]
        profile = json.loads(raw)
        priorities = brief(list(profile["sampled_values"].values()))
        attention = f"我挑产品会关注{priorities}。" if priorities else "我会先看产品的具体信息。"
        if standalone:
            return f"{attention}我想先看看具体的产品或使用场景，再判断这个说法是否符合我的需求。"
        return f"{attention}这句承诺看起来涵盖整件产品。我想知道哪些部件有证据，哪些没包含。"
    if "the moderator of a discussion" in system:
        if OPENING_TASK in prompt:
            if standalone:
                return (
                    "请围绕议题说明你关注的信息，以及哪些假设需要核实。"
                    '<plan>{"subquestions":["我们如何判断各方案？","什么信息会改变判断？"]}</plan>'
                )
            return (
                "这是一次演示复核。请分别说明规则适用范围和目前缺少的证明。"
                '<plan>{"subquestions":["规则能覆盖整句宣称吗？","还需要哪份证据？"]}</plan>'
            )
        if SELECTION_TASK in prompt:
            match = re.search(r"Who still has turns in this round:\n- ([^:]+):", prompt)
            return json.dumps({"next": match[1] if match else "Lin", "reason": "听取尚未发言的视角"})
        if SUMMARY_TASK in prompt:
            if standalone:
                return "演示小结：先统一判断标准，列出分歧和需要验证的假设。"
            return f"演示小结：已指出规则覆盖范围与产品证明是两个需要分别核对的问题。{citation}"
        if REPORT_TASK in prompt:
            if standalone:
                return "演示纪要：记录各方的判断标准和分歧，再用具体材料或小范围验证检验主要假设。"
            guest_note = " 数字人像也指出，广告需要交代宣称适用于产品的哪一部分。" if issue.invitee else ""
            return (
                "演示纪要：各方同意先核对规则的适用范围及产品证明。"
                f"当前材料能否支持整句承诺仍有待确认，建议补证后复审。{guest_note}{citation}"
            )
    for name, role, stance in participants:
        if system.startswith(f"You are {name}"):
            return f"从{role}角度，{stance}{citation}"
    return f"演示发言：当前证据仍有待核对。{citation}"
