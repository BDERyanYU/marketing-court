import json
from collections import Counter
from threading import Barrier, Lock

import httpx
from fastapi.testclient import TestClient

from backend.app.core.model_api import DeepSeekProvider
from backend.app.jury import demo
from backend.app.jury.main import create_app


class RecordingProvider(demo.DemoProvider):
    def __init__(self, *, verify_overlap: bool = False):
        self.evaluator = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(self.respond))
        self.calls = []
        self.lock = Lock()
        self.active = 0
        self.peak = 0
        self.first_pair = Barrier(2, timeout=2) if verify_overlap else None
        self.fail_once = None

    def complete(self, *, step, instruction, context, output):
        if step == "jury_reaction":
            return self.evaluator.complete(step=step, instruction=instruction, context=context, output=output)
        return super().complete(step=step, instruction=instruction, context=context, output=output)

    def respond(self, request):
        assert request.headers["Authorization"] == "Bearer test-only-key"
        messages = json.loads(request.content)["messages"]
        assert [message["role"] for message in messages] == ["system", "user"]
        context = json.loads(messages[1]["content"])
        assert context.keys() == {"step", "base_persona", "member", "ad_copy"}
        key = context["member"]["name"], context["ad_copy"]
        with self.lock:
            self.calls.append(context)
            self.active += 1
            self.peak = max(self.active, self.peak)
            fail = key == self.fail_once
            if fail:
                self.fail_once = None
        try:
            if self.first_pair is not None and key in {
                ("模拟成员 1", demo.ORIGINAL), ("模拟成员 2", demo.REVISED),
            }:
                self.first_pair.wait()
            if fail:
                return httpx.Response(502)
            output = demo.demo_reaction(context["member"], context["ad_copy"])
            return httpx.Response(200, json={"choices": [
                {"finish_reason": "stop", "message": {"content": json.dumps(output)}},
            ]})
        finally:
            with self.lock:
                self.active -= 1


def make_comparison(client):
    report = client.post("/api/jury/reports", files={
        "file": ("bottle-research.txt", demo.REPORT.encode()),
    }).raise_for_status().json()
    panel = client.post("/api/jury/panels", json={
        "report_id": report["report_id"], "persona_id": report["personas"][0]["persona_id"],
    }).raise_for_status().json()
    comparison = client.post("/api/jury/comparisons", json={
        "panel_id": panel["panel_id"], "original_text": demo.ORIGINAL, "revised_text": demo.REVISED,
    }).raise_for_status().json()
    return "/api/jury/comparisons/" + comparison["comparison_id"], panel


def advance_members(client, path, index):
    return client.post(path + "/advance-members", json={"expected_index": index})


def test_members_overlap_and_each_member_uses_one_frozen_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("JURY_MAX_CONCURRENT_MEMBERS", "2")
    provider = RecordingProvider(verify_overlap=True)
    app = create_app(database_path=tmp_path / "jury.db", provider=provider)

    with TestClient(app) as client:
        path, panel = make_comparison(client)
        first = advance_members(client, path, 0).raise_for_status().json()
        assert len(first["exposures"]) == 4 and first["next_index"] == 4
        assert advance_members(client, path, 0).raise_for_status().json() == first
        final = advance_members(client, path, 4).raise_for_status().json()

    assert provider.peak == 2
    assert len(provider.calls) == 6
    assert final["next_index"] is None
    assert [pair["member_id"] for pair in final["pairs"]] == [member["member_id"] for member in panel["members"]]
    for index, member in enumerate(panel["members"]):
        calls = [call for call in provider.calls if call["member"]["name"] == member["name"]]
        order = [demo.ORIGINAL, demo.REVISED] if index % 2 == 0 else [demo.REVISED, demo.ORIGINAL]
        assert [call["ad_copy"] for call in calls] == order
        assert calls[0]["member"] == calls[1]["member"]
        assert calls[0]["base_persona"] == calls[1]["base_persona"]


def test_parallel_wave_saves_other_members_and_resumes_a_failed_version(tmp_path, monkeypatch):
    monkeypatch.setenv("JURY_MAX_CONCURRENT_MEMBERS", "2")
    database = tmp_path / "jury.db"
    provider = RecordingProvider()

    with TestClient(create_app(database_path=database, provider=provider)) as client:
        path, panel = make_comparison(client)
        checkpoint = client.post(path + "/advance", json={"expected_index": 0}).raise_for_status().json()
        assert checkpoint["next_index"] == 1
        provider.fail_once = ("模拟成员 1", demo.REVISED)

        assert advance_members(client, path, 1).status_code == 502
        partial = client.get(path).raise_for_status().json()
        assert partial["next_index"] == 1
        assert {(item["member_id"], item["variant"]) for item in partial["exposures"]} == {
            (panel["members"][0]["member_id"], "A"),
            (panel["members"][1]["member_id"], "A"),
            (panel["members"][1]["member_id"], "B"),
        }

    with TestClient(create_app(database_path=database, provider=provider)) as client:
        assert client.get(path).raise_for_status().json() == partial
        result = advance_members(client, path, 1).raise_for_status().json()
        assert result["next_index"] is None and len(result["exposures"]) == 6

    calls = Counter((item["member"]["name"], item["ad_copy"]) for item in provider.calls)
    assert len(calls) == 6
    assert calls.pop(("模拟成员 1", demo.REVISED)) == 2
    assert set(calls.values()) == {1}
