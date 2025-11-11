# marimo_guard

## Installation

1. Clone the GitHub repository to get marimo_guard locally:

   ```sh
   git clone https://github.com/Evan-Kim2028/marimo_guard.git
   ```

## Why marimo_guard

- Purpose-built to catch errors before you open a Marimo notebook. It validates code, data, visuals, and (optionally) the UI so you don’t discover breakage only after launching a browser session.
- Designed for CI, editor agents, and local workflows to give a fast “go/no-go” signal with actionable artifacts.

## What it does (defensive checks)

- **Static checks** – runs `marimo check` and fails on errors; can optionally fail on warnings.
- **Programmatic run** – imports your notebook and calls `app.run()` to catch Python exceptions deterministically.
- **Visual validation** – inspects Altair/Plotly/Bokeh/Matplotlib outputs (optionally with a chart registry you control).
- **Headless smoke run** – short `marimo run --headless --check` phase to ensure it boots and renders early cells.
- **UI verification (optional)** – Playwright-based DOM checks; collects console and request failures; saves screenshot and HTML.
- **MCP session awareness (optional)** – queries Marimo’s MCP endpoint to detect active sessions and surface errors.
- **Self-test artifact** – writes JSON per notebook to `logs/` for audit and tooling.

## Shortcomings to be aware of

- Visual validation may produce false positives/negatives for complex libraries or custom renderers.
- UI verification requires Playwright (and installed browsers), adding optional overhead.
- First run with `uv` builds an isolated environment; subsequent runs are faster.
- Notebook-specific side effects (network calls, heavy imports) can slow or flake preflight unless guarded in your code.
- Different Marimo versions expose slightly different flags; `marimo_guard` contains fallbacks (e.g., `--timeout`) but version skew can still affect UX.

## Quick start (uv-managed)

### 1) From this folder

```sh
uv run -- marimo-guard --help
uv run -- marimo-guard notebooks/layerzero_stablecoins.py --json
uv run -- marimo-guard-loop notebooks/layerzero_stablecoins.py --max-iters 3
uv run -- marimo-watch notebooks/layerzero_stablecoins.py --port 2731
```

### 2) Optional configuration

Place `.marimo-guard.toml` at your project root, for example:

```toml
[visual]
strict = true

[ui]
strict = false
port = 2731
timeout_seconds = 20
```

### MCP URL env

- `MARIMO_GUARD_MCP_URL` controls the default MCP endpoint used by `--mcp-url`.
- Example: `export MARIMO_GUARD_MCP_URL=http://localhost:2718/mcp/server`
- You can always override with the CLI flag: `--mcp-url <URL>`

## CLI overview

- `marimo-guard path/to/notebook.py [--json] [--launch] [--use-mcp] [--visual-strict] [--ui-strict] [--ui-port N] [--ui-timeout N] [--smoke-seconds N]`
- `marimo-guard-loop path/to/notebook.py --max-iters 3 --sleep-seconds 3 [--on-error-cmd "..."]`
- `marimo-watch path/to/notebook.py --port 2731`

## Dev UX tips

- Slow first run? Use the venv directly after `uv` creates it: `.venv/bin/marimo-guard ...`.
- Disable smoke for speed: `--smoke-seconds 0`.
- Skip UI checks unless you need browser-level assurance; rely on programmatic and smoke phases first.
- Register charts you care about with the registry (`marimo_guard.notebooks.chart_registry`) for precise validation and cleaner error messages.

## UI verification (optional)

- Install browsers required for Playwright UI checks:
  ```sh
  uv run --with playwright python -m playwright install chromium
  ```
- Run with strict UI checks:
  ```sh
  uv run -- marimo-guard notebooks/your_notebook.py --ui-strict --ui-port 2731
  ```
- Artifacts saved to `logs/`: HTML snapshot, screenshot, and JSON.

## Python version

- Requires Python 3.13+ (`requires-python = ">=3.13"` in `pyproject.toml`). `uv` will manage an isolated environment by default.
