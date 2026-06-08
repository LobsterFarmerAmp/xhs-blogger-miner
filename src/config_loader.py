from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOGGERS_CONFIG = PROJECT_ROOT / "config" / "bloggers.yaml"
SETTINGS_MODULE_PATH = PROJECT_ROOT / "config" / "settings.py"


def load_settings(env_file: str | Path | None = None) -> Any:
    spec = importlib.util.spec_from_file_location(
        "_xhs_blogger_miner_settings",
        SETTINGS_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load settings from {SETTINGS_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.Settings.from_env(env_file)


def load_bloggers_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_BLOGGERS_CONFIG
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    validate_and_normalize_bloggers_config(data)
    return data


def validate_and_normalize_bloggers_config(data: dict[str, Any]) -> None:
    bloggers = data.get("bloggers")
    if not isinstance(bloggers, list) or not bloggers:
        raise ValueError("Config must contain a non-empty 'bloggers' list")
    for item in bloggers:
        if not isinstance(item, dict):
            raise ValueError("Each blogger entry must be a mapping")
        if not item.get("user_id") and not item.get("homepage_url"):
            raise ValueError("Each blogger must define user_id or homepage_url")
        notes = item.setdefault("notes", {})
        if notes.get("max_count") is not None and int(notes["max_count"]) < 1:
            raise ValueError("notes.max_count must be greater than 0")
