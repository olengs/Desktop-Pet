from __future__ import annotations

import os
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name(".config")
ENV_PATH = Path(__file__).with_name(".env")
TRUTHY = {"1", "true", "yes", "on"}

_CONFIG_VALUES: dict[str, str] | None = None


def config_value(key: str, default: str = "") -> str:
    return os.getenv(key) or _config_values().get(key, default)


def config_bool(key: str, default: bool = False) -> bool:
    fallback = "1" if default else ""
    return config_value(key, fallback).strip().lower() in TRUTHY


def config_int(key: str, default: int) -> int:
    try:
        return int(config_value(key, str(default)))
    except ValueError:
        return default


def config_float(key: str, default: float) -> float:
    try:
        return float(config_value(key, str(default)))
    except ValueError:
        return default


def _config_values() -> dict[str, str]:
    global _CONFIG_VALUES
    if _CONFIG_VALUES is None:
        _CONFIG_VALUES = _read_key_value_file(CONFIG_PATH)
    return _CONFIG_VALUES


def _read_key_value_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values

