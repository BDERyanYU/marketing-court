from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.core.store import Store
from backend.app.main import create_app
from backend.app.models.review import ExtractedClaim, TextAnchor
from backend.app.services.claims import map_claim


class OCR:
    calls = 0

    def extract(self, path, width, height):
        self.calls += 1
        return [TextAnchor(anchor_id="a1", text="100% Eco-Friendly.",
                    polygon=[(.1,.1),(.8,.1),(.8,.2),(.1,.2)], score=.99, method="paddleocr"),
                TextAnchor(anchor_id="a2", text="Meet the Everyday Bottle.",
                    polygon=[(.1,.3),(.9,.3),(.9,.4),(.1,.4)], score=.99, method="paddleocr")]


class Provider:
    mode = "live"
    model = "test-model"

    def __init__(self):
        self.source = "G1"
        self.claim = "100% Eco-Friendly"
        self.calls = []

    def complete(self, *, step, instruction, context, output):
        self.calls.append(step)
        if step == "claim_extraction":
            text = context["original_text"]
            return output.model_validate({"claims": ([{"claim_text": self.claim, "claim_type": "environmental"}]
                                                       if "Eco-Friendly" in text else [])})
        if step == "risk_assessment":
            return output.model_validate(dict(assessment="requires_substantiation", severity="high",
                reason="The broad claim needs matching evidence.", source_ids=[self.source],
                evidence_gaps=["Product-wide evidence"]))
        raise AssertionError(f"Unexpected model step: {step}")


def png():
    buffer = BytesIO()
    Image.new("RGB", (800, 900), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def uploaded(client):
    project = client.post("/api/projects", json={"name": "Campaign"}).json()
    response = client.post(f'/api/projects/{project["project_id"]}/assets',
                           files={"file": ("advert.png", png(), "image/png")})
    assert response.status_code == 201, response.text
    return response.json()


def reviewed(client):
    asset = uploaded(client)
    task = client.post(f'/api/assets/{asset["asset_version_id"]}/reviews').json()
    result = client.get(f'/api/tasks/{task["task_id"]}').json()
    assert result["status"] == "completed", result
    assert "checkpoints" not in result
    return client.get(f'/api/reviews/{result["result_id"]}').json(), task


def test_image_review_rewrite_and_export_survive_restart(tmp_path):
    database = tmp_path / "app.sqlite3"
    provider = Provider()
    with TestClient(create_app(database_path=database, provider=provider, ocr=OCR())) as client:
        original, task = reviewed(client)
        risk = original["risks"][0]
        assert risk["location_status"] == "located"
        assert risk["anchor_ids"] == ["a1"]
        assert original["sources"][0]["content_hash"]
        repeated = client.post(f'/api/assets/{original["asset_version_id"]}/reviews').json()
        assert repeated["task_id"] == task["task_id"]
        assert provider.calls.count("claim_extraction") == 1

        rewrite_path = f'/api/reviews/{original["review_id"]}/risks/{risk["risk_id"]}/rewrite'
        rewrite_task = client.post(rewrite_path).json()
        done = client.get(f'/api/tasks/{rewrite_task["task_id"]}').json()
        assert done["status"] == "completed", done
        rewrite = client.get(f'/api/rewrites/{done["result_id"]}').json()
        assert rewrite["revised_text"] == "Meet the Everyday Bottle."
        recheck = client.get(f'/api/reviews/{rewrite["review_id"]}').json()
        assert not recheck["risks"]
        assert rewrite["asset_version_id"] != original["asset_version_id"]
        assert client.post(rewrite_path).json()["task_id"] == rewrite_task["task_id"]
        assert client.get(f'/api/reviews/{original["review_id"]}').json() == original

    with TestClient(create_app(database_path=database, provider=provider, ocr=OCR())) as client:
        report = client.get(f'/api/reviews/{original["review_id"]}/report')
        assert "attachment" in report.headers["content-disposition"]
        assert "court_cases" not in report.json()
        assert report.json()["rewrites"][0]["recheck"]["risks"] == []
        assert "storage_name" not in report.json()["asset"]


def test_invalid_citation_can_retry_without_repeating_ocr(tmp_path):
    provider, ocr = Provider(), OCR()
    provider.source = "made-up"
    with TestClient(create_app(database_path=tmp_path / "app.db", provider=provider, ocr=ocr)) as client:
        asset = uploaded(client)
        task = client.post(f'/api/assets/{asset["asset_version_id"]}/reviews').json()
        endpoint = f'/api/tasks/{task["task_id"]}'
        failed = client.get(endpoint).json()
        assert failed["status"] == "failed"
        assert client.get(f'/api/projects/{asset["project_id"]}/reviews').json() == []
        provider.source = "G1"
        assert client.post(endpoint + "/retry").status_code == 202
        assert client.get(endpoint).json()["status"] == "completed"
        assert ocr.calls == 1
        assert provider.calls.count("claim_extraction") == 1
        assert client.post(endpoint + "/retry").status_code == 409


def test_restart_marks_running_tasks_interrupted(tmp_path):
    path = tmp_path / "app.db"
    store = Store(path)
    task, _ = store.start_task("review", "asset-missing", "live", "test-model")
    task.status = "running"
    task.checkpoints = {"anchors": []}
    store.save_task(task)
    with TestClient(create_app(database_path=path, provider=Provider())) as client:
        restored = client.get(f'/api/tasks/{task.task_id}').json()
        assert restored["status"] == "interrupted"
        assert store.task(task.task_id).checkpoints == {"anchors": []}


def test_fabricated_claim_is_rejected(tmp_path):
    provider = Provider()
    provider.claim = "Not in the actual image"
    with TestClient(create_app(database_path=tmp_path / "app.db", provider=provider, ocr=OCR())) as client:
        asset = uploaded(client)
        task = client.post(f'/api/assets/{asset["asset_version_id"]}/reviews').json()
        assert client.get(f'/api/tasks/{task["task_id"]}').json()["status"] == "failed"


@pytest.mark.parametrize("content,mime,status", [(b'not an image', "image/png",415),
    (b'MZ' + b'0' * 100, "application/octet-stream",415), (b'x' * (10*1024*1024+1),"image/png",413)])
def test_upload_validation(tmp_path, content, mime, status):
    with TestClient(create_app(database_path=tmp_path / "app.db", provider=Provider())) as client:
        project = client.post("/api/projects",json={"name":"Upload"}).json()
        response = client.post(f'/api/projects/{project["project_id"]}/assets', files={"file":("x.png",content,mime)})
        assert response.status_code == status


def test_demo_is_separate_and_supports_fixed_rewrite(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "app.db")) as client:
        demo = client.post("/api/demo").json()
        assert demo["mode"] == "demo"
        assert demo["anchors"][0]["method"] == "fixture"
        assert client.get(f'/api/assets/{demo["asset_version_id"]}/image').status_code == 200
        asset = uploaded(client)
        assert client.post(f'/api/assets/{asset["asset_version_id"]}/reviews').status_code == 409
        task = client.post(f'/api/reviews/{demo["review_id"]}/risks/demo-eco-bottle/rewrite').json()
        result = client.get(f'/api/tasks/{task["task_id"]}').json()
        assert result["status"] == "completed", result


def test_multiline_normalized_anchor_mapping_and_unmatched_fallback():
    anchors = [TextAnchor(anchor_id=str(i), text=t, polygon=[(0,0),(1,0),(1,1),(0,1)],score=.9,method="paddleocr")
               for i,t in enumerate(["100%", "Eco-Friendly", "Meet the Everyday Bottle."])]
    mapped = map_claim(ExtractedClaim(claim_text="100% Eco-Friendly", claim_type="environmental"),anchors)
    assert mapped.anchor_ids == ["0","1"]
    unmatched = map_claim(ExtractedClaim(claim_text="Unrecognized text",claim_type="environmental"),anchors)
    assert unmatched.location_status == "needs_confirmation"
    assert unmatched.anchor_ids == []
    exact = map_claim(ExtractedClaim(claim_text="Eco-Friendly",claim_type="environmental"),anchors)
    assert exact.anchor_ids == ["1"]
    anchors[1].score = .6
    uncertain = map_claim(ExtractedClaim(claim_text="Eco-Friendly",claim_type="environmental"),anchors)
    assert uncertain.location_status == "needs_confirmation"
