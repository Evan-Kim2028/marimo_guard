# Marimo Best Practices and Agent Guide

Build fast, reliable, reactive Marimo notebooks and dashboards. This guide clusters best practices into fundamentals, data and plotting, UI and interactivity, performance, production, and integration.

## Fundamentals

- Reactive execution: cells form a DAG by variable reference; only dependents re-run.
- UI elements expose `.value`: bind `mo.ui.*` to a global to drive reactivity.
- Prefer `.value` over `mo.state`: reserve `mo.state` for shared, mutable state only when necessary.
- Unique globals: keep names descriptive and unique to avoid dependency ambiguity.

## DataFrames and Transformations

- Native support: `mo.ui.dataframe`, `mo.ui.table`, and the data explorer panels work with Polars and Pandas interchangeably.
- Interactive transforms: `df_tf = mo.ui.dataframe(df)` exposes filters/group-bys; use `df_tf.value` (type preserved: Polars in → Polars out).
- Selections: table/chart selections round-trip to Python as dataframes; wire them into downstream cells.
- Big data pattern: keep heavy transforms in Polars (`LazyFrame` until materialization), aggregate/downsample upstream, and hand compact frames to UI/plots.

## Visualization

- Altair + Polars
  - Use Polars directly: `alt.Chart(df)` accepts a Polars `DataFrame`.
  - Convenience API: `df.plot.point(...)` returns an Altair `Chart` for further config (e.g., `.properties`, `.configure_*`).
  - Lazy pipelines: call `.collect()` on a `LazyFrame` before plotting.
  - Keep payloads small: Altair serializes data; aggregate/downsample in Polars.
  - Data transformers (large data):
    ```python
    import altair as alt
    # Option A: disable max_rows guard (be careful with large frames)
    alt.data_transformers.disable_max_rows()
    # Option B: serve data via JSON files (more scalable than inline)
    # Note: for static exports, ensure data is embedded (pre-render) or paths resolve.
    alt.data_transformers.enable('json')
    ```
  - Reactive embedding: wrap with `mo.ui.altair_chart(chart)` to receive selection payloads via `.value`.
  - Manage selections: customize with `.add_params(...)`; set `chart_selection=False` and/or `legend_selection=False` in `mo.ui.altair_chart` if you manage selections yourself (see “Disabling automatic selection” in the Plotting API).
- Plotly + Polars
  - Use arrays from Polars (no conversion):
    ```python
    import plotly.express as px
    fig = px.scatter(x=df["sepal_length"].to_list(), y=df["sepal_width"].to_list(), color=df["species"].to_list())
    ```
  - Or convert to Pandas for convenience APIs:
    ```python
    fig = px.scatter(df.to_pandas(), x="sepal_length", y="sepal_width", color="species")
    ```
  - Wrap with `mo.ui.plotly(fig)` for reactive selections where supported.
- Matplotlib
  - Static by default; works for rendering. For interactivity, see `marimo.mpl.interactive` (limited compared to Altair/Plotly).

Marimo plotting wrappers: key properties

- Altair wrapper (`mo.ui.altair_chart`)
  - `.value`: reactive selection payload for the chart.
  - `.selections`: convenience accessor for selection info.
  - `.dataframe`, `.name`, `.text`: introspection helpers.
  - `.apply_selection(...)`: apply the selection to data downstream.
  - Layout helpers: `.left()`, `.right()`, `.center()`, `.style()`, `.form()`, `.callout()`, `.batch()`.

- Plotly wrapper (`mo.ui.plotly`)
  - `.value`: reactive payload containing selections.
  - `.points`, `.indices`, `.ranges`, `.text`: convenience accessors for selected points/indices/ranges.
  - Same layout helpers as above.

Minimal reactive Altair example

```python
import altair as alt
import marimo as mo

# df can be a Polars or Pandas DataFrame
chart = alt.Chart(df).mark_point().encode(x="x", y="y")
ui = mo.ui.altair_chart(chart)
selected = ui.value  # reactive selection payload
```

Disable automatic selection (manage your own Altair selection)

```python
import altair as alt

sel = alt.selection_point(fields=["species"])  # define your selection
chart = (
    alt.Chart(df)
    .mark_point()
    .encode(x="sepal_length", y="sepal_width", color="species")
    .add_params(sel)
    .transform_filter(sel)
)
ui = mo.ui.altair_chart(chart, chart_selection=False)
```

Altair selection patterns

```python
import altair as alt

# 1) Multi-select categories via legend
sel_legend = alt.selection_point(fields=["species"], bind="legend")
legend_chart = (
    alt.Chart(df)
    .mark_point()
    .encode(
        x="sepal_length",
        y="sepal_width",
        color="species",
        opacity=alt.condition(sel_legend, alt.value(1.0), alt.value(0.2)),
    )
    .add_params(sel_legend)
)

# 2) Interval brush on x and y
brush = alt.selection_interval(encodings=["x", "y"])  # drag to select a region
brush_chart = (
    alt.Chart(df)
    .mark_point()
    .encode(x="sepal_length", y="sepal_width", color="species")
    .add_params(brush)
)

# 3) Nearest point highlight on hover
nearest = alt.selection_point(nearest=True, on="pointerover", empty=False)
nearest_chart = (
    alt.Chart(df)
    .mark_point(size=60)
    .encode(
        x="sepal_length",
        y="sepal_width",
        color=alt.condition(nearest, "species", alt.value("lightgray")),
        tooltip=["species", "sepal_length", "sepal_width"],
    )
    .add_params(nearest)
)

# Wrap any chart for reactivity; pass chart_selection=False if managing selection yourself
ui = mo.ui.altair_chart(legend_chart)
```

Reading Altair selection payloads (`ui.value`)

```python
import polars as pl

payload = ui.value or {}
print(payload)  # inspect keys to confirm your selection shape

# Example A: point/categorical selection (e.g., legend multi-select)
selected_species = payload.get("species")
if selected_species:
    if not isinstance(selected_species, list):
        selected_species = [selected_species]
    filtered = df.filter(pl.col("species").is_in(selected_species))
else:
    filtered = df

# Example B: interval brush (x/y ranges with min/max)
xr = payload.get("x")
yr = payload.get("y")
if xr and yr:
    filtered = df.filter(
        (pl.col("sepal_length").is_between(xr["min"], xr["max"]))
        & (pl.col("sepal_width").is_between(yr["min"], yr["max"]))
    )
```

Plotly selection → filter DataFrame

```python
import plotly.express as px

# Using Polars arrays (no conversion), or use df.to_pandas() for convenience
fig = px.scatter(
    x=df["sepal_length"].to_list(),
    y=df["sepal_width"].to_list(),
    color=df["species"].to_list(),
)
plot = mo.ui.plotly(fig)

# Downstream: use selected indices to filter the source frame
sel_idx = plot.indices  # list of integer indices into the plotted data
filtered_df = df if not sel_idx else df.take(sel_idx)  # Polars take by indices
```

## End-to-End Reactive Loop (Data → Altair → Marimo → Data)

Pattern: source data and controls drive a computed frame; charts render from that frame; user selections feed downstream filters and views. Keep the DAG acyclic: selections should not feed back into the same cell that computes the chart’s source data.

```python
import marimo as mo
import polars as pl
import altair as alt

# Controls
time = mo.ui.range_slider(0, 100, value=(10, 60), label="Time")
species = mo.ui.multiselect(["Setosa", "Versicolor", "Virginica"], value=["Setosa", "Versicolor"], label="Species")
run = mo.ui.run_button(label="Refresh data")  # gate heavy work

@mo.cache
def load_raw(path: str) -> pl.DataFrame:
    return pl.read_parquet(path)

@mo.cache
def compute_frame(raw: pl.DataFrame, time_range: tuple[int, int], sp: list[str]) -> pl.DataFrame:
    lo, hi = time_range
    return (
        raw.filter((pl.col("t") >= lo) & (pl.col("t") <= hi) & (pl.col("species").is_in(sp)))
           .group_by(["species"]).agg(pl.col("value").mean().alias("avg_value"))
    )

# Gate recompute behind the run button
mo.stop(not run.value, mo.md("Click Refresh data to compute"))

raw = load_raw("events.parquet")
frame = compute_frame(raw, time.value, species.value)

# Chart from computed Polars DataFrame
chart = alt.Chart(frame).mark_bar().encode(x="species", y="avg_value")
chart_ui = mo.ui.altair_chart(chart)  # get selection via chart_ui.value

# Normalize selection → downstream filter (drill-down table)
payload = chart_ui.value or {}
selected_species = payload.get("species")
if selected_species and not isinstance(selected_species, list):
    selected_species = [selected_species]

drill_filter = selected_species or species.value  # fallback to current control selection
drill = raw.filter(pl.col("species").is_in(drill_filter))
mo.ui.dataframe(drill)
```

Loop checklist

- Acyclic: keep “source-of-truth” compute cells upstream; use selection only in downstream views to avoid cycles.
- Materialize once: compute once per control state, reuse across charts/tables; avoid `.collect()` per chart.
- Cache: use `@mo.cache`/`@mo.persistent_cache` for expensive pure functions keyed by controls.
- Gate: pair fast, instant controls with upstream filters; use a run button for heavy recompute.
- Normalize selection: always handle empty, scalar, and list cases for `ui.value`.
- Fallbacks: when selection is empty, fall back to current control state or “show all”.
- Shareable state: mirror control values in `mo.query_params()` for deep links; initialize Altair selections via `selection_point(value=...)` when needed.

## UI, Layout, and Interactivity

- Layout primitives: `mo.vstack`, `mo.hstack`, `mo.sidebar`, `mo.right`, `mo.routes` (multi-page), `mo.ui.tabs`.
- Tables and editors: `mo.ui.table`, `mo.ui.dataframe`, `mo.ui.data_explorer`, `mo.ui.data_editor` for sorting/filtering/editing.
- Outputs and streaming: `mo.output.replace`/`append`/`clear`/`replace_at_index` stream logs/progress/partials.
- Status and progress: `mo.status.spinner`, `mo.status.progress_bar` for responsive UX during work.
- URL state: `qp = mo.query_params()` for sharable deep links; bind inputs to `qp[...]`.
- Watchers: `mo.watch.file(path)`, `mo.watch.directory(path)` react to changes in files/directories.
- Compose interactions: use one chart’s/table’s selection to filter other views; pair charts with controls (sliders/dropdowns) to parameterize queries.

### HTML and Markdown

- Markdown: `mo.md` for safe, styled text; supports headings, tables, and code blocks.
- Raw HTML: `mo.html("<div>...</div>")` to embed custom components, CSS, and small amounts of JS when needed.
- Styling: prefer CSS classes and scoped styles in your HTML; avoid heavy inline scripts.
- Security: only render trusted HTML. Avoid injecting untrusted scripts; prefer Marimo components when possible.

Custom HTML widget (scoped styles)

```python
active_users = 12345  # example value; set from your compute
card = mo.html(
    f"""
    <style>
      .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; }}
      .title {{ font-weight: 600; margin-bottom: 6px; }}
      .metric {{ font-size: 20px; }}
    </style>
    <div class="card">
      <div class="title">Active Users</div>
      <div class="metric">{active_users:,}</div>
    </div>
    """
)
```

## Performance and Reliability

- Cache: `@mo.cache` (memory) and `@mo.persistent_cache` (disk) for expensive pure functions; consider `@mo.lru_cache`.
- Gate heavy work: `run = mo.ui.run_button()` + `mo.stop(not run.value, mo.md("Click Run"))` to avoid incidental recomputation.
- Lazy UI: `mo.lazy(fn)` to render expensive components on demand.
- Minimize mutations: create new objects or confine mutation to the creator cell.
- Prefer functions/modules: move complex logic to modules; rely on Marimo’s module reloader.
- Vectorized compute: prefer Polars/Pandas, Altair, Plotly for efficient re-runs.

## Production and Export

- App mode: `marimo run notebook.py` renders a code-optional app view (grid options available).
- App config: `marimo.App(width=..., theme=...)` and `AppMeta` for presentation.
- Export: `marimo export` to static HTML (supports pre-render), WASM HTML, Python script, Markdown, Jupyter, PDF/slides.
- Embed (“Islands”): embed selected reactive widgets/outputs into arbitrary HTML.

## CLI and Linting (`marimo check`)

- Command: `marimo check [OPTIONS] [FILES]...`
- Useful options: `--fix`, `--unsafe-fixes`, `--strict`, `--format json`, `--ignore-scripts`.
- Use in CI to enforce reactive-safe, well-structured notebooks.

## MCP Integration (Server and Client)

- Install and run with MCP

```bash
# pip
pip install "marimo[mcp]"
marimo edit notebook.py --mcp --no-token

# uv
uv run --with="marimo[mcp]" marimo edit notebook.py --mcp --no-token

# uvx
uvx "marimo[mcp]" edit notebook.py --mcp --no-token
```

- Security: `--no-token` is for local only; enable tokens (`--token/--token-password`) in production. MCP is experimental.
- Connect clients to `http://localhost:PORT/mcp/server` (Claude Code, Cursor/VS Code, etc.).
- Once connected, external tools can invoke Marimo AI tools (e.g., `active_notebooks`, `errors_summary`) against live notebooks.

## Recipes

- Polars-powered KPI dashboard
  - Data: read → `LazyFrame` transforms → `collect()`; aggregate/downsample upstream.
  - Controls: time-range slider, segment multi-select, run button for expensive refresh.
  - Views: summary `mo.stat`, Altair charts, table of filtered rows, drill-down routes.

- Minimal reactive dashboard (Altair + slider)

```python
import marimo as mo
import altair as alt
import pandas as pd

app = mo.App(width="medium")

@app.cell
def _():
    slider = mo.ui.slider(1, 100, value=20, label="N")
    return slider

@app.cell
def _(slider):
    df = pd.DataFrame({"x": range(slider.value), "y": range(slider.value)})
    return df

@app.cell
def _(df: pd.DataFrame):
    alt.Chart(df).mark_line().encode(x="x", y="y")
```

- Controlled recomputation and progress

```python
run = mo.ui.run_button(label="Run report")

# In a downstream cell
mo.stop(not run.value, mo.md("Click Run to start"))
with mo.status.spinner(title="Building…"):
    do_work()
mo.output.replace("Starting…")
mo.output.append("Step 1 done")
```

## Common Pitfalls

- Expecting mutations to trigger reactivity: mutating lists/dicts in place doesn’t re-run dependents; assign new values or leverage UI/state.
- UI not bound to globals: an unbound UI element won’t drive reactivity.
- Overusing `mo.state`: prefer UI `.value` for almost all workflows.
- Storing UI objects in `mo.state`: discouraged; keep state for values, not widgets.

## References

- Key concepts: https://docs.marimo.io/getting_started/key_concepts/
- DataFrames (Polars/Pandas): https://docs.marimo.io/guides/working_with_data/dataframes/
- Plotting guide: https://docs.marimo.io/guides/working_with_data/plotting/
- Best practices: https://docs.marimo.io/guides/best_practices/
- Outputs (API): https://docs.marimo.io/api/outputs/
- Outputs (guide): https://docs.marimo.io/guides/outputs/
- Layouts (API): https://docs.marimo.io/api/layouts/
- Plotting (API): https://docs.marimo.io/api/plotting/
- HTML (API): https://docs.marimo.io/api/html/
- State (API): https://docs.marimo.io/api/state/
- Watchers (API): https://docs.marimo.io/api/watch/
- Status (API): https://docs.marimo.io/api/status/
- Query params (API): https://docs.marimo.io/api/query_params/
- Apps guide: https://docs.marimo.io/guides/apps/
- Exporting/Embedding: https://docs.marimo.io/guides/exporting/
- Expensive notebooks: https://docs.marimo.io/guides/expensive_notebooks/
- CLI: https://docs.marimo.io/cli/
- MCP server/client: https://docs.marimo.io/guides/editor_features/mcp/
- Security/auth: https://docs.marimo.io/security/
