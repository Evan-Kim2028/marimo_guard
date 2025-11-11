from __future__ import annotations

"""Config loading for marimo-guard defaults.

Supports a project-level TOML file and environment variable overrides.

Priority: CLI > env vars > config file > code defaults.
"""

from pathlib import Path
from typing import Any, Optional

import os


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return cur


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+

        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def load_guard_config(notebook_path: Path) -> dict[str, Any]:
    root = _find_project_root(notebook_path)
    candidates = [root / ".marimo-guard.toml", root / "marimo-guard.toml"]
    for c in candidates:
        if c.exists():
            cfg = _load_toml(c)
            if isinstance(cfg, dict):
                return cfg.get("marimo_guard", cfg)
    return {}


def env_override_bool(env_name: str, default: Optional[bool]) -> Optional[bool]:
    val = os.getenv(env_name)
    if val is None:
        return default
    v = val.strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off"}:
        return False
    return default


def env_override_int(env_name: str, default: Optional[int]) -> Optional[int]:
    val = os.getenv(env_name)
    if val is None:
        return default
    try:
        return int(val)
    except Exception:
        return default

