import json

import httpx
import pytest

from backend.app.court.config import provider_from_env
from backend.app.court.models import CourtStep, TurnOutput
from backend.app.core.model_api import DeepSeekProvider, ModelError


def complete_prosecution(provider):
    return provider.complete(
        step=CourtStep.PROSECUTION_1,
        instruction="Return the prosecution argument.",
        context={"case_facts": {"original_text": "100% Eco-Friendly"}},
        output=TurnOutput,
    )


def test_deepseek_sends_json_mode_and_parses_a_turn():
    def answer(request):
        assert request.method == "POST"
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-only-key"
        request_json = json.loads(request.content)
        assert request_json["model"] == "deepseek-flash"
        assert request_json["response_format"] == {"type": "json_object"}
        assert "JSON" in request_json["messages"][0]["content"]
        case_context = json.loads(request_json["messages"][1]["content"])
        assert case_context["step"] == "prosecution_1"
        assert case_context["case_facts"]["original_text"] == "100% Eco-Friendly"
        turn = {
            "position": "maintain",
            "argument": "The broad claim needs substantiation.",
            "source_ids": ["G1"],
            "responds_to": None,
            "evidence_requested": [],
        }
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(turn)}}],
        })

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    assert complete_prosecution(provider).source_ids == ["G1"]


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, {"choices": [{"finish_reason": "stop", "message": {"content": "  "}}]}),
        (200, {"choices": [{"finish_reason": "stop", "message": {"content": '{"position": "maintain"}'}}]}),
        (200, {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}),
        (429, {"error": {"message": "test-only-key"}}),
    ],
)
def test_deepseek_errors_are_retryable_without_exposing_provider_content(status, body):
    provider = DeepSeekProvider(
        "test-only-key",
        transport=httpx.MockTransport(lambda _request: httpx.Response(status, json=body)),
    )
    with pytest.raises(ModelError) as error:
        complete_prosecution(provider)
    assert "test-only-key" not in str(error.value)


def test_live_settings_read_the_key_file_and_reject_a_missing_key(tmp_path, monkeypatch):
    monkeypatch.setenv("COURT_MODE", "live")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY_FILE", raising=False)
    monkeypatch.delenv("COURT_DEEPSEEK_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="Live mode requires"):
        provider_from_env()

    key_file = tmp_path / "test-key.txt"
    key_file.write_text("test-only-key\n", encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY_FILE", str(key_file))
    provider = provider_from_env()
    assert provider.mode == "live"
    assert provider.model == "deepseek-flash"
