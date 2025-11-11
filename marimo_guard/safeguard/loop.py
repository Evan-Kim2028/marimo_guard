from __future__ import annotations

"""Retry loop around the marimo safeguard preflight with optional fixer."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Tuple

from .guard import PreflightOptions, preflight_check
from ..utils.proc import python_executable
import subprocess


def _write_iter_json(nb: Path, iteration: int, payload: dict[str, Any]) -> str:
    logs = Path("logs")
    logs.mkdir(parents=True, exist_ok=True)
    out_path = logs / f"marimo_guard_iter_{nb.stem}_{iteration}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return str(out_path)


def _format_error_summary(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    err = payload.get("error")
    if err:
        parts.append(f"error: {err}")
    app_run = payload.get("preflight", {}).get("app_run") if "preflight" in payload else payload.get("app_run")
    if isinstance(app_run, dict) and not app_run.get("ok", True):
        parts.append(f"app_run: {app_run.get('error')}")
    run = payload.get("preflight", {}).get("run") if "preflight" in payload else payload.get("run")
    if isinstance(run, dict) and run.get("log_error_patterns"):
        parts.append("log errors: " + ", ".join(run.get("log_error_patterns", [])))
        log_excerpt = run.get("log_excerpt")
        if log_excerpt:
            parts.append("excerpt:\n" + str(log_excerpt))
    st = payload.get("preflight", {}).get("selftest") if "preflight" in payload else payload.get("selftest")
    if isinstance(st, dict) and not st.get("ok", True):
        errs = st.get("errors") or []
        if errs:
            parts.append("selftest: " + "; ".join(map(str, errs)))
    mcp = payload.get("preflight", {}).get("mcp") if "preflight" in payload else payload.get("mcp")
    if isinstance(mcp, dict):
        this_nb = mcp.get("this_notebook_errors")
        if this_nb:
            parts.append("mcp: " + "; ".join(map(str, this_nb if isinstance(this_nb, list) else [this_nb])))
    return "\n".join(parts)


def _run_shell(cmd_str: str, *, env: dict[str, str]) -> Tuple[int, str, str]:
    proc = subprocess.Popen(["bash", "-lc", cmd_str], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    out, err = proc.communicate()
    return proc.returncode, out, err


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run marimo_guard in a retry loop with optional fixer")
    p.add_argument("notebook", help="Path to marimo .py notebook")
    p.add_argument("--max-iters", type=int, default=3, help="Maximum iterations (default 3)")
    p.add_argument("--sleep-seconds", type=int, default=3, help="Seconds to sleep between iterations")
    p.add_argument("--use-mcp", action="store_true", help="Enable MCP checks (recommended)")
    p.add_argument(
        "--mcp-url",
        type=str,
        default=os.environ.get("MARIMO_GUARD_MCP_URL", "http://localhost:2718/mcp/server"),
    )
    p.add_argument("--mcp-strict", action="store_true", help="Fail on any MCP errors across notebooks")
    p.add_argument("--mcp-wait-seconds", type=int, default=0, help="Wait for MCP availability up to N seconds")
    p.add_argument("--timeout", type=int, default=10)
    p.add_argument("--smoke-seconds", type=int, default=6)
    p.add_argument("--on-error-cmd", type=str, default="", help="Shell command to run on error; gets {nb} substitution and ERR_JSON env var")

    args = p.parse_args(argv)
    nb = Path(args.notebook).expanduser().resolve()
    if not nb.exists():
        print(f"Notebook not found: {nb}", file=sys.stderr)  # noqa: T201
        return 1

    opts = PreflightOptions(
        timeout=args.timeout,
        smoke_seconds=args.smoke_seconds,
        use_mcp=args.use_mcp,
        mcp_url=args.mcp_url,
        mcp_strict=args.mcp_strict,
        mcp_wait_seconds=args.mcp_wait_seconds,
    )

    fixer_cmd_template = args.on_error_cmd.strip()

    for i in range(1, max(1, args.max_iters) + 1):
        pre = preflight_check(nb, opts)
        payload: dict[str, Any] = {"ok": pre.get("ok", False), "preflight": pre, "iteration": i, "notebook": str(nb)}
        out_path = _write_iter_json(nb, i, payload)
        if payload.get("ok") is True:
            print(f"✓ Notebook passed preflight on iteration {i}: {nb}")  # noqa: T201
            print(f"  details: {out_path}")  # noqa: T201
            return 0

        print(f"✗ Preflight failed on iteration {i}")  # noqa: T201
        summary = _format_error_summary(payload or {})
        if summary:
            print(summary)  # noqa: T201
        print(f"  json: {out_path}")  # noqa: T201

        if fixer_cmd_template:
            env = os.environ.copy()
            env["ERR_JSON"] = out_path
            cmd_str = fixer_cmd_template.replace("{nb}", str(nb))
            rc, out, err = _run_shell(cmd_str, env=env)
            if rc != 0:
                print(f"  fixer command failed (rc={rc}): {err or out}")  # noqa: T201
        else:
            time.sleep(max(0, int(args.sleep_seconds)))

    print("Failed to converge within iteration budget", file=sys.stderr)  # noqa: T201
    return 2


__all__ = ["main"]
