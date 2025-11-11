# Marimo Guard: Robust Pre‑Launch Validation

This guide explains how to use the Marimo Guard to catch visualization and runtime issues before you open a Marimo notebook. It covers strictness modes, chart registry, UI verification, MCP integration, artifacts, and troubleshooting.

## What It Does

Marimo Guard runs layered checks to catch problems early:
- Static checks: `marimo check` (syntax/lint)
- Python runtime: programmatic `app.run()` to catch code errors
- Offline visual validation (library‑aware): Altair, Plotly, Bokeh, Matplotlib
- Self‑test artifacts: dataset and chart preflights (JSON in `logs/`)
- MCP integration (optional): surface UI errors from Marimo MCP server
- UI strict (optional): headless browser visit to catch client‑only errors and assert chart DOM mounted

## Installation and Optional Extras

Base guard requires `marimo`. Optional extras:
- Visual export helpers (best effort):
  - Altair/Vega: `vl-convert-python` (optional)
  - Plotly static export: `kaleido` (optional)
- UI strict (headless browser):
  - `playwright` and `playwright install chromium`

## CLI Usage

```bash
# Fast checks (static + runtime + offline visual validation warnings)
marimo-guard path/to/notebook.py

# Add MCP checks
marimo-guard path/to/notebook.py --use-mcp

# Strict visual failures (Altair/Plotly/Bokeh/Matplotlib)
marimo-guard path/to/notebook.py --visual-strict

# Strict MCP (MCP outage/errors fail preflight)
marimo-guard path/to/notebook.py --use-mcp --mcp-strict

# UI strict (headless browser verification)
marimo-guard path/to/notebook.py --ui-strict --ui-timeout 20

# Combine for “belt‑and‑suspenders”
marimo-guard path/to/notebook.py --use-mcp --mcp-strict --visual-strict --ui-strict
```

## Strictness Levels

- `--visual-strict`: fail if offline validation (serialization/export) fails for Altair, Plotly, Bokeh, Matplotlib.
- `--mcp-strict`: fail if MCP unreachable or MCP reports notebook errors.
- `--ui-strict`: fail if headless browser captures console errors, request failures, or no chart DOM is present.

You can set these defaults in a config file (see Config below).

## Chart Registry (Precise Diagnostics)

Register charts to get named, per‑library diagnostics:

```python
from marimo_guard.notebooks.chart_registry import register_chart

# Altair
chart = alt.Chart(df).mark_line().encode(x="ts:T", y="value:Q")
register_chart("time_series_line", chart, lib="altair", meta={"section": "overview"})

# Plotly
fig = go.Figure(data=[go.Sankey(node=..., link=...)])
register_chart("sankey_source_token_destination", fig, lib="plotly")

# Bokeh
p = figure(...); p.line(...)
register_chart("bokeh_line", p, lib="bokeh")
```

If you don’t register, the guard falls back to a module‑scan heuristic.

## Library Coverage (Offline Validation)

- Altair: `to_dict(validate=True)`
- Plotly: `plotly.io.to_html(...)` and (if available) `plotly.io.to_image(...)`
- Bokeh: `bokeh.embed.file_html(model, bokeh.resources.CDN, ...)`
- Matplotlib: `savefig` to an in‑memory buffer
- Best‑effort checks (optional): HoloViews, Folium, PyDeck, Pyecharts, Plotnine, Graphviz

Errors appear as warnings (non‑strict) or fail the run (`--visual-strict`).

## UI Strict (Headless Browser)

When `--ui-strict` is enabled, the guard launches `marimo run` on a port and drives a headless Chromium page via Playwright.

What it checks:
- Console errors, request failures
- DOM presence for charts:
  - Altair: `[role="graphics-document"]`
  - Plotly: `div.js-plotly-plot`
  - Bokeh: `.bk-root`
  - Matplotlib: `canvas` or `img`

Artifacts are saved under `logs/`:
- `guard_ui_<notebook>.png`
- `guard_ui_<notebook>.html`

Any console/request error or missing chart DOM fails the run.

## MCP Integration

Use `--use-mcp` to query Marimo’s MCP server for errors.
- `--mcp-strict`: fail if MCP unreachable or it reports errors for this notebook
- Non‑strict: unreachable MCP adds a warning and sets `mcp.reachable=false`

## Self‑Test Artifacts

Scripts and notebooks write a JSON self‑test to `logs/marimo_selftest_<stem>.json` containing:
- `ok`: whether checks passed
- `errors`: a list of reasons

The guard requires this by default and fails if missing or false.

## Results Schema (v1.1)

Guard returns a JSON with:
- `schema_version`: `"1.1"`
- `ok`: overall status
- `error?`, `warnings[]`
- `check`: static check results
- `app_run`: programmatic run status
- `run`: headless warm run logs (patterns, excerpts)
- `selftest`: self‑test payload (if provided)
- `visual_validation`: errors and registry failures
- `mcp`: reachability, per‑notebook errors, totals
- `ui`: console errors, request failures, DOM counts, artifact paths

## Config and Environment

See `docs/marimo_guard_config.md`.

Example `.marimo-guard.toml`:

```
[visual]
strict = true

[mcp]
enabled = true
strict = true
url = "http://localhost:2718/mcp/server"
wait_seconds = 3

[ui]
strict = true
port = 2731
timeout_seconds = 20

fail_on_warn = false
require_artifact = true
```

## Troubleshooting

- UI strict fails with “playwright not installed”:
  - Install and provision: `pip install playwright && playwright install chromium`
- Plotly appears blank in UI but passes guard:
  - Enable `--ui-strict` or embed via `fig.to_html(full_html=False, include_plotlyjs="cdn")` in the notebook.
- MCP warnings about `reachable=false`:
  - Start Marimo with `--mcp` or disable MCP in config/CLI for non‑strict use.
- Slow notebooks:
  - Use smaller time windows in self‑tests; UI strict has a timeout control.

## Best Practices

- Always register critical charts with the registry and run with `--visual-strict`.
- Use MCP + UI strict for pre‑publish or CI to catch client‑only issues.
- Keep a `.marimo-guard.toml` in the repo to standardize strictness.
- Log screenshots and HTML on UI failures for faster triage.
