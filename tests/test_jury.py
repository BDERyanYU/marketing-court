from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
import pytest

from backend.app.jury.main import create_app
from backend.app.jury.parsing import read_report


REPORT = "通勤人群预算较紧，购买水杯主要为了减少上下班路上补水的不便。"
BEFORE = "100% Eco-Friendly. Meet the Everyday Bottle."
AFTER = "Meet the Everyday Bottle."


class RecordingProvider:
    mode = "live"
    model = "test-jury-model"

    def __init__(self):
        self.calls = []
        self.found_quote = "通勤人群预算较紧"
        self.theory_id = "team_skill"
        self.invalid_plan = None

    def complete(self, *, step, instruction, context, output):
        self.calls.append((step, context))
        if step == "jury_personas":
            data = {"personas": [{
                "name": "通勤补水者",
                "traits": [{
                    "attribute": "预算",
                    "value": "预算较紧",
                    "status": "grounded",
                    "source_quote": self.found_quote,
                }],
            }]}
        elif step == "jury_theory_selection":
            data = {"theory_ids": [self.theory_id]}
        elif step == "jury_tinytroupe_dimensions":
            assert "Given a sampling description" in instruction
            data = {
                "sampling_space_description": "购杯时所处的接触情境。",
                "dimensions": [
                    {"name": "接触情境", "kind": "exposure", "values": ["出门前", "到店后"]},
                ],
            }
        elif step == "jury_tinytroupe_plan":
            assert "Each *sampling directive* is a **combination**" in instruction
            data = {"sample_plan": [
                {
                    "id": index,
                    "subpopulation_description": f"{situation}留意水杯",
                    "sampled_values": {"接触情境": situation},
                    "quantity": 1,
                }
                for index, situation in enumerate(["出门前", "到店后"], start=1)
            ]}
            if self.invalid_plan == "count":
                data["sample_plan"][0]["quantity"] = 2
            if self.invalid_plan == "value":
                data["sample_plan"][0]["sampled_values"]["接触情境"] = "未定义的情境"
        elif step == "jury_tinytroupe_person":
            assert "# Agent Generator" in instruction
            situation = context["sampled_values"]["接触情境"]
            data = {
                "situation": f"{situation}留意水杯。",
                "persona_prompt": f"你是预算较紧的通勤者，{situation}看到文案。",
                "assumptions": [f"在{situation}看到文案。"],
            }
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


def upload(client, *, content=REPORT.encode(), filename="research.txt"):
    return client.post("/api/jury/reports", files={"file": (filename, content)})


def get_json(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def prepare_panel(client):
    report = get_json(upload(client), 201)
    assert report["personas"][0]["traits"][0]["source_quote"] == "通勤人群预算较紧"
    assert get_json(client.get("/api/jury/reports/" + report["report_id"])) == report
    return get_json(client.post("/api/jury/panels", json={
        "report_id": report["report_id"],
        "persona_id": report["personas"][0]["persona_id"],
        "member_count": 2,
    }), 201)


def advance(client, case_path, index):
    return client.post(case_path + "/advance", json={"expected_index": index})


def test_confirmed_persona_uses_a_selected_skill_and_blind_ab_pairs_resume(tmp_path):
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
        assert provider.calls[2][1]["theories"][0]["content"] == skill.read_text()
        assert "content" not in provider.calls[1][1]["available_theories"][0]
        assert [step for step, _ in provider.calls[2:]] == [
            "jury_tinytroupe_dimensions", "jury_tinytroupe_plan", "jury_tinytroupe_person", "jury_tinytroupe_person",
        ]
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
    assert [(c["member"]["name"], c["ad_copy"]) for c in reactions] == [
        ("模拟成员 1", BEFORE), ("模拟成员 1", AFTER), ("模拟成员 2", AFTER), ("模拟成员 2", BEFORE),
    ]
    assert reactions[0]["member"] == reactions[1]["member"]
    assert reactions[2]["member"] == reactions[3]["member"]


def test_a_claimed_source_must_exist_in_the_uploaded_report(tmp_path):
    provider = RecordingProvider()
    provider.found_quote = "不存在于报告的引文"
    app = create_app(database_path=tmp_path / "jury.sqlite3", provider=provider)
    with TestClient(app) as client:
        assert upload(client).status_code == 502


@pytest.mark.parametrize("fault", ["count", "value"])
def test_invalid_tinytroupe_plan_stops_before_creating_personas(tmp_path, fault):
    provider = RecordingProvider()
    provider.theory_id = "jtbd"
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
    assert [step for step, _ in provider.calls[-2:]] == ["jury_tinytroupe_dimensions", "jury_tinytroupe_plan"]


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
