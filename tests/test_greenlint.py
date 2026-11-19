import pytest
from fastapi.testclient import TestClient

from backend.app.court.demo import DemoProvider
from backend.app.main import create_app
from backend.app.models.court import COURT_STEPS
from backend.app.services.greenlint import package
from tests.test_review_api import Provider


@pytest.mark.parametrize("case_id,market,count", [("apple-watch", "GB", 1), ("eco-dog-bed", "GB", 5), ("copier-paper", "EU", 0)])
def test_imported_cases_preserve_market_text_and_results(tmp_path, case_id, market, count):
    database = tmp_path / "cases.db"
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        examples = client.get("/api/demo-cases").json()
        assert len(examples) == 3
        assert [c["polarity"] for c in examples] == ["negative", "negative", "positive"]
        result = client.post(f"/api/demo-cases/{case_id}")
        assert result.status_code == 200, result.text
        review = result.json()
        assert review["example"]["market"] == market
        expected = next(c for c in package()[0]["cases"] if c["case_id"] == case_id)
        assert review["original_text"] == expected["original_text"]
        assert len(review["risks"]) == count
        assert all(r["severity"] == "high" and r["claim_quote"] in review["original_text"] for r in review["risks"])
        assert all(r["anchor_ids"] == [] and r["location_status"] == "needs_confirmation" for r in review["risks"])
        assert client.post(f"/api/demo-cases/{case_id}").json() == review
        asset = client.get(f'/api/assets/{review["asset_version_id"]}').json()
        assert asset["kind"] == "text" and not asset["image_url"] and not asset["width"]
        assert client.get(f'/api/assets/{review["asset_version_id"]}/image').status_code == 404
        project = next(p for p in client.get("/api/projects").json() if p["project_id"] == review["project_id"])
        assert project["market"] == market
        report = client.get(f'/api/reviews/{review["review_id"]}/report').json()
        assert report["review"]["example_rules"] == review["example_rules"]
        if case_id == "apple-watch":
            assert review["risks"][0]["demo_rule_ids"] == ["LR-003"]
            assert "Carbon Neutral" in review["risks"][0]["claim_quote"]
        if case_id == "eco-dog-bed":
            assert len(review["risks"][2]["demo_rule_ids"]) == 2
        if market == "EU":
            assert review["sources"] == []  # Never borrow UK sources for a positive EU example.
            assert "FSC N004130" in review["original_text"]
            assert "darker than conventional" in review["original_text"]
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        assert client.get(f'/api/reviews/{review["review_id"]}').json() == review


@pytest.mark.parametrize("case_id,count", [("apple-watch", 1), ("eco-dog-bed", 5)])
def test_each_negative_risk_supports_court_and_conservative_rewrite(tmp_path, case_id, count):
    database = tmp_path / "cases.db"
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        review = client.post(f"/api/demo-cases/{case_id}").json()
        for risk in review["risks"]:
            case = client.post(f'/api/risks/{risk["risk_id"]}/appeals')
            assert case.status_code == 201, case.text
            case = case.json()
            assert case["snapshot"]["market"] == "GB"
            assert {s["source_id"] for s in case["snapshot"]["citations"]} == {"G1", "G2"}
            assert client.post(f'/api/cases/{case["case_id"]}/advance', json={"expected_step": "judgment"}).status_code == 409
            for step in COURT_STEPS:
                response = client.post(f'/api/cases/{case["case_id"]}/advance', json={"expected_step": step})
                assert response.status_code == 200, response.text
            finished = response.json()
            assert len(finished["turns"]) == 4 and finished["judgment"]
            assert client.post(f'/api/cases/{case["case_id"]}/advance', json={"expected_step": "judgment"}).json() == finished
        risk = review["risks"][0]
        path = f'/api/reviews/{review["review_id"]}/risks/{risk["risk_id"]}/rewrite'
        task = client.post(path).json()
        task = client.get(f'/api/tasks/{task["task_id"]}').json()
        assert task["status"] == "completed", task
        rewrite = client.get(f'/api/rewrites/{task["result_id"]}').json()
        assert rewrite["removed_text"] == risk["claim_quote"]
        assert risk["claim_quote"] not in rewrite["revised_text"]
        recheck = client.get(f'/api/reviews/{rewrite["review_id"]}').json()
        assert len(recheck["risks"]) == count - 1
        assert not ({r["risk_id"] for r in review["risks"]} & {r["risk_id"] for r in recheck["risks"]})
        revised_asset = client.get(f'/api/assets/{rewrite["asset_version_id"]}').json()
        assert revised_asset["sha256"] != client.get(f'/api/assets/{review["asset_version_id"]}').json()["sha256"]
        assert client.get(f'/api/reviews/{review["review_id"]}').json() == review
        report = client.get(f'/api/reviews/{review["review_id"]}/report').json()
        assert len(report["court_cases"]) == count
        assert report["rewrites"][0]["recheck"] == recheck
    with TestClient(create_app(database_path=database, provider=DemoProvider())) as client:
        assert client.get(f'/api/cases/{case["case_id"]}').json() == finished


def test_examples_do_not_call_live_models(tmp_path):
    provider = Provider()
    with TestClient(create_app(database_path=tmp_path / "cases.db", provider=provider)) as client:
        review = client.post('/api/demo-cases/apple-watch').json()
        risk = review["risks"][0]
        result = client.post(f'/api/reviews/{review["review_id"]}/risks/{risk["risk_id"]}/rewrite').json()
        assert client.get(f'/api/tasks/{result["task_id"]}').json()["status"] == "completed"
        assert provider.calls == []
        assert client.post('/api/projects', json={"name": "EU project", "market": "EU"}).status_code == 201
        assert client.post('/api/demo-cases/missing').status_code == 404
        assert client.post('/api/demo').json()["review_id"] == "demo-review-1"
