"""Exercise the real provider adapter and task checkpoints through the API."""
import json

import httpx
from fastapi.testclient import TestClient

from backend.app.core.model_api import DeepSeekProvider
from backend.app.core.store import Store
from backend.app.main import create_app
from tests.test_review_api import OCR, uploaded


def test_network_failure_resumes_without_repeating_saved_model_or_ocr_steps(tmp_path, monkeypatch):
    calls = []
    offline = True
    monkeypatch.setattr("backend.app.core.model_api.time.sleep", lambda _: None)

    def answer(request):
        step = json.loads(json.loads(request.content)["messages"][1]["content"])["step"]
        calls.append(step)
        if step == "risk_assessment" and offline:
            raise httpx.RemoteProtocolError("test-only-key", request=request)
        result = ({"claims": [{"claim_text": "100% Eco-Friendly", "claim_type": "environmental"}]}
                  if step == "claim_extraction" else
                  dict(assessment="requires_substantiation", severity="high", reason="需要产品证明。",
                       source_ids=["G1"], evidence_gaps=["产品材料与范围"]))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(result)}}]})

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    database = tmp_path / "app.db"
    ocr = OCR()
    with TestClient(create_app(database_path=database, provider=provider, ocr=ocr)) as client:
        asset = uploaded(client)
        task = client.post(f'/api/assets/{asset["asset_version_id"]}/reviews').json()
        endpoint = f'/api/tasks/{task["task_id"]}'
        failed = client.get(endpoint).json()
        assert failed["status"] == "failed" and failed["stage"] == "assessing_risks"
        assert failed["error_code"] == "deepseek_connection_interrupted" and failed["retryable"]
        assert "test-only-key" not in failed["error"]
        assert calls == ["claim_extraction"] + ["risk_assessment"] * 3
        checkpoints = Store(database).task(task["task_id"]).checkpoints
        assert checkpoints["claims"] and checkpoints["anchors"]

    offline = False
    with TestClient(create_app(database_path=database, provider=provider, ocr=ocr)) as client:
        assert client.post(endpoint + "/retry").status_code == 202
        done = client.get(endpoint).json()
        assert done["status"] == "completed" and done["error"] is None
        assert done["error_code"] is None and not done["retryable"]
        review = client.get(f'/api/reviews/{done["result_id"]}').json()
        assert review["risks"][0]["source_ids"] == ["G1"]
        assert ocr.calls == 1 and calls.count("claim_extraction") == 1
        assert review["claims"][0]["claim_id"] == checkpoints["claims"][0]["claim_id"]
        assert client.post(endpoint + "/retry").status_code == 409
