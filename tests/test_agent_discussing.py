from contextlib import closing
import sqlite3
from time import monotonic, sleep

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.review_demo import DemoProvider


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
        deadline = monotonic() + 5
        while True:
            result = client.get(discussion_url).raise_for_status().json()
            if result["status"] == "finished" or monotonic() >= deadline:
                break
            sleep(0.02)
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
