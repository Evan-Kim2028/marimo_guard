# Reports and Notebooks Guide

spice-mcp includes optional Marimo integration for creating interactive data visualization notebooks from Dune queries. Generate a starter notebook, then customize it interactively in Marimo's UI.

## 🚀 Getting Started

### Installation

Install the optional reports dependency group:

```bash
# Install with Marimo and visualization libraries
pip install 'spice-mcp[reports]'

# Or install individually
pip install marimo altair vegafusion plotly
```

### Quick Start

```bash
# Generate basic notebook
spice-mcp notebook "SELECT date, price FROM eth_prices ORDER BY date" eth_analysis.py

# Open automatically in browser
spice-mcp notebook "SELECT * FROM eth.blocks LIMIT 100" blocks.py --open
```

> Notebooks are stored under the configured reports directory (default: `./reports/notebooks`). The CLI returns the exact path after creation.

## 🔧 CLI Usage

### Basic Syntax

```bash
spice-mcp notebook <QUERY> <OUTPUT_FILE> [OPTIONS]
```

### Parameters

- **`QUERY`**: Dune query SQL, query ID, or URL (required)
- **`OUTPUT_FILE`**: Path for generated notebook file (required)
- **`--chart-type`**: `"line"` (default) | `"bar"` | `"area"` — Initial chart type
- **`--no-open`**: Don't open notebook automatically (default: opens)
- **`--title`**: Custom notebook title (auto-generated if omitted)
- **`--description`**: Custom notebook description
- **`--markdown`**: Markdown text to seed the Notes section
- **`--max-rows`**: Override the maximum number of rows fetched (default: 500)

### Examples

```bash
# Basic Altair notebook (default)
spice-mcp notebook \
  "SELECT date, price FROM eth.prices ORDER BY date LIMIT 1000" \
  eth_price_analysis.py

# Area chart with custom title and description
spice-mcp notebook \
  "SELECT * FROM dex.trades WHERE token_address = '0x...' LIMIT 5000" \
  dex_volume.py \
  --chart-type area \
  --title "DEX Volume Analysis" \
  --description "Daily trading volume analysis"

# Custom title and description
spice-mcp notebook \
  "SELECT block_number, gas_used FROM eth.blocks ORDER BY block_number DESC LIMIT 500" \
  gas_analysis.py \
  --title "Ethereum Gas Usage Analysis" \
  --description "Recent Ethereum block gas usage trends with interactive charts"

# Generate without auto-opening
spice-mcp notebook "SELECT 1" test.py --no-open

# Use query ID instead of SQL
spice-mcp notebook "2759013" my_query.py --title "My Saved Query"
```

## 🤖 MCP Tool Workflow

Agents can skip the CLI entirely by calling the `dune_marimo` MCP tool. The tool runs the query, saves a parquet dataset + preview, writes a Marimo notebook under the configured reports directory, and optionally launches `marimo edit`.

### Basic Usage

```python
mcp__spice_mcp__dune_marimo({
  "query": "SELECT date_trunc('day', block_time) AS day, SUM(volume_usd) AS usd FROM dex.swaps GROUP BY 1 ORDER BY 1",
  "title": "Daily DEX Volume",
  "chart_type": "area",
  "template": "time_series",  # Auto-adds date range slider
  "max_rows": 1000
})
```

**Response fields**
- `report_path`: Marimo script path (e.g., `reports/notebooks/daily-dex-volume.py`)
- `data_path`: Matching parquet dataset path
- `preview`: First few rows so the agent can summarize results inline
- `chart_type`: Chart type used in the generated notebook
- `suggested_charts`: Array of 2-3 chart suggestions with executable code snippets
- `rows`: Number of rows in the dataset
- `columns`: List of column names
- `launch`: Whether Marimo was opened automatically and the command used
- `next_steps`: Copy/paste instruction (`marimo edit ...`) when manual launch is needed
- `session_warning`: Warning message if notebook is currently open in marimo (refresh operations only)

### Session-Aware Refresh

When refreshing a notebook that's currently open in marimo, spice-mcp will detect the active session and include a warning in the response:

```python
result = mcp__spice_mcp__dune_marimo({
    "action": "refresh",
    "report_path": "my_notebook.py"
})

# Response includes session_warning if notebook is active:
# {
#   "ok": True,
#   "report_path": "...",
#   "session_warning": "Notebook is currently open in marimo (session: abc123). Refreshing data may cause conflicts with active editing session."
# }
```

This helps prevent conflicts when refreshing data for notebooks that are actively being edited. See the [Marimo MCP Integration Guide](marimo_mcp_integration.md) for more details.

### Configuration

Set `SPICE_REPORTS_DIR`, `SPICE_REPORTS_MAX_ROWS`, `SPICE_REPORTS_OPEN_ON_CREATE`, and `SPICE_REPORTS_MARIMO_COMMAND` to customize output location, row cap, default launch behavior, and the marimo executable that should be invoked.

### 📐 Notebook Templates

**NEW in v0.2.0**: Spice-MCP now auto-generates template-specific notebooks based on your data characteristics. Each template includes optimized interactive controls and chart suggestions.

#### Template Types

1. **`auto` (recommended)**: Intelligently selects the best template based on data
   - Detects temporal patterns → `time_series`
   - Detects categorical + numeric → `comparison`
   - Detects multiple numerics → `distribution`

2. **`time_series`**: Optimized for temporal analysis
   - Auto-generated date range slider for filtering
   - Line/area chart suggestions
   - Ideal for: prices, volumes, metrics over time

3. **`comparison`**: Optimized for group comparisons
   - Auto-generated category multiselect filter
   - Bar chart suggestions with grouping
   - Ideal for: protocol comparisons, top N rankings, aggregates by category

4. **`distribution`**: Optimized for statistical analysis
   - Histogram and box plot layout
   - Scatter plot for correlation analysis
   - Ideal for: price distributions, gas analysis, statistical patterns

#### Template Detection Logic

The `auto` template uses smart heuristics:
- **Low-cardinality numerics treated as categorical** (e.g., year columns, status codes)
- **Temporal columns trigger time_series** if numeric metrics present
- **String columns + numerics trigger comparison** for group analysis
- **Multiple numeric columns trigger distribution** for statistical analysis

#### Example Usage

```python
# Auto-detect template (recommended)
mcp__spice_mcp__dune_marimo({
  "query": "SELECT date, price, volume FROM eth.prices",
  "title": "ETH Price Analysis",
  "template": "auto"  # Will detect time_series
})

# Explicit time series template
mcp__spice_mcp__dune_marimo({
  "query": "SELECT block_time, gas_price FROM eth.transactions LIMIT 10000",
  "title": "Gas Price Trends",
  "template": "time_series"
})

# Comparison template
mcp__spice_mcp__dune_marimo({
  "query": "SELECT protocol, SUM(volume) FROM dex.trades GROUP BY protocol",
  "title": "DEX Volume Comparison",
  "template": "comparison"
})

# Distribution analysis
mcp__spice_mcp__dune_marimo({
  "query": "SELECT gas_price, block_time FROM eth.transactions LIMIT 10000",
  "title": "Gas Distribution",
  "template": "distribution"
})
```

#### Suggested Charts

All templates return a `suggested_charts` array with 2-3 executable Altair code snippets:

```python
{
  "suggested_charts": [
    {
      "chart_type": "line",
      "x_axis": "date",
      "y_axis": "price",
      "title": "Price over time",
      "code_snippet": "alt.Chart(pdf).mark_line().encode(x='date', y='price').interactive()"
    },
    {
      "chart_type": "area",
      "x_axis": "date",
      "y_axis": "volume",
      "title": "Volume over time (area)",
      "code_snippet": "alt.Chart(pdf).mark_area().encode(x='date', y='volume').interactive()"
    }
  ]
}
```

Copy/paste these snippets directly into your Marimo notebook for instant visualizations.

### ⚡ Autorun Configuration

**NEW:** All generated notebooks include a `.marimo.toml` configuration file that enables **automatic execution on startup**. No manual button clicks needed!

#### What This Means

When you open a notebook:
1. ✅ All cells execute automatically
2. ✅ Data loads immediately  
3. ✅ Charts appear without interaction
4. ✅ Interactive controls are ready to use

**Before:** Open notebook → Click "autorun on startup" → Wait → See charts  
**Now:** Open notebook → Charts appear immediately ✨

#### Configuration File

**Location:** `reports/notebooks/.marimo.toml`

**Default Settings:**
```toml
[execution]
autorun = true          # Auto-execute all cells on startup

[display]
width = "full"          # Use full width for better chart display

[runtime]
auto_instantiate = true # Auto-load modules
```

#### Customization

To disable autorun (prefer manual execution):
```toml
[execution]
autorun = false  # Manually run cells with Shift+Enter
```

**Note:** The config file applies to all notebooks in the directory and is only created once. If you have a custom config, it will never be overwritten.

## 📊 Generated Notebooks

### Notebook Structure

Generated notebooks include:

1. **Header with title and description**
2. **Imports** for Marimo, Polars, Pandas, and Altair
3. **Data loading cell** that reads from the parquet file
4. **Data preview section** showing first 10 rows
5. **Basic chart** with auto-selected axes based on data types
6. **Notes section** with customization tips

The generated notebook is minimal by design—users customize it interactively in Marimo's UI.

## 🎨 Customizing in Marimo

After generating a starter notebook, open it in Marimo's UI to customize interactively. The generated notebook provides a foundation—add charts, filters, and layouts using Marimo's built-in components.

### Adding Charts

The generated notebook includes one starter chart. Add more charts by creating new cells:

```python
@app.cell
def _(alt, pdf, COLUMNS):
    # Add a second chart
    chart_type_2 = mo.ui.dropdown(["line", "bar", "area"], value="bar")
    x_axis_2 = mo.ui.dropdown(COLUMNS, value="date")
    y_axis_2 = mo.ui.dropdown(COLUMNS, value="volume")
    
    def create_chart_2(chart_t: str, x: str, y: str) -> alt.Chart:
        base_chart = alt.Chart(pdf)
        mark_methods = {
            "line": lambda c: c.mark_line(),
            "bar": lambda c: c.mark_bar(),
            "area": lambda c: c.mark_area(),
        }
        chart = mark_methods.get(chart_t, lambda c: c.mark_line())(base_chart)
        return chart.encode(x=x, y=y).interactive()
    
    chart_2 = create_chart_2(chart_type_2.value, x_axis_2.value, y_axis_2.value)
    return chart_type_2, x_axis_2, y_axis_2, chart_2

@app.cell
def _(chart_2):
    chart_2  # Display the second chart
    return
```

### Adding Filters

Add interactive filters using Marimo UI components:

```python
@app.cell
def _(mo, pdf):
    # Date range filter
    start_date = mo.ui.date(value="2024-01-01", label="Start Date")
    end_date = mo.ui.date(value="2024-12-31", label="End Date")
    
    # Numeric filter
    min_volume = mo.ui.slider(
        start=0,
        stop=1000000,
        step=1000,
        value=10000,
        label="Minimum Volume"
    )
    
    return start_date, end_date, min_volume

@app.cell
def _(pdf, start_date, end_date, min_volume):
    # Apply filters to data
    filtered_df = pdf.filter(
        (pl.col("date") >= start_date.value) &
        (pl.col("date") <= end_date.value) &
        (pl.col("volume") >= min_volume.value)
    )
    return filtered_df
```

### Creating Layouts

Use Marimo's layout components to organize multiple charts:

```python
@app.cell
def _(mo, chart_1, chart_2):
    # Horizontal layout (side by side)
    mo.hstack([chart_1, chart_2])
    return

@app.cell
def _(mo, chart_1, chart_2, chart_3):
    # Vertical layout (stacked)
    mo.vstack([chart_1, chart_2, chart_3])
    return

@app.cell
def _(mo, chart_1, chart_2):
    # Grid layout (2 columns)
    mo.hstack([
        mo.vstack([chart_1]),
        mo.vstack([chart_2])
    ])
    return
```

### Using Marimo's Grid Editor

Marimo's UI includes a visual grid editor for arranging cells:

1. Open the notebook in Marimo: `marimo edit notebook.py`
2. Click the grid icon in the toolbar
3. Drag and drop cells to rearrange them
4. Resize cells by dragging their borders
5. Create multi-column layouts visually

For more advanced customization, see the [Marimo Documentation](https://marimo.io/).

## 🎨 Chart Library Support

### Altair (Default)
```bash
spice-mcp notebook "SELECT * FROM test" analysis.py --chart-type altair
```

**Features**:
- Native Polars DataFrame compatibility
- Reactive charts with zooming and selection
- Multiple chart types: line, bar, scatter, area, histogram
- Automatic tooltips and interactive legends
- VegaFusion integration for client-side rendering

**Example Output**:
```python
# Interactive Altair chart
create_altair_chart(chart_type.value, x_axis.value, y_axis.value)
```

### Plotly
```bash
spice-mcp notebook "SELECT * FROM test" analysis.py --chart-type plotly
```

**Features**:
- High-performance rendering for large datasets
- 3D chart support
- Statistical chart types (violin, box, etc.)
- Export capabilities (PNG, SVG, HTML)

### Marimo Built-in
```bash
spice-mcp notebook "SELECT * FROM test" analysis.py --chart-type builtin
```

**Features**:
- No external dependencies (works with base Marimo)
- Simple table and statistics views
- Polars expression filtering
- Lightweight and fast

## 🛠️ Troubleshooting

### Marimo Not Installed

```bash
# Error: 'marimo' command not found
# Solution:
pip install 'spice-mcp[reports]'
```

### Query Execution Issues

```bash
# Problem: Query fails during notebook generation
# Solutions:
# 1. Use simple queries first to test connection
spice-mcp notebook "SELECT 1" test.py

# 2. Verify query with dune_data tool first
# 3. Check query syntax and table names

# Problem: Large queries timeout
# Solution: Add LIMIT clause to test data
spice-mcp notebook "SELECT * FROM large_table LIMIT 1000" test.py
```

### Chart Rendering Issues

```bash
# Problem: Altair charts don't render
# Solution: Ensure vegafusion is installed
pip install vegafusion

# Problem: Slow chart performance  
# Solution: Use smaller datasets or builtin charts
spice-mcp notebook "SELECT * FROM table LIMIT 1000" test.py --chart-type builtin
```

### Notebook Syntax Errors

```python
# Test generated notebook syntax
python my_notebook.py --check  # Marimo syntax checking

# Or use Marimo built-in validation
marimo check my_notebook.py
```

### Blank Notebook Display

**Issue**: Notebook opens but displays blank/empty cells.

**Root Cause**: Marimo 0.17+ requires notebooks to use `@app.cell` decorators, NOT `# %%` cell markers (Jupyter-style).

**Solution**: The scaffolder has been updated to generate proper Marimo 0.17+ format. If you encounter blank notebooks:

1. **Verify Marimo version**: `marimo --version` should be 0.17+
2. **Check notebook format**: Open the `.py` file and verify it uses `@app.cell` decorators
3. **Regenerate notebook**: Delete the old notebook and create a new one using the updated scaffolder

**Example of correct format**:
```python
import marimo

__generated_with = "0.17.7"
app = marimo.App()

@app.cell
def _():
    import marimo as mo
    import polars as pl
    return mo, pl

@app.cell
def _(mo, pl):
    df = pl.read_parquet("data.parquet")
    mo.md(f"Loaded {len(df)} rows")
    return df
```

**Example of incorrect format** (will show blank):
```python
# %% [python]  # ❌ Wrong - Jupyter-style markers
import marimo as mo
```

The scaffolder automatically generates the correct format, so this should not occur with newly created notebooks.

## 🧪 Testing Integration

### Unit Tests

The scaffolder includes comprehensive tests:

```bash
# Run all notebook tests
python -m pytest tests/notebooks/ -v

# Run specific test files
python -m pytest tests/notebooks/test_marimo_scaffolder.py -v
python -m pytest tests/notebooks/test_marimo_integration.py -v
python -m pytest tests/notebooks/test_cli_integration.py -v
```

### Manual Testing

```bash
# Generate test notebook without opening
spice-mcp notebook "SELECT 1" test.py --no-open

# Verify notebook runs
marimo edit test.py

# Check output
python test.py --check
```

### Integration Testing

```python
# Test different chart types
spice-mcp notebook "SELECT 1" altair_test.py --chart-type altair
spice-mcp notebook "SELECT 1" plotly_test.py --chart-type plotly
spice-mcp notebook "SELECT 1" builtin_test.py --chart-type builtin

# Test with real data
spice-mcp notebook "SELECT block_number, gas_used FROM eth.blocks LIMIT 100" gas_test.py
```

## 🚀 Best Practices

### Query Design

1. **Test Queries First**: Verify queries with `dune_data` before scaffolding
2. **Use Reasonable Limits**: Start with 1000-5000 rows for performance
3. **Select Relevant Columns**: Only include columns you'll actually visualize
4. **Order Results**: Use ORDER BY for time-series charts

```sql
-- Good practice
SELECT date, price, volume 
FROM eth.prices 
WHERE date >= '2023-01-01' 
ORDER BY date 
LIMIT 5000

-- Less ideal for notebook
SELECT * FROM large_table  -- Too many columns
```

### Notebook Organization

```python
# Let scaffolder create structure
spice_mcp notebook "..." analysis.py

# Then customize interactively in Marimo
# - Add additional analysis cells
# - Customize chart configurations
# - Add documentation cells
# - Create dashboard layouts
```

### Iterative Development

```bash
# 1. Start with simple query and small dataset
spice-mcp notebook "SELECT date, price FROM eth.prices LIMIT 100" test_v1.py

# 2. Expand functionality
spice-mcp notebook "SELECT date, price, volume FROM eth.prices LIMIT 1000" test_v2.py

# 3. Add customizations in Marimo editor
marimo edit test_v2.py
```

## 📚 Examples

### Basic Time Series

```bash
spice-mcp notebook \
  "SELECT date, price FROM eth.prices ORDER BY date LIMIT 1000" \
  eth_price_analysis.py \
  --title "Ethereum Price Analysis" \
  --description "Daily ETH price trends with interactive charts"
```

### Multi-Table Analysis

```bash
spice-mcp notebook \
  "SELECT b.block_number, b.gas_used, t.gas_price 
   FROM eth.blocks b 
   JOIN eth.transactions t ON b.block_hash = t.block_hash 
   ORDER BY b.block_number DESC LIMIT 2000" \
  gas_analysis.py \
  --title "Ethereum Gas Analysis"
```

### DEX Volume Dashboard

```bash
spice-mcp notebook \
  "SELECT date, volume_usd, token_symbol, blockchain 
   FROM dex.trades 
   WHERE date >= '2023-01-01' 
   ORDER BY date DESC LIMIT 5000" \
  dex_dashboard.py \
  --title "DEX Trading Volume" \
  --description "Cross-DEX trading volume analysis"
```

## 🔗 Resources

- [Marimo Documentation](https://marimo.io/)
- [Altair Documentation](https://altair-viz.github.io/)
- [Plotly Documentation](https://plotly.com/python/)
- [Polars Documentation](https://pola.rs/)
- [spice-mcp Repository](https://github.com/Evan-Kim2028/spice-mcp)
