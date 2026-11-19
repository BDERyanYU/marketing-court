"""Opt-in real PaddleOCR with controlled text model; no paid model requests."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from test_review_api import Provider


@pytest.mark.skipif(os.environ.get("RUN_PADDLE_OCR") != "1", reason="Opt-in real local OCR and model download")
def test_real_image_localization_and_rewrite(tmp_path):
    image = Path(__file__).resolve().parents[1] / "examples" / "eco-bottle.png"
    with TestClient(create_app(database_path=tmp_path / "app.sqlite3", provider=Provider())) as client:
        project = client.post("/api/projects", json={"name": "Real OCR integration"}).json()
        asset = client.post(f'/api/projects/{project["project_id"]}/assets',
                            files={"file": (image.name, image.read_bytes(), "image/png")}).json()
        task = client.post(f'/api/assets/{asset["asset_version_id"]}/reviews').json()
        saved = client.get(f'/api/tasks/{task["task_id"]}').json()
        assert saved["status"] == "completed", saved
        review = client.get(f'/api/reviews/{saved["result_id"]}').json()
        risk = review["risks"][0]
        assert risk["location_status"] == "located"
        assert len(risk["anchor_ids"]) == 1
        anchor = next(a for a in review["anchors"] if a["anchor_id"] == risk["anchor_ids"][0])
        assert "100% Eco-Friendly" in anchor["text"]
        assert anchor["method"] == "paddleocr"
        assert all(.1 < y < .25 for x,y in anchor["polygon"])
        rewrite = client.post(f'/api/reviews/{review["review_id"]}/risks/{risk["risk_id"]}/rewrite').json()
        assert client.get(f'/api/tasks/{rewrite["task_id"]}').json()["status"] == "completed"
