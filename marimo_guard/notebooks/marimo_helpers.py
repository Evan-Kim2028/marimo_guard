"""Reusable utilities for Marimo notebooks following best practices (standalone)."""

from __future__ import annotations

from typing import Any

import polars as pl
from datetime import date, datetime
from pathlib import Path
import json
from datetime import datetime as _dt


def validate_dataframe(
    df: pl.DataFrame,
    required_columns: list[str] | None = None,
) -> dict[str, Any]:
    if df.height == 0:
        return {"valid": False, "error": "DataFrame is empty - no data available", "row_count": 0, "column_count": len(df.columns)}
    if required_columns:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {"valid": False, "error": f"Missing required columns: {', '.join(missing_columns)}", "row_count": df.height, "column_count": len(df.columns)}
    return {"valid": True, "error": None, "row_count": df.height, "column_count": len(df.columns)}


def get_data_quality_summary(df: pl.DataFrame) -> dict[str, Any]:
    null_summary: dict[str, int] = {}
    column_types: dict[str, str] = {}
    for col in df.columns:
        null_summary[col] = df[col].null_count()
        column_types[col] = str(df[col].dtype)
    return {"row_count": df.height, "column_count": len(df.columns), "null_summary": null_summary, "column_types": column_types}


def write_selftest_artifact(
    notebook_path: str | Path,
    *,
    ok: bool,
    errors: list[str] | None = None,
    out_dir: str | Path | None = None,
) -> str:
    nb = Path(notebook_path).resolve()
    stem = nb.stem
    base = Path(out_dir) if out_dir else _find_project_root(nb) / "logs"
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / f"marimo_selftest_{stem}.json"
    payload = {"ok": bool(ok), "errors": list(errors or []), "notebook": str(nb), "created_at": _dt.utcnow().isoformat() + "Z"}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return str(out_path)


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return cur

