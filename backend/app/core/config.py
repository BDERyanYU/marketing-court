import os
from pathlib import Path

from ..court.demo import DemoProvider
from .llm import ModelProvider
from .model_api import configured_provider


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def database_path_from_env() -> Path:
    default = PROJECT_ROOT / "data" / "marketing_court.sqlite3"
    return Path(os.environ.get("DATABASE_PATH", os.environ.get("COURT_DB_PATH", str(default)))).expanduser()


def provider_from_env() -> ModelProvider:
    return configured_provider(DemoProvider, mode_variable="COURT_MODE", model_variable="COURT_DEEPSEEK_MODEL")
