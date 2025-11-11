# Marimo Guard Configuration

Marimo Guard supports project-level defaults via a TOML config file and environment variables.

## Config file

Create `.marimo-guard.toml` (or `marimo-guard.toml`) at your project root:

```
[visual]
strict = true  # fail on Altair/Plotly/Bokeh/Matplotlib validation errors

[mcp]
enabled = true
strict = true
url = "http://localhost:2718/mcp/server"
wait_seconds = 3

[ui]
strict = true
port = 2731
timeout_seconds = 20

# Optional top-level flags
fail_on_warn = false
require_artifact = true
```

## Environment variables (override config)

- `MARIMO_GUARD_VISUAL_STRICT=1`
- `MARIMO_GUARD_UI_STRICT=1`
- `MARIMO_GUARD_UI_TIMEOUT=30`
- `MARIMO_GUARD_UI_PORT=2731`
- `MARIMO_GUARD_MCP_STRICT=1`
- `MARIMO_GUARD_MCP_WAIT_SECONDS=3`
- `MARIMO_GUARD_USE_MCP=1`
- `MARIMO_GUARD_FAIL_ON_WARN=1`
- `MARIMO_GUARD_REQUIRE_ARTIFACT=0`

CLI options always take precedence over config and env defaults.

## Selectors (advanced)

UI verification uses sane defaults to detect chart DOMs:

- Altair: `[role="graphics-document"]`
- Plotly: `div.js-plotly-plot`
- Bokeh: `.bk-root`
- Matplotlib: `canvas`, `img`

These can be extended in the future to support per-project overrides.

