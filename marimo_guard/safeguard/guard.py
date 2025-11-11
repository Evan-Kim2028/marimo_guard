from __future__ import annotations

"""Marimo safeguard preflight checks with optional MCP integration (standalone)."""

import argparse
import json
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import subprocess

try:
    from marimo_guard.adapters.marimo.client import MarimoMCPClient  # type: ignore
    from marimo_guard.adapters.http_client import HttpClient, HttpClientConfig  # type: ignore
except Exception:  # pragma: no cover
    MarimoMCPClient = None  # type: ignore
    HttpClient = None  # type: ignore
    HttpClientConfig = None  # type: ignore

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

from ..utils.proc import python_executable, run as run_proc
from .config import load_guard_config, env_override_bool, env_override_int


def _marimo_cmd(*args: str) -> list[str]:
    return [python_executable(), "-m", "marimo", *args]


ERROR_PATTERNS = (
    "Traceback",
    "NameError",
    "KeyError",
    "AttributeError",
    "TypeError",
    "ValueError",
    "Exception",
    "Chart Error:",
    "SELFTEST: FAIL",
)


def _scan_logs_for_errors(text: str) -> list[str]:
    hits = []
    low = text or ""
    for pat in ERROR_PATTERNS:
        if pat in low:
            hits.append(pat)
    return hits


def _validate_visual_objects(module: Any) -> list[str]:
    errors: list[str] = []

    def _is_altair(obj: Any) -> bool:
        try:
            mod = getattr(obj.__class__, "__module__", "")
            return mod.startswith("altair") and hasattr(obj, "to_dict")
        except Exception:
            return False

    def _validate_altair(obj: Any) -> None:
        try:
            _ = obj.to_dict(validate=True)
        except Exception as e:  # noqa: BLE001
            errors.append(f"altair validation failed: {e}")

    def _is_plotly(obj: Any) -> bool:
        try:
            mod = getattr(obj.__class__, "__module__", "")
            return mod.startswith("plotly") or hasattr(obj, "to_plotly_json") or hasattr(obj, "to_dict")
        except Exception:
            return False

    def _validate_plotly(obj: Any) -> None:
        try:
            import plotly.io as pio  # type: ignore

            _ = pio.to_html(obj, include_plotlyjs=False, full_html=False)
        except Exception as e:  # noqa: BLE001
            errors.append(f"plotly validation failed: {e}")
        try:
            import plotly.io as pio  # type: ignore

            _ = pio.to_image(obj, format="png")  # requires kaleido
        except Exception:
            pass

    def _is_matplotlib(obj: Any) -> bool:
        try:
            from matplotlib.figure import Figure  # type: ignore

            return isinstance(obj, Figure)
        except Exception:
            return False

    def _validate_matplotlib(obj: Any) -> None:
        try:
            import io

            buf = io.BytesIO()
            obj.savefig(buf, format="png")
            buf.seek(0)
        except Exception as e:  # noqa: BLE001
            errors.append(f"matplotlib validation failed: {e}")

    def _is_bokeh(obj: Any) -> bool:
        try:
            from bokeh.model import Model  # type: ignore

            return isinstance(obj, Model)
        except Exception:
            return False

    def _validate_bokeh(obj: Any) -> None:
        try:
            from bokeh.embed import file_html  # type: ignore
            from bokeh.resources import CDN  # type: ignore

            _ = file_html(obj, CDN, "guard-validate")
        except Exception as e:  # noqa: BLE001
            errors.append(f"bokeh validation failed: {e}")

    try:
        for name, obj in list(getattr(module, "__dict__", {}).items()):
            if not name or name.startswith("__"):
                continue
            try:
                if _is_altair(obj):
                    _validate_altair(obj)
                elif _is_plotly(obj):
                    _validate_plotly(obj)
                elif _is_matplotlib(obj):
                    _validate_matplotlib(obj)
                elif _is_bokeh(obj):
                    _validate_bokeh(obj)
            except Exception:
                continue
    except Exception:
        pass

    return errors


def _validate_single_visual(obj: Any) -> list[str]:
    errs: list[str] = []
    try:
        mod = getattr(obj.__class__, "__module__", "")
    except Exception:
        mod = ""
    if mod.startswith("altair") and hasattr(obj, "to_dict"):
        try:
            spec = obj.to_dict(validate=True)
        except Exception as e:  # noqa: BLE001
            errs.append(f"altair validation failed: {e}")
            return errs
        try:
            import vl_convert as vlc  # type: ignore

            _ = vlc.vegalite_to_vega(spec)  # noqa: F841
        except Exception as e:
            errs.append(f"warning: altair vl-convert failed: {e}")
        return errs
    if mod.startswith("plotly") or hasattr(obj, "to_plotly_json") or hasattr(obj, "to_dict"):
        try:
            import plotly.io as pio  # type: ignore

            _ = pio.to_html(obj, include_plotlyjs=False, full_html=False)
        except Exception as e:  # noqa: BLE001
            errs.append(f"plotly validation failed: {e}")
        try:
            import plotly.io as pio  # type: ignore

            _ = pio.to_image(obj, format="png")
        except Exception:
            pass
        return errs
    if mod.startswith("bokeh"):
        try:
            from bokeh.embed import file_html  # type: ignore
            from bokeh.resources import CDN  # type: ignore

            _ = file_html(obj, CDN, "guard-validate")
        except Exception as e:  # noqa: BLE001
            errs.append(f"bokeh validation failed: {e}")
        return errs
    if mod.startswith("matplotlib"):
        try:
            import io

            buf = io.BytesIO()
            obj.savefig(buf, format="png")
            buf.seek(0)
        except Exception as e:  # noqa: BLE001
            errs.append(f"matplotlib validation failed: {e}")
        return errs
    return errs


def _pick_free_port(preferred: Optional[int] = None) -> int:
    import socket

    if preferred is not None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", preferred))
                return preferred
        except Exception:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_ui_server(nb: Path, port: int) -> subprocess.Popen[str] | None:
    try:
        cmd = _marimo_cmd("run", str(nb), "--no-token", "--headless", "--port", str(port))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(1.0)
        return proc
    except Exception:
        return None


def _project_root_from_nb(nb_path: Path) -> Path:
    cur = nb_path.resolve()
    for p in [cur] + list(cur.parents):
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return Path.cwd()


def _selftest_artifact_path(nb_path: Path) -> Path:
    root = _project_root_from_nb(nb_path)
    return root / "logs" / f"marimo_selftest_{nb_path.stem}.json"


@dataclass
class PreflightOptions:
    timeout: Optional[int] = 10
    smoke_seconds: int = 6
    run_port: Optional[int] = None
    fail_on_warn: bool = False
    require_artifact: bool = True
    use_mcp: bool = False
    mcp_url: Optional[str] = None
    mcp_strict: bool = False
    mcp_wait_seconds: int = 0
    visual_strict: bool = False
    ui_strict: bool = False
    ui_port: Optional[int] = None
    ui_timeout_seconds: int = 20


def preflight_check(notebook_path: Path, opts: PreflightOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "notebook": str(notebook_path),
        "check": {},
        "run": {},
        "warnings": [],
        "schema_version": "1.1",
    }

    rc, out, err = run_proc(_marimo_cmd("check", str(notebook_path)))
    result["check"] = {"rc": rc, "stdout": out, "stderr": err}
    if rc != 0:
        result["error"] = "marimo check failed"
        return result
    if opts.fail_on_warn and (out and "warning[" in out):
        result["error"] = "warnings detected during marimo check"
        result["check"]["warnings"] = True
        result["ok"] = False
        return result

    # Selftest via packaged module
    try:
        rc_st, out_st, err_st = run_proc([python_executable(), "-m", "marimo_guard.selftest", str(notebook_path)])
        result["selftest_script"] = {"rc": rc_st, "stdout": out_st, "stderr": err_st}
    except Exception as e:  # pragma: no cover
        result["selftest_script_error"] = str(e)

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("_nb_module", str(notebook_path))
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        app = getattr(mod, "app", None)
        if app is None:
            result["error"] = "notebook has no 'app' instance"
            return result

        _outputs, _defs = app.run()
        result["app_run"] = {"ok": True, "outputs_len": len(_outputs), "defs_len": len(_defs)}
        visual_errors = _validate_visual_objects(mod)
        if visual_errors:
            result.setdefault("visual_validation", {})["errors"] = visual_errors
            result.setdefault("warnings", []).extend(visual_errors)
        try:
            from marimo_guard.notebooks.chart_registry import snapshot_registry  # type: ignore

            reg = snapshot_registry()
            if reg:
                reg_errors = []
                fatal_found = False
                for entry in reg:
                    errs = _validate_single_visual(getattr(entry, "obj", None))
                    if errs:
                        reg_errors.append({
                            "name": getattr(entry, "name", "<unnamed>"),
                            "lib": getattr(entry, "lib", None),
                            "errors": errs,
                        })
                        result.setdefault("warnings", []).extend(
                            [f"{getattr(entry, 'name', '<unnamed>')}: {e}" for e in errs]
                        )
                        if any(not str(e).startswith("warning:") for e in errs):
                            fatal_found = True
                if reg_errors:
                    vv = result.setdefault("visual_validation", {})
                    vv["registry"] = reg_errors
                    if opts.visual_strict and fatal_found:
                        result["error"] = "visual validation errors detected (registry)"
                        result["ok"] = False
                        return result
        except Exception:
            pass
    except Exception as ex:
        tb = traceback.format_exception_only(type(ex), ex)
        result["app_run"] = {"ok": False, "error": "".join(tb)}
        result["error"] = "marimo App.run failed"
        return result

    run_args = ["run", str(notebook_path), "--no-token", "--headless", "--check"]
    if opts.run_port is not None:
        run_args += ["--port", str(opts.run_port)]
    if opts.timeout is not None:
        run_args += ["--timeout", str(opts.timeout)]
    rc, out, err = run_proc(_marimo_cmd(*run_args))
    err_lc = (err or "").lower()
    # Fallback for marimo versions that don't support --timeout
    if rc != 0 and (
        "unrecognized arguments: --timeout" in err_lc
        or "error: unrecognized arguments" in err_lc
        or "no such option: --timeout" in err_lc
    ):
        rc, out, err = run_proc(_marimo_cmd("run", str(notebook_path), "--no-token", "--headless", "--check"))
    result["run"] = {"rc": rc, "stdout": out, "stderr": err}

    smoke_ok = True
    if opts.smoke_seconds > 0:
        try:
            t0 = time.time()
            p = subprocess.Popen(_marimo_cmd("run", str(notebook_path), "--no-token", "--headless"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(max(0.1, min(opts.smoke_seconds, 2)))
            p.terminate()
            try:
                p.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                p.kill()
                smoke_ok = False
            out_smoke, err_smoke = p.communicate(timeout=1.0)
            elapsed = time.time() - t0
            logs = (out_smoke or "") + "\n" + (err_smoke or "")
            result["smoke"] = {
                "elapsed_sec": round(elapsed, 2),
                "log_error_patterns": _scan_logs_for_errors(logs),
                "log_excerpt": logs[-1000:],
            }
            if result["smoke"]["log_error_patterns"]:
                smoke_ok = False
        except Exception as e:
            result["smoke_error"] = str(e)
            smoke_ok = False

    ui_ok = True
    if opts.ui_strict or opts.ui_port is not None:
        ui = {"available": False, "ok": False}
        if not opts.ui_port:
            ui["error"] = "ui_port required for UI verification"
        else:
            try:
                from playwright.sync_api import sync_playwright  # type: ignore
            except Exception:
                ui["error"] = "playwright not installed; UI verification unavailable"
            else:
                chosen_port = _pick_free_port(opts.ui_port)
                proc = _start_ui_server(notebook_path, chosen_port)
                if proc is None:
                    ui["error"] = "failed to start UI server"
                else:
                    console_errors: list[str] = []
                    console_warnings: list[str] = []
                    request_failures: list[str] = []
                    dom: dict[str, Any] = {}
                    screenshot_path: Optional[str] = None
                    html_path: Optional[str] = None
                    try:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            page = browser.new_page()
                            cfg = load_guard_config(notebook_path)
                            allowlist = []
                            try:
                                ui_cfg = cfg.get("ui", {}) if isinstance(cfg, dict) else {}
                                if isinstance(ui_cfg, dict):
                                    allowlist = [str(s) for s in (ui_cfg.get("error_allowlist") or [])]
                            except Exception:
                                allowlist = []

                            def on_console(msg):  # type: ignore[no-untyped-def]
                                if msg.type == "error":
                                    text = f"{msg.type}: {msg.text}"
                                    if not any(sub in text for sub in allowlist):
                                        console_errors.append(text)
                                elif msg.type == "warning":
                                    console_warnings.append(f"{msg.type}: {msg.text}")

                            def on_request_failed(request):  # type: ignore[no-untyped-def]
                                request_failures.append(f"{request.method} {request.url} -> {request.failure}")

                            page.on("console", on_console)
                            page.on("requestfailed", on_request_failed)

                            page.goto(f"http://127.0.0.1:{chosen_port}/", wait_until="networkidle", timeout=opts.ui_timeout_seconds * 1000)

                            def count(sel: str) -> int:
                                try:
                                    return page.locator(sel).count()
                                except Exception:
                                    return 0

                            checks = [
                                ("altair", '[role="graphics-document"]'),
                                ("plotly", "div.js-plotly-plot"),
                                ("bokeh", ".bk-root"),
                                ("matplotlib_canvas", "canvas"),
                                ("matplotlib_img", "img"),
                            ]
                            maxima: dict[str, int] = {}
                            import time as _t
                            for _ in range(3):
                                for key, selector in checks:
                                    c = count(selector)
                                    maxima[key] = max(maxima.get(key, 0), c)
                                _t.sleep(0.4)
                            dom = {
                                "altair": {"graphics_docs": maxima.get("altair", 0)},
                                "plotly": {"plotly_divs": maxima.get("plotly", 0)},
                                "bokeh": {"bk_root": maxima.get("bokeh", 0)},
                                "matplotlib": {"canvas": maxima.get("matplotlib_canvas", 0), "img": maxima.get("matplotlib_img", 0)},
                            }

                            logs_dir = _project_root_from_nb(notebook_path) / "logs"
                            logs_dir.mkdir(parents=True, exist_ok=True)
                            screenshot_path = str(logs_dir / f"guard_ui_{notebook_path.stem}.png")
                            html_path = str(logs_dir / f"guard_ui_{notebook_path.stem}.html")
                            page.screenshot(path=screenshot_path, full_page=True)
                            html_content = page.content()
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)

                            browser.close()

                        ui["available"] = True
                        ui["console_errors"] = console_errors
                        if console_warnings:
                            ui["console_warnings"] = console_warnings
                        ui["request_failures"] = request_failures
                        ui["dom"] = dom
                        ui["screenshot"] = screenshot_path
                        ui["html"] = html_path
                        has_any_dom = any(v and any(count > 0 for count in v.values()) for v in dom.values())
                        ui_ok = has_any_dom and not console_errors and not request_failures
                        ui["ok"] = ui_ok
                        if not ui_ok and not console_errors and not request_failures and not has_any_dom:
                            ui["error"] = "no chart DOM detected"
                        elif console_errors:
                            ui["error"] = "console errors detected"
                        elif request_failures:
                            ui["error"] = "request failures detected"
                        result["ui"] = ui
                    except Exception as e:
                        ui["error"] = f"ui verification exception: {e}"
                        result["ui"] = ui
                    finally:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
        if opts.ui_strict and not (result.get("ui", {}).get("ok") is True):
            result["error"] = result.get("ui", {}).get("error") or "ui verification failed"
            return result

    if opts.use_mcp and MarimoMCPClient is not None and HttpClient is not None:
        mcp_info: dict[str, Any] = {"ok": False}
        base_url = opts.mcp_url or "http://localhost:2718/mcp/server"
        try:
            http = HttpClient(HttpClientConfig())
            client = MarimoMCPClient(base_url, http)
            if client.health_check():
                mcp_info["reachable"] = True
                errors_summary = client.get_errors_summary()
                mcp_info.update(errors_summary or {})
                try:
                    active = client.get_active_notebooks()
                except Exception:
                    active = []
                mcp_info["active_notebooks"] = active
                if opts.mcp_strict:
                    notebook_errors = None
                    nb_str = str(notebook_path)
                    if isinstance(errors_summary, dict):
                        notebooks = errors_summary.get("notebooks") or {}
                        notebook_errors = notebooks.get(nb_str) or notebooks.get(Path(nb_str).name)
                    if notebook_errors:
                        mcp_info["this_notebook_errors"] = notebook_errors
                        result["error"] = "MCP errors detected for this notebook"
                        result["mcp"] = mcp_info
                        return result
                mcp_info["ok"] = True
        except Exception as e:
            mcp_info["error"] = str(e)
        result["mcp"] = mcp_info

    # Require selftest artifact if configured
    try:
        art = _selftest_artifact_path(notebook_path)
        if opts.require_artifact and not art.exists():
            result["error"] = "selftest artifact missing"
            return result
        if art.exists():
            try:
                import json as _json

                with open(art, "r", encoding="utf-8") as f:
                    result["selftest"] = _json.load(f)
            except Exception:
                pass
    except Exception:
        pass

    result["ok"] = (result.get("error") is None) and (rc == 0) and smoke_ok
    return result


def launch_if_ok(nb_path: Path, port: Optional[int], *, kill_existing: bool = True) -> dict[str, Any]:
    try:
        port = port or _pick_free_port(2731)
        cmd = _marimo_cmd("edit", str(nb_path), "--no-token", "--port", str(port))
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        time.sleep(0.75)
        return {"launched": True, "url": f"http://127.0.0.1:{port}/", "pid": proc.pid}
    except Exception as e:
        return {"launched": False, "error": str(e)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Preflight checks for Marimo notebook")
    p.add_argument("notebook", help="Path to marimo .py notebook")
    p.add_argument("--timeout", type=int, default=10)
    p.add_argument("--smoke-seconds", type=int, default=6)
    p.add_argument("--run-port", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--launch", action="store_true")
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--keep-existing", action="store_true")
    p.add_argument("--use-mcp", action="store_true")
    p.add_argument("--mcp-url", type=str, default=None)
    p.add_argument("--mcp-strict", action="store_true")
    p.add_argument("--mcp-wait-seconds", type=int, default=0)
    p.add_argument("--fail-on-warn", action="store_true")
    p.add_argument("--visual-strict", action="store_true")
    p.add_argument("--ui-strict", action="store_true")
    p.add_argument("--ui-port", type=int, default=None)
    p.add_argument("--ui-timeout", type=int, default=20)

    args = p.parse_args(argv)
    nb_path = Path(args.notebook).expanduser().resolve()
    if not nb_path.exists():
        print(json.dumps({"ok": False, "error": f"Notebook not found: {nb_path}"}))  # noqa: T201
        return 1

    cfg = load_guard_config(nb_path)

    def pick_bool(cli_val: Optional[bool], cfg_path: list[str], env_name: str, default: bool) -> bool:
        v = cli_val if cli_val is not None else default
        if v == default:
            cfg_cursor: Any = cfg
            try:
                for k in cfg_path:
                    if not isinstance(cfg_cursor, dict):
                        cfg_cursor = {}
                        break
                    cfg_cursor = cfg_cursor.get(k, {})
                if isinstance(cfg_cursor, bool):
                    v = cfg_cursor
            except Exception:
                pass
            v = env_override_bool(env_name, v)
            v = bool(v)
        return v

    def pick_int(cli_val: Optional[int], cfg_path: list[str], env_name: str, default: Optional[int]) -> Optional[int]:
        v: Optional[int] = cli_val if cli_val is not None else default
        if v == default:
            cfg_cursor: Any = cfg
            try:
                for k in cfg_path:
                    if not isinstance(cfg_cursor, dict):
                        cfg_cursor = {}
                        break
                    cfg_cursor = cfg_cursor.get(k, {})
                if isinstance(cfg_cursor, int):
                    v = cfg_cursor
            except Exception:
                pass
            v = env_override_int(env_name, v)
        return v

    opts = PreflightOptions(
        timeout=args.timeout,
        smoke_seconds=args.smoke_seconds,
        run_port=args.run_port,
        fail_on_warn=pick_bool(args.fail_on_warn, ["fail_on_warn"], "MARIMO_GUARD_FAIL_ON_WARN", False),
        require_artifact=pick_bool(True, ["require_artifact"], "MARIMO_GUARD_REQUIRE_ARTIFACT", True),
        use_mcp=pick_bool(args.use_mcp, ["mcp", "enabled"], "MARIMO_GUARD_USE_MCP", False),
        mcp_url=cfg.get("mcp", {}).get("url", args.mcp_url) if isinstance(cfg.get("mcp"), dict) else args.mcp_url,
        mcp_strict=pick_bool(args.mcp_strict, ["mcp", "strict"], "MARIMO_GUARD_MCP_STRICT", False),
        mcp_wait_seconds=pick_int(args.mcp_wait_seconds, ["mcp", "wait_seconds"], "MARIMO_GUARD_MCP_WAIT_SECONDS", 0) or 0,
        visual_strict=pick_bool(args.visual_strict, ["visual", "strict"], "MARIMO_GUARD_VISUAL_STRICT", False),
        ui_strict=pick_bool(args.ui_strict, ["ui", "strict"], "MARIMO_GUARD_UI_STRICT", False),
        ui_port=pick_int(args.ui_port, ["ui", "port"], "MARIMO_GUARD_UI_PORT", None),
        ui_timeout_seconds=pick_int(args.ui_timeout, ["ui", "timeout_seconds"], "MARIMO_GUARD_UI_TIMEOUT", 20) or 20,
    )

    pre = preflight_check(nb_path, opts)
    if not pre.get("ok"):
        if args.json:
            print(json.dumps(pre))  # noqa: T201
        else:
            print("Preflight failed:")  # noqa: T201
            print(pre.get("error", "unknown error"))  # noqa: T201
        return 1

    launch_info = None
    if args.launch:
        launch_info = launch_if_ok(nb_path, args.port, kill_existing=not args.keep_existing)
        if not launch_info.get("launched"):
            payload = {**pre, "launch": launch_info}
            if args.json:
                print(json.dumps(payload))  # noqa: T201
            else:
                print(f"Launch failed: {launch_info.get('error')}")  # noqa: T201
            return 2

    payload: dict[str, Any] = {"ok": True, "notebook": str(nb_path), "preflight": pre}
    if launch_info:
        payload["launch"] = launch_info

    if args.json:
        print(json.dumps(payload))  # noqa: T201
    else:
        print(f"OK: {nb_path}")  # noqa: T201
        for w in pre.get("warnings", []) or []:
            print(f"Warning: {w}")  # noqa: T201
        if launch_info and launch_info.get("launched"):
            print(f"Launched at {launch_info['url']}")  # noqa: T201
    return 0


__all__ = ["PreflightOptions", "preflight_check", "launch_if_ok", "main"]
