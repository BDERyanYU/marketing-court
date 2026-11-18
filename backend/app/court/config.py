import os
from pathlib import Path

from ..core.model_api import ModelProvider, configured_provider
from ..core.paths import PROJECT_ROOT

from .demo import DemoProvider


def database_path_from_env() -> Path:
    default = PROJECT_ROOT / "var" / "court.sqlite3"
    return Path(os.environ.get("COURT_DB_PATH", str(default))).expanduser()


def provider_from_env() -> ModelProvider:
    return configured_provider(
        DemoProvider, mode_variable="COURT_MODE", model_variable="COURT_DEEPSEEK_MODEL",
    )
