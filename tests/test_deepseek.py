import json

import httpx
import pytest

from backend.app.core.config import provider_from_env
from backend.app.core.llm import DeepSeekProvider, ModelError
from pydantic import BaseModel


class ProbeOutput(BaseModel):
    position: str
    argument: str
    source_ids: list[str]
    responds_to: str | None
    evidence_requested: list[str]


def complete_probe(provider):
    return provider.complete(
        step="structured_probe",
        instruction="Return a structured result.",
        context={"input": {"original_text": "100% Eco-Friendly"}},
        output=ProbeOutput,
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
        assert case_context["step"] == "structured_probe"
        assert case_context["input"]["original_text"] == "100% Eco-Friendly"
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
    assert complete_probe(provider).source_ids == ["G1"]


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
        max_attempts=1,
    )
    with pytest.raises(ModelError) as error:
        complete_probe(provider)
    assert "test-only-key" not in str(error.value)


def turn_response():
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
        "content": json.dumps(dict(position="maintain", argument="Evidence is required.",
                                  source_ids=["G1"], responds_to=None, evidence_requested=[]))}}]})


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.ConnectTimeout,
    httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError])
def test_transient_transport_failure_recovers_with_bounded_backoff(failure, monkeypatch, caplog):
    delays, calls = [], []
    monkeypatch.setattr("backend.app.core.model_api.time.sleep", delays.append)

    def answer(request):
        calls.append(request)
        assert request.extensions["timeout"]["connect"] == 15
        assert request.extensions["timeout"]["read"] == 90
        if len(calls) < 3:
            raise failure("test-only-key private payload", request=request)
        return turn_response()

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    assert complete_probe(provider).source_ids == ["G1"]
    assert len(calls) == 3 and delays == [1, 2]
    assert len({r.content for r in calls}) == 1
    assert "test-only-key" not in caplog.text and "private payload" not in caplog.text


@pytest.mark.parametrize(("failure", "code"), [
    (httpx.ReadTimeout, "deepseek_read_timeout"),
    (httpx.ConnectTimeout, "deepseek_connect_timeout"),
    (httpx.ConnectError, "deepseek_connection_error"),
    (httpx.RemoteProtocolError, "deepseek_connection_interrupted"),
])
def test_exhausted_transport_failure_has_safe_actionable_reason(failure, code, monkeypatch):
    calls = []
    monkeypatch.setattr("backend.app.core.model_api.time.sleep", lambda _: None)

    def answer(request):
        calls.append(request)
        raise failure("test-only-key", request=request)

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    with pytest.raises(ModelError) as error:
        complete_probe(provider)
    assert len(calls) == 3
    assert error.value.code == code and error.value.retryable
    assert "重试" in str(error.value) and "test-only-key" not in str(error.value)


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_http_failure_recovers(status, monkeypatch):
    delays, calls = [], []
    monkeypatch.setattr("backend.app.core.model_api.time.sleep", delays.append)

    def answer(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, headers={"Retry-After": "2"}, json={"error": "test-only-key"})
        return turn_response()

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    assert complete_probe(provider).source_ids == ["G1"]
    assert len(calls) == 2 and delays == [2]


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 422])
def test_configuration_or_account_failure_is_not_automatically_retried(status):
    calls = []

    def answer(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "test-only-key"})

    with pytest.raises(ModelError) as error:
        complete_probe(DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer)))
    assert len(calls) == 1 and not error.value.retryable
    assert error.value.code == f"deepseek_http_{status}"
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


def test_native_chat_preserves_messages_budget_and_review_recovery(monkeypatch):
    calls = []
    messages = [{"role": "system", "content": "Generate JSON."},
                {"role": "user", "content": "Native persona input"}]
    monkeypatch.setattr("backend.app.core.model_api.time.sleep", lambda _: None)

    def answer(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["messages"] == messages
        assert payload["max_tokens"] == 8192 and payload["temperature"] == 0.6
        assert payload["response_format"] == {"type": "json_object"}
        if len(calls) == 1:
            raise httpx.RemoteProtocolError("private upstream body", request=request)
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": '{"name":"Example"}'}}]})

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    assert json.loads(provider.chat(messages, max_tokens=8192, temperature=0.6)["content"]) == {"name": "Example"}
    assert len(calls) == 2


def test_review_retains_large_output_budget_after_native_chat_integration():
    from backend.app.models.review import ClaimExtraction

    def answer(request):
        assert json.loads(request.content)["max_tokens"] >= 2400
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": '{"claims":[]}'}}]})

    provider = DeepSeekProvider("test-only-key", transport=httpx.MockTransport(answer))
    assert provider.complete(step="claim_extraction", instruction="Extract exact claims.",
                             context={"original_text": "A bottle."}, output=ClaimExtraction).claims == []
