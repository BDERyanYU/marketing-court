from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models import CourtInput
from backend.app.court.repository import CourtRepository


DEMO_RISK = "demo-eco-bottle"


@pytest.fixture(autouse=True)
def use_demo_by_default(monkeypatch):
    monkeypatch.setenv("COURT_MODE", "demo")


def open_case(client, risk_id=DEMO_RISK):
    response = client.post(f"/api/risks/{risk_id}/appeals")
    assert response.status_code == 201, response.json()
    return response.json()


def advance(client, case_id, step):
    return client.post(f"/api/cases/{case_id}/advance", json={"expected_step": step})


def test_case_resumes_after_restart_and_preserves_the_order(tmp_path):
    database = tmp_path / "court.sqlite3"
    with TestClient(create_app(database_path=database)) as client:
        opened = open_case(client)
        case_id = opened["case_id"]
        assert opened["mode"] == "demo"
        assert opened["next_step"] == "prosecution_1"
        assert opened["snapshot"]["claim_quote"] == "100% Eco-Friendly"
        first_turn = advance(client, case_id, "prosecution_1")
        assert first_turn.status_code == 200
        assert first_turn.json()["next_step"] == "defense_1"

    with TestClient(create_app(database_path=database)) as client:
        restored = client.get(f"/api/cases/{case_id}").json()
        assert restored == first_turn.json()
        assert advance(client, case_id, "prosecution_1").json() == restored
        assert advance(client, case_id, "judgment").status_code == 409

        for step in ("defense_1", "prosecution_2", "defense_2", "judgment"):
            response = advance(client, case_id, step)
            assert response.status_code == 200, response.json()
        finished = response.json()
        assert finished["status"] == "completed"
        assert finished["next_step"] is None
        assert [turn["role"] for turn in finished["turns"]] == [
            "prosecutor", "defense", "prosecutor", "defense",
        ]
        assert [turn["responds_to"] for turn in finished["turns"]] == [
            None, "prosecution_1", "defense_1", "prosecution_2",
        ]
        assert finished["judgment"]["disposition"] == "insufficient_evidence"
        assert set(finished["judgment"]["source_ids"]) == {"G1", "G2"}
        assert advance(client, case_id, "judgment").json() == finished


class RecordingProvider:
    mode = "live"
    model = "test-model"

    def __init__(self):
        self.source_ids = ["T1"]
        self.requests = []

    def complete(self, *, step, instruction, context, output):
        self.requests.append((step, context))
        if step == "judgment":
            return output.model_validate({
                "disposition": "insufficient_evidence",
                "reason": "The evidence provided does not cover the claim.",
                "source_ids": self.source_ids,
                "evidence_requested": ["Evidence for the advertised scope"],
            })
        return output.model_validate({
            "position": "challenge",
            "argument": "Check whether the cited guidance supports this claim.",
            "source_ids": self.source_ids,
            "responds_to": context["reply_to"],
            "evidence_requested": [],
        })


def workflow_input():
    return {
        "risk_id": "review-risk-1",
        "review_id": "review-1",
        "asset_version_id": "asset-v1",
        "original_text": "An eco-friendly bottle.",
        "claim_quote": "eco-friendly",
        "market": "GB",
        "assessment": "requires_substantiation",
        "reason": "The claim is broad.",
        "rule_pack_version": "rules-1",
        "citations": [{
            "source_id": "T1",
            "excerpt": "Claims must be substantiated",
            "url": "https://www.gov.uk/example",
        }],
        "product_evidence_status": "not_supplied",
    }


def test_workflow_contract_and_role_contexts(tmp_path):
    provider = RecordingProvider()
    payload = workflow_input()
    with TestClient(create_app(database_path=tmp_path / "court.db", provider=provider)) as client:
        path = "/api/court-inputs/review-risk-1"
        assert client.put(path, json=payload).status_code == 200
        assert client.put(path, json=payload).status_code == 200
        case = open_case(client, payload["risk_id"])
        assert case["snapshot"] == payload
        assert client.put(path, json={**payload, "rule_pack_version": "rules-2"}).status_code == 409
        assert client.put(path, json={**payload, "claim_quote": "invented"}).status_code == 422
        for step in ("prosecution_1", "defense_1", "prosecution_2", "defense_2", "judgment"):
            response = advance(client, case["case_id"], step)
            assert response.status_code == 200, response.json()

    assert provider.requests[0][1]["earlier_turns"] == []
    assert provider.requests[1][1]["earlier_turns"][0]["step"] == "prosecution_1"
    assert provider.requests[2][1]["reply_to"] == "defense_1"
    judge_context = provider.requests[4][1]
    assert len(judge_context["earlier_turns"]) == 4
    assert judge_context["case_facts"]["rule_pack_version"] == "rules-1"
    assert "initial_assessment" not in judge_context


def test_unknown_citation_leaves_the_step_ready_to_retry(tmp_path):
    provider = RecordingProvider()
    provider.source_ids = ["invented"]
    with TestClient(create_app(database_path=tmp_path / "court.db", provider=provider)) as client:
        case = open_case(client)
        case_id = case["case_id"]
        assert advance(client, case_id, "prosecution_1").status_code == 502
        saved = client.get(f"/api/cases/{case_id}").json()
        assert saved["turns"] == []
        assert saved["next_step"] == "prosecution_1"
        provider.source_ids = ["G1"]
        assert advance(client, case_id, "prosecution_1").json()["next_step"] == "defense_1"


def test_concurrent_requests_commit_only_one_turn(tmp_path):
    entered = Event()
    release = Event()

    class SlowProvider(RecordingProvider):
        def complete(self, **request):
            entered.set()
            assert release.wait(timeout=5)
            return super().complete(**request)

    provider = SlowProvider()
    provider.source_ids = ["G1"]
    with TestClient(create_app(database_path=tmp_path / "court.db", provider=provider)) as client:
        case_id = open_case(client)["case_id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            running = pool.submit(advance, client, case_id, "prosecution_1")
            try:
                assert entered.wait(timeout=5)
                competing = advance(client, case_id, "prosecution_1")
                assert competing.status_code == 409
            finally:
                release.set()
            assert running.result(timeout=5).status_code == 200
        replay = advance(client, case_id, "prosecution_1")
        assert [x["step"] for x in replay.json()["turns"]] == ["prosecution_1"]
        assert len(provider.requests) == 1


def test_demo_mode_identifies_its_single_supported_case(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "court.db")) as client:
        payload = workflow_input()
        assert client.put("/api/court-inputs/review-risk-1", json=payload).status_code == 200
        assert client.post("/api/risks/review-risk-1/appeals").status_code == 409
        assert client.post("/api/risks/does-not-exist/appeals").status_code == 404


def test_an_existing_case_cannot_mix_demo_and_live_outputs(tmp_path):
    database = tmp_path / "court.db"
    with TestClient(create_app(database_path=database)) as client:
        case_id = open_case(client)["case_id"]
        first_turn = advance(client, case_id, "prosecution_1").json()

    provider = RecordingProvider()
    with TestClient(create_app(database_path=database, provider=provider)) as client:
        assert advance(client, case_id, "defense_1").status_code == 409
        assert client.get(f"/api/cases/{case_id}").json() == first_turn
        assert provider.requests == []


def test_refreshing_the_sample_does_not_block_opening_an_existing_database(tmp_path):
    database = tmp_path / "court.db"
    earlier_sample = CourtInput.model_validate({**workflow_input(), "risk_id": DEMO_RISK})
    repository = CourtRepository(database)
    repository.register_input(earlier_sample)
    existing_case = repository.create_case(earlier_sample, "live", "test-model")
    case_id = str(existing_case.case_id)

    provider = RecordingProvider()
    with TestClient(create_app(database_path=database, provider=provider)) as client:
        restored = client.get(f"/api/cases/{case_id}")
        assert restored.json()["snapshot"] == earlier_sample.model_dump(mode="json")
        continued = advance(client, case_id, "prosecution_1")
        assert continued.status_code == 200
        assert continued.json()["next_step"] == "defense_1"
