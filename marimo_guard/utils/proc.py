"""Process helpers for CLI orchestration (standalone)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Tuple


def python_executable() -> str:
    """Prefer project-local virtualenv interpreter if present."""
    venv_python = Path(".venv/bin/python")
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def run(cmd: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None) -> Tuple[int, str, str]:
    """Run a command returning (rc, stdout, stderr)."""
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    out, err = proc.communicate()
    return proc.returncode, out, err

