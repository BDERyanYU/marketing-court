from fastapi.testclient import TestClient

from backend.app.court.config import provider_from_env as court_provider_from_env
from backend.app.jury.main import provider_from_env as jury_provider_from_env
from backend.app.main import create_app
from backend.app.core.model_api import DeepSeekProvider


def test_court_and_jury_run_on_the_same_application(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETING_COURT_MODE", "demo")
    monkeypatch.setenv("JURY_MAX_CONCURRENT_MEMBERS", "1")
    app = create_app(
        court_database_path=tmp_path / "court.db",
        jury_database_path=tmp_path / "jury.db",
    )
    with TestClient(app) as client:
        assert client.get("/health").raise_for_status().json() == {"status": "ok"}
        home = client.get("/").raise_for_status().text
        assert 'href="/jury"' in home and 'href="/docs"' in home
        assert client.get("/jury").raise_for_status().status_code == 200
        paths = client.get("/openapi.json").raise_for_status().json()["paths"]
        assert "/api/risks/{risk_id}/appeals" in paths
        assert "/api/jury/comparisons" in paths
        assert "/api/jury/comparisons/{comparison_id}/advance-members" in paths

        case = client.post("/api/risks/demo-eco-bottle/appeals").raise_for_status().json()
        case_path = f"/api/cases/{case['case_id']}"
        for _ in range(5):
            case = client.post(case_path + "/advance", json={
                "expected_step": case["next_step"],
            }).raise_for_status().json()
        assert len(case["turns"]) == 4 and case["judgment"] is not None

        sample = client.get("/api/jury/demo").raise_for_status().json()
        report = client.post("/api/jury/reports", files={
            "file": ("research.txt", sample["report_text"].encode()),
        }).raise_for_status().json()
        panel = client.post("/api/jury/panels", json={
            "report_id": report["report_id"],
            "persona_id": report["personas"][0]["persona_id"],
        }).raise_for_status().json()
        comparison = client.post("/api/jury/comparisons", json={
            "panel_id": panel["panel_id"],
            "original_text": sample["original_text"],
            "revised_text": sample["revised_text"],
        }).raise_for_status().json()
        comparison_path = f"/api/jury/comparisons/{comparison['comparison_id']}"
        for index in range(0, 6, 2):
            comparison = client.post(comparison_path + "/advance-members", json={
                "expected_index": index,
            }).raise_for_status().json()
            assert len(comparison["exposures"]) == index + 2
        assert comparison["next_index"] is None and len(comparison["pairs"]) == 3


def test_both_features_use_one_model_adapter_and_product_configuration(tmp_path, monkeypatch):
    key_file = tmp_path / "key.txt"
    key_file.write_text("test-only-key\n", encoding="utf-8")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY_FILE", str(key_file))
    monkeypatch.setenv("MARKETING_COURT_MODE", "live")
    monkeypatch.setenv("MARKETING_COURT_DEEPSEEK_MODEL", "shared-test-model")
    monkeypatch.setenv("COURT_MODE", "demo")
    monkeypatch.setenv("JURY_MODE", "demo")

    court = court_provider_from_env()
    jury = jury_provider_from_env()
    assert type(court) is type(jury) is DeepSeekProvider
    assert court.mode == jury.mode == "live"
    assert court.model == jury.model == "shared-test-model"
