from __future__ import annotations

"""Python-only watcher to (re)start marimo edit on file changes with MCP."""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from ..utils.proc import python_executable


def _spawn_marimo(nb: Path, port: int, log_file: Optional[str]) -> subprocess.Popen[str]:
    cmd = [
        python_executable(),
        "-m",
        "marimo",
        "edit",
        str(nb),
        "--no-token",
        "--port",
        str(port),
        "--headless",
        "--mcp",
    ]
    out = open(log_file, "a", encoding="utf-8") if log_file else subprocess.DEVNULL  # noqa: SIM115
    proc = subprocess.Popen(cmd, stdout=out, stderr=out, text=True)
    return proc


def _restart(proc: Optional[subprocess.Popen[str]], nb: Path, port: int, log_file: Optional[str]) -> subprocess.Popen[str]:
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass
    return _spawn_marimo(nb, port, log_file)


def _watch_loop(nb: Path, port: int, log_file: Optional[str], poll_seconds: float) -> int:
    proc: Optional[subprocess.Popen[str]] = None
    try:
        from watchdog.events import FileSystemEventHandler  # type: ignore
        from watchdog.observers import Observer  # type: ignore

        class _Handler(FileSystemEventHandler):
            def __init__(self) -> None:
                self._last = 0.0

            def on_modified(self, event):  # type: ignore[no-untyped-def]
                nonlocal proc
                now = time.time()
                if now - self._last < 0.25:
                    return
                self._last = now
                proc = _restart(proc, nb, port, log_file)

        handler = _Handler()
        observer = Observer()
        observer.schedule(handler, str(nb.parent), recursive=False)
        proc = _spawn_marimo(nb, port, log_file)
        observer.start()
        try:
            while True:
                time.sleep(0.5)
        finally:
            observer.stop()
            observer.join(timeout=2.0)
    except Exception:
        proc = _spawn_marimo(nb, port, log_file)
        last_mtime = nb.stat().st_mtime if nb.exists() else 0.0
        try:
            while True:
                time.sleep(max(0.1, poll_seconds))
                try:
                    mtime = nb.stat().st_mtime
                except FileNotFoundError:
                    mtime = last_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    proc = _restart(proc, nb, port, log_file)
        finally:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Python watcher for marimo edit with MCP")
    p.add_argument("notebook", help="Path to marimo .py notebook")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", 2731)))
    p.add_argument("--log-file", type=str, default=os.environ.get("MARIMO_WATCH_LOG", ""))
    p.add_argument("--poll-seconds", type=float, default=0.5, help="Polling interval when watchdog unavailable")

    args = p.parse_args(argv)
    nb = Path(args.notebook).expanduser().resolve()
    if not nb.exists():
        print(f"Notebook not found: {nb}", file=sys.stderr)  # noqa: T201
        return 1

    def _sig_handler(signum, frame):  # type: ignore[no-untyped-def]
        raise SystemExit(130)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    log_file = args.log_file or None
    return _watch_loop(nb, args.port, log_file, args.poll_seconds)


__all__ = ["main"]

