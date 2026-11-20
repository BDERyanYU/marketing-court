"""Exercise credentials, service routing, shutdown and portable OCR boundaries."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_key_prompt_saved_locally_without_overwriting_dotenv(tmp_path, monkeypatch):
    launcher = load_script("launch")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY_FILE", raising=False)
    original = "DATABASE_PATH=./data/preserved.sqlite3\nCOURT_MODE=demo\n"
    (tmp_path / ".env").write_text(original)
    monkeypatch.setattr(launcher.getpass, "getpass", lambda _: "sk-test-only-placeholder")
    key, _ = launcher.read_key()
    assert key == "sk-test-only-placeholder"
    assert (tmp_path / "data/deepseek-api-key.txt").read_text().strip() == key
    assert (tmp_path / ".env").read_text() == original
    monkeypatch.setattr(launcher.getpass, "getpass", lambda _: pytest.fail("Prompt repeated"))
    assert launcher.read_key()[0] == key


def test_existing_key_file_and_environment_priority(tmp_path, monkeypatch):
    launcher = load_script("launch")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY_FILE", raising=False)
    (tmp_path / "saved.key").write_text("sk-file-placeholder")
    (tmp_path / ".env").write_text('DEEPSEEK_API_KEY_FILE="saved.key"\n')
    assert launcher.read_key()[0] == "sk-file-placeholder"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-placeholder")
    assert launcher.read_key()[0] == "sk-env-placeholder"


def test_local_server_serves_ui_and_api_together(tmp_path, monkeypatch):
    server = load_script("local_server")
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setenv("MARKETING_COURT_MODE", "demo")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "review.sqlite3"))
    monkeypatch.setenv("JURY_DB_PATH", str(tmp_path / "jury.sqlite3"))
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MARKETING_COURT_LAUNCH_ID", "test-instance")
    for name in ["index.html", "review/index.html", "jury/index.html", "landing-ads/sample.webp"]:
        path = tmp_path / "frontend/dist" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    with TestClient(server.create_local_app()) as client:
        pages = {
            "/": "index.html",
            "/index.html": "index.html",
            "/review": "review/index.html",
            "/review/": "review/index.html",
            "/review/index.html": "review/index.html",
            "/jury": "jury/index.html",
            "/jury/": "jury/index.html",
            "/jury/index.html": "jury/index.html",
        }
        for route, content in pages.items():
            response = client.get(route)
            assert response.text == content
            assert response.headers.get("cache-control") == "no-store"
        image = client.get("/landing-ads/sample.webp")
        assert image.text == "landing-ads/sample.webp"
        assert "cache-control" not in image.headers
        assert client.get("/health").json()["mode"] == "demo"
        assert client.get("/api/jury/demo").json()["mode"] == "demo"
        assert client.get("/__launcher/status").json()["instance"] == "test-instance"
        assert client.get("/api/projects").status_code == 200


def test_launcher_stops_child_and_clears_state(tmp_path, monkeypatch):
    launcher = load_script("launch")
    monkeypatch.setattr(launcher, "TOOLS", tmp_path)
    monkeypatch.setattr(launcher, "available_port", lambda: 5180)
    class Process:
        stopped = False
        def poll(self): return None if not self.stopped else 0
        def terminate(self): self.stopped = True
        def wait(self, **kwargs): return 0
    process = Process()
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(launcher, "request_json", lambda _: {"instance": "known"})
    monkeypatch.setattr(launcher.uuid, "uuid4", lambda: SimpleNamespace(hex="known"))
    monkeypatch.setattr(launcher.time, "sleep", lambda _: None)
    launcher.serve(Path(sys.executable), {}, no_browser=True, stop_after=1)
    assert process.stopped
    assert not (tmp_path / "running.json").exists()


def test_portable_ocr_uses_real_boxes_and_filters_bad_coordinates(monkeypatch):
    from backend.app.services.ocr import PortableOCRService, ocr_from_env
    result = SimpleNamespace(
        txts=["real claim", "bad box", "low score"], scores=[.95, .99, .1],
        boxes=[[(10, 20), (80, 20), (80, 40), (10, 40)], [(-1, 0)] * 4, [(0, 0)] * 4],
    )
    service = PortableOCRService()
    service._engine = lambda _: result
    anchors = service.extract(Path("sample.png"), 100, 200)
    assert len(anchors) == 1
    assert anchors[0].method == "rapidocr"
    assert anchors[0].polygon == [(0.1, .1), (.8, .1), (.8, .2), (.1, .2)]
    monkeypatch.setenv("MARKETING_COURT_OCR_ENGINE", "onnx")
    assert isinstance(ocr_from_env(), PortableOCRService)


def test_windows_unicode_paths_choose_portable_ocr(monkeypatch):
    launcher = load_script("launch")
    if launcher.os.name == "nt":
        monkeypatch.setattr(launcher, "ROOT", Path("C:/Users/中文/MarketingCourt"))
        assert launcher.needs_portable_ocr()
        monkeypatch.setattr(launcher, "ROOT", Path("C:/Users/demo/MarketingCourt"))
        assert not launcher.needs_portable_ocr()
