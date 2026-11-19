import json
import sqlite3
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
import pytest

from backend.app.core.model_api import ModelError
from backend.app.jury.demo import DemoProvider, _factory_arguments
from backend.app.jury.main import create_app
from backend.app.jury.parsing import read_report


REPORT = "通勤人群预算较紧，购买水杯主要为了减少上下班路上补水的不便。"
BEFORE = "100% Eco-Friendly. Meet the Everyday Bottle."
AFTER = "Meet the Everyday Bottle."


class RecordingProvider(DemoProvider):
    mode = "live"
    model = "test-jury-model"

    def __init__(self):
        self.calls = []
        self.found_quote = "通勤人群预算较紧"
        self.native_calls = []
        self.invalid_plan = None
        self.has_explicit_persona = True
        self.fail_native_person = False

    def complete(self, *, step, instruction, context, output):
        self.calls.append((step, context))
        if step == "jury_personas":
            if not self.has_explicit_persona:
                return output.model_validate({"personas": []})
            data = {"personas": [{
                "name": "通勤补水者",
                "traits": [{
                    "attribute": "预算",
                    "value": "预算较紧",
                    "status": "grounded",
                    "source_quote": self.found_quote,
                }],
            }]}
        else:
            revised = context["ad_copy"] == AFTER
            data = {
                "interpretation": "这是一个水杯广告。",
                "noticed": "注意到产品名称",
                "possible_misreading": None if revised else "可能理解成整个水杯对环保有益",
                "evidence_needed": [],
                "trust_reason": "文案的承诺是否具体",
                "uncertainty": "不了解价格",
                "scores": {"clarity": 4, "trust": 4 if revised else 2, "appeal": 3, "purchase_interest": 3},
                "vote": "would_consider" if revised else "unsure",
                "vote_reason": "想了解实用信息",
            }
        return output.model_validate(data)

    def chat(self, messages, **kwargs):
        system, user = (message["content"] for message in messages[:2])
        self.native_calls.append((system, user))
        if self.fail_native_person and "# Agent Generator" in user:
            raise ModelError("Test provider failure")
        result = super().chat(messages, **kwargs)
        if self.invalid_plan and "This function defines which and how many people" in system:
            plan = json.loads(result["content"])
            if self.invalid_plan == "count":
                plan["sample_plan"][0]["quantity"] += 1
            elif self.invalid_plan == "malformed":
                plan["sample_plan"][0]["sampled_values"] = None
            else:
                plan["sample_plan"][0]["sampled_values"].pop("通勤携带优先项")
            result["content"] = json.dumps(plan)
        elif kwargs["json_mode"]:
            result["content"] = json.dumps(json.loads(result["content"]))
        return result


def upload(client, *, content=REPORT.encode(), filename="research.txt"):
    return client.post("/api/jury/reports", files={"file": (filename, content)})


def get_json(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def prepare_panel(client):
    report = get_json(upload(client), 201)
    assert "source_text" not in report
    assert report["personas"][0]["traits"][0]["source_quote"] == "通勤人群预算较紧"
    assert get_json(client.get("/api/jury/reports/" + report["report_id"])) == report
    return get_json(client.post("/api/jury/panels", json={
        "report_id": report["report_id"],
        "persona_id": report["personas"][0]["persona_id"],
        "member_count": 2,
    }), 201)


def advance(client, case_path, index):
    return client.post(case_path + "/advance", json={"expected_index": index})


def test_confirmed_persona_uses_the_configured_skill_and_blind_ab_pairs_resume(tmp_path):
    provider = RecordingProvider()
    skill = tmp_path / "SKILL.md"
    skill.write_text("Use purchase occasions to vary the attention budget.", encoding="utf-8")
    database = tmp_path / "jury.sqlite3"
    app = create_app(database_path=database, provider=provider, skill_path=skill)

    with TestClient(app) as client:
        panel = prepare_panel(client)
        assert panel["theories"][0]["theory_id"] == "team_skill"
        assert panel["base_persona"]["name"] == "通勤补水者"
        assert len({m["member_id"] for m in panel["members"]}) == 2
        assert set(panel["members"][0]["sampled_values"]) >= {"通勤携带优先项", "清洁偏好"}
        dimension_system, dimension_user = provider.native_calls[0]
        description = _factory_arguments(dimension_user)["sampling_space_description"]
        assert "Given a sampling description" in dimension_system
        assert skill.read_text() in description
        assert REPORT in description
        assert skill.read_text() not in dimension_system
        assert all(
            skill.read_text() in user
            for _, user in provider.native_calls
            if "# Agent Generator" in user
        )
        case = get_json(client.post("/api/jury/comparisons", json={
            "panel_id": panel["panel_id"], "original_text": BEFORE, "revised_text": AFTER,
        }), 201)
        path = f"/api/jury/comparisons/{case['comparison_id']}"
        first = get_json(advance(client, path, 0))
        assert first["next_index"] == 1

    with TestClient(create_app(database_path=database, provider=provider, skill_path=skill)) as client:
        assert get_json(client.get(path)) == first
        assert get_json(advance(client, path, 0)) == first
        assert advance(client, path, 2).status_code == 409
        for index in range(1, 4):
            result = get_json(advance(client, path, index))
        assert result["next_index"] is None
        assert result["vote_counts"]["A"]["unsure"] == 2
        assert result["vote_counts"]["B"]["would_consider"] == 2
        assert result["metric_changes"]["trust"] == {"higher": 2, "same": 0, "lower": 0}
        assert len(result["pairs"]) == 2

    reactions = [context for step, context in provider.calls if step == "jury_reaction"]
    assert len(reactions) == 4
    assert {frozenset(context) for context in reactions} == {
        frozenset({"base_persona", "member", "ad_copy"})
    }
    names = [member["specification"]["persona"]["name"] for member in panel["members"]]
    assert [(c["member"]["name"], c["ad_copy"]) for c in reactions] == [
        (names[0], BEFORE), (names[0], AFTER), (names[1], AFTER), (names[1], BEFORE),
    ]
    assert reactions[0]["member"] == reactions[1]["member"]
    assert reactions[2]["member"] == reactions[3]["member"]


def test_report_with_no_persona_uses_same_original_prompt_with_optional_skill(tmp_path):
    provider = RecordingProvider()
    provider.has_explicit_persona = False
    database = tmp_path / "jury.db"
    skill = tmp_path / "SKILL.md"
    skill.write_text("用营销理论考察消费者会先核对哪类环保依据。", encoding="utf-8")
    with TestClient(create_app(database_path=database, provider=provider)) as client:
        report = get_json(upload(client), 201)
        assert report["personas"] == []
        request = {"report_id": report["report_id"], "member_count": 2}
        bare = get_json(client.post("/api/jury/panels", json=request), 201)

    with TestClient(create_app(database_path=database, provider=provider, skill_path=skill)) as client:
        skilled = get_json(client.post("/api/jury/panels", json=request), 201)

    dimensions = [(system, user) for system, user in provider.native_calls if "Given a sampling description" in system]
    assert len(dimensions) == 2
    assert dimensions[0][0] == dimensions[1][0]
    assert REPORT in _factory_arguments(dimensions[0][1])["sampling_space_description"]
    enriched = _factory_arguments(dimensions[1][1])["sampling_space_description"]
    assert REPORT in enriched and skill.read_text(encoding="utf-8") in enriched
    assert bare["theories"] == [] and skilled["theories"][0]["theory_id"] == "team_skill"
    for panel in (bare, skilled):
        assert panel["base_persona"] is None
        assert all(seat["specification"]["type"] == "TinyPerson" for seat in panel["members"])


def test_saved_legacy_members_can_finish_an_ab_comparison(tmp_path):
    provider = RecordingProvider()
    database = tmp_path / "jury.db"
    panel_id = str(uuid4())
    member_id = str(uuid4())
    with TestClient(create_app(database_path=database, provider=provider)) as client:
        report = get_json(upload(client), 201)
        legacy = {
            "panel_id": panel_id, "report_id": report["report_id"], "mode": "live", "model": provider.model,
            "base_persona": report["personas"][0], "theories": [],
            "members": [{
                "member_id": member_id, "name": "旧面板角色", "persona_prompt": "重视价格。",
                "situation": "上班路上", "assumptions": ["赶着去办公室"], "theory_ids": ["jtbd"],
            }],
        }
        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO jury_records (kind, id, body) VALUES ('panel', ?, ?)",
                (panel_id, json.dumps(legacy, ensure_ascii=False)),
            )
        comparison = get_json(client.post("/api/jury/comparisons", json={
            "panel_id": panel_id, "original_text": BEFORE, "revised_text": AFTER,
        }), 201)
        path = "/api/jury/comparisons/" + comparison["comparison_id"]
        assert get_json(advance(client, path, 0))["next_index"] == 1

    with TestClient(create_app(database_path=database, provider=provider)) as client:
        result = get_json(advance(client, path, 1))
        assert result["next_index"] is None
        assert result["pairs"][0]["member_name"] == "旧面板角色"
    assert provider.calls[-2][1]["member"] == provider.calls[-1][1]["member"]
    assert provider.calls[-1][1]["member"]["persona_prompt"] == "重视价格。"


def test_a_claimed_source_must_exist_in_the_uploaded_report(tmp_path):
    provider = RecordingProvider()
    provider.found_quote = "不存在于报告的引文"
    app = create_app(database_path=tmp_path / "jury.sqlite3", provider=provider)
    with TestClient(app) as client:
        assert upload(client).status_code == 502


@pytest.mark.parametrize("fault", ["count", "malformed", "missing_dimension"])
def test_invalid_tinytroupe_plan_stops_before_creating_personas(tmp_path, fault):
    provider = RecordingProvider()
    provider.invalid_plan = fault
    app = create_app(database_path=tmp_path / "jury.sqlite3", provider=provider)
    with TestClient(app) as client:
        report = get_json(upload(client), 201)
        response = client.post("/api/jury/panels", json={
            "report_id": report["report_id"],
            "persona_id": report["personas"][0]["persona_id"],
            "member_count": 2,
        })
        assert response.status_code == 502
    assert not any("# Agent Generator" in user for _, user in provider.native_calls)
    assert not any("Generates a single full name" in system for system, _ in provider.native_calls)


def test_model_error_in_explicit_sampling_is_retryable(tmp_path):
    provider = RecordingProvider()
    provider.fail_native_person = True
    app = create_app(database_path=tmp_path / "jury.db", provider=provider)
    with TestClient(app) as client:
        report = get_json(upload(client), 201)
        response = client.post("/api/jury/panels", json={
            "report_id": report["report_id"],
            "member_count": 1,
            "sampling": {"mode": "random", "space": {"dimensions": [
                {"name": "接触场景", "kind": "exposure", "values": ["地铁", "手机"]},
            ]}},
        })
        assert response.status_code == 502


def test_docx_table_text_can_ground_a_profile(tmp_path):
    document = Document()
    document.add_paragraph("水杯调研")
    document.add_table(rows=1, cols=1).cell(0, 0).text = REPORT
    buffer = BytesIO()
    document.save(buffer)
    app = create_app(database_path=tmp_path / "jury.sqlite3", provider=RecordingProvider())
    with TestClient(app) as client:
        result = get_json(upload(client, content=buffer.getvalue(), filename="sample.docx"), 201)
        assert result["personas"][0]["traits"][0]["value"] == "预算较紧"
        assert upload(client, content=b"image data", filename="scanned.png").status_code == 415


def test_demo_fixture_runs_without_a_key_and_rejects_arbitrary_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JURY_MODE", "demo")
    app = create_app(database_path=tmp_path / "jury.sqlite3")
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert upload(client).status_code == 409
        sample = get_json(client.get("/api/jury/demo"))
        report = get_json(upload(client, content=sample["report_text"].encode()), 201)
        assert report["mode"] == "demo"
        panel = get_json(client.post("/api/jury/panels", json={
            "report_id": report["report_id"], "persona_id": report["personas"][0]["persona_id"],
            "member_count": 2,
        }), 201)
        request = {
            "panel_id": panel["panel_id"],
            "original_text": sample["original_text"],
            "revised_text": sample["revised_text"],
        }
        assert client.post("/api/jury/comparisons", json={**request, "revised_text": "Other ad"}).status_code == 409
        comparison = get_json(client.post("/api/jury/comparisons", json=request), 201)
        path = f"/api/jury/comparisons/{comparison['comparison_id']}"
        for index in range(4):
            result = get_json(advance(client, path, index))
        assert result["mode"] == "demo"
        assert len(result["pairs"]) == 2


def test_extracts_the_text_layer_of_a_research_pdf():
    pdf = PdfWriter()
    page = pdf.add_blank_page(width=200, height=200)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
    })
    contents = DecodedStreamObject()
    contents.set_data(b"BT /F1 12 Tf 15 150 Td (Commuters compare prices) Tj ET")
    page.replace_contents(contents)
    buffer = BytesIO()
    pdf.write(buffer)
    assert read_report("research.pdf", buffer.getvalue()) == "Commuters compare prices"


def test_live_mode_uses_the_standalone_model_config(tmp_path, monkeypatch):
    key_file = tmp_path / "test-key.txt"
    key_file.write_text("test-only-key\n", encoding="utf-8")
    monkeypatch.setenv("JURY_MODE", "live")
    monkeypatch.setenv("JURY_DEEPSEEK_MODEL", "test-jury-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY_FILE", str(key_file))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(create_app(database_path=tmp_path / "jury.sqlite3")) as client:
        settings = get_json(client.get("/api/jury/demo"))
        assert (settings["mode"], settings["model"]) == ("live", "test-jury-model")
