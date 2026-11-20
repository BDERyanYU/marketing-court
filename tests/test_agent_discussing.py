from contextlib import closing
import json
import sqlite3
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.jury import demo as jury_demo
from backend.app.main import create_app
from backend.app.services.review_demo import DemoProvider


def wait_for_discussion(client, url):
    deadline = monotonic() + 5
    while True:
        result = client.get(url).raise_for_status().json()
        if result["status"] == "finished" or monotonic() >= deadline:
            return result
        sleep(0.02)


def test_moot_roundtable_uses_the_selected_risk_and_keeps_a_saved_transcript(tmp_path):
    pytest.importorskip("moot")
    database = tmp_path / "marketing.sqlite3"
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        review = client.post("/api/demo").raise_for_status().json()
        risk = review["risks"][0]
        report_url = f"/api/reviews/{review['review_id']}/report"
        report_before = client.get(report_url).raise_for_status().json()
        start = f"/api/reviews/{review['review_id']}/risks/{risk['risk_id']}/discussions"
        response = client.post(start, json={"question": "现有证据是否能覆盖整句环保宣称？"})
        assert response.status_code == 202
        discussion_url = "/api/discussions/" + response.json()["discussion_id"]
        result = wait_for_discussion(client, discussion_url)
        assert result["end_reason"] == "completed"
        assert result["engine"] == "moot"
        assert result["issue"]["risk"] == risk
        assert result["issue"]["rule_pack_version"] == review["rule_pack_version"]
        assert {s["source_id"] for s in result["issue"]["sources"]} == set(risk["source_ids"])
        assert len(result["participants"]) == 3
        seat_ids = {"moderator", *(agent["id"] for agent in result["participants"])}
        avatars = result["avatar_indices"]
        assert set(avatars) == seat_ids
        assert len(set(avatars.values())) == len(seat_ids)
        assert all(0 <= index < 16 for index in avatars.values())
        agent_turns = [turn for turn in result["turns"] if turn["speaker_kind"] == "agent"]
        assert len({turn["speaker_id"] for turn in agent_turns}) == 3
        assert len({turn["round_index"] for turn in agent_turns}) >= 2
        assert result["report"]
        assert client.get(report_url).raise_for_status().json() == report_before
        assert client.get("/api/jury/demo").status_code == 200
    assert database.with_name("marketing.sqlite3.agent-discussions.sqlite3").is_file()
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        assert client.get(discussion_url).raise_for_status().json() == result
        removed = client.delete(f"/api/projects/{review['project_id']}").raise_for_status().json()
        assert removed["file_cleanup_pending"] is False
        assert client.get(discussion_url).status_code == 404
    with closing(sqlite3.connect(database.with_name("marketing.sqlite3.agent-discussions.sqlite3"))) as db:
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 0


def test_discussion_cannot_attach_to_a_risk_outside_the_review(tmp_path):
    database = tmp_path / "marketing.sqlite3"
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        review = client.post("/api/demo").raise_for_status().json()
        response = client.post(f"/api/reviews/{review['review_id']}/risks/missing/discussions",
                               json={"question": "能否复核这条证据？"})
        assert response.status_code == 404
        assert response.json()["detail"] == "所选风险不属于该次审核。"
        assert client.get("/health").status_code == 200
    assert not database.with_name("marketing.sqlite3.agent-discussions.sqlite3").exists()


def test_saved_digital_persona_joins_moot_with_its_own_seat(tmp_path, monkeypatch):
    pytest.importorskip("moot")
    monkeypatch.setenv("JURY_MODE", "demo")
    database = tmp_path / "marketing.sqlite3"
    jury_database = tmp_path / "jury.sqlite3"
    discussion_database = database.with_name("marketing.sqlite3.agent-discussions.sqlite3")
    with TestClient(create_app(database_path=database, provider=DemoProvider(),
                              jury_database_path=jury_database)) as client:
        invitees_url = "/api/discussions/invitees"
        assert client.get(invitees_url).raise_for_status().json() == []
        report = client.post("/api/jury/reports", files={
            "file": ("水杯报告.txt", jury_demo.REPORT.encode(), "text/plain"),
        }).raise_for_status().json()
        panel = client.post("/api/jury/panels", json={
            "report_id": report["report_id"], "persona_id": report["personas"][0]["persona_id"], "member_count": 2,
        }).raise_for_status().json()
        member = panel["members"][1]
        name = member["specification"]["persona"]["name"]
        choices = client.get(invitees_url).raise_for_status().json()
        assert choices[0]["panel_id"] == panel["panel_id"]
        assert choices[0]["report_name"] == "水杯报告.txt"
        assert {"member_id": member["member_id"], "name": name} in choices[0]["members"]

        review = client.post("/api/demo").raise_for_status().json()
        risk = review["risks"][0]
        start = f"/api/reviews/{review['review_id']}/risks/{risk['risk_id']}/discussions"
        invitee = {"panel_id": panel["panel_id"], "member_id": member["member_id"]}
        invalid = dict(invitee, member_id=str(uuid4()))
        assert client.post(start, json={"question": "消费者会如何理解这条宣称？", "invitee": invalid}).status_code == 404
        assert not discussion_database.exists()

        meeting = client.post(start, json={
            "question": "消费者会如何理解这条宣称？", "invitee": invitee,
        }).raise_for_status().json()
        url = "/api/discussions/" + meeting["discussion_id"]
        result = wait_for_discussion(client, url)
        assert result["end_reason"] == "completed"
        assert result["issue"]["invitee"] == invitee
        assert len(result["participants"]) == 4
        guest = next(agent for agent in result["participants"] if agent["id"] == member["member_id"])
        assert guest["name"] == name
        assert guest["role"] == "受邀数字人像"
        assert "prompt_override" not in guest
        assert len(set(result["avatar_indices"].values())) == 5
        assert result["avatar_indices"] == meeting["avatar_indices"]
        turns = [turn for turn in result["turns"] if turn["speaker_id"] == guest["id"]]
        assert {turn["round_index"] for turn in turns} == {0, 1, 2}
        assert all(not turn["source_ids"] for turn in turns)
        assert client.get(f"/api/jury/panels/{panel['panel_id']}").raise_for_status().json() == panel

    with closing(sqlite3.connect(discussion_database)) as db:
        (raw_state,) = db.execute("SELECT state FROM sessions WHERE id = ?", (meeting["discussion_id"],)).fetchone()
    saved = json.loads(raw_state)
    agent = next(agent for agent in saved["config"]["agents"] if agent["id"] == guest["id"])
    frozen_profile = json.loads(agent["prompt_override"].splitlines()[-1])
    assert frozen_profile["member"]["specification"] == member["specification"]
    assert frozen_profile["sampled_values"] == member["sampled_values"]
    with TestClient(create_app(database_path=database, provider=DemoProvider(),
                              jury_database_path=jury_database)) as client:
        assert client.get(url).raise_for_status().json() == result
