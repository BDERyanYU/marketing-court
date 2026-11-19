import os
from pathlib import Path

from ..court.demo import DemoProvider
from .llm import DEFAULT_DEEPSEEK_MODEL, DeepSeekProvider, ModelProvider


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def database_path_from_env() -> Path:
    default = PROJECT_ROOT / "data" / "marketing_court.sqlite3"
    return Path(os.environ.get("COURT_DB_PATH", str(default))).expanduser()


def provider_from_env() -> ModelProvider:
    mode = os.environ.get("COURT_MODE", "demo")
    if mode == "demo":
        return DemoProvider()
    if mode != "live":
        raise RuntimeError("COURT_MODE must be demo or live.")

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    key_file = os.environ.get("DEEPSEEK_API_KEY_FILE", "")
    if not api_key and key_file:
        try:
            api_key = Path(key_file).expanduser().read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            raise RuntimeError("Could not read DEEPSEEK_API_KEY_FILE.") from None
    if not api_key or any(character.isspace() for character in api_key):
        raise RuntimeError("Live mode requires one DeepSeek API key in DEEPSEEK_API_KEY or DEEPSEEK_API_KEY_FILE.")

    model = os.environ.get("COURT_DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip()
    if not model:
        raise RuntimeError("COURT_DEEPSEEK_MODEL must contain a model ID.")
    return DeepSeekProvider(api_key=api_key, model=model)
