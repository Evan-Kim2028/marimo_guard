# Marimo Customization Guide

After generating a starter notebook with `spice-mcp notebook` or the `dune_marimo` tool, customize it interactively in Marimo's UI. This guide covers common customization tasks.

## Opening Your Notebook

```bash
# Open the generated notebook
marimo edit reports/notebooks/your_notebook.py
```

The notebook opens in your browser with an interactive editor. All changes are saved automatically.

## Adding Charts

The generated notebook includes one starter chart. Add more charts by creating new cells in Marimo's UI.

### Adding a New Chart Cell

1. Click the "+" button to add a new cell
2. Select "Code" cell type
3. Add chart code:

```python
@app.cell
def _(alt, pdf, COLUMNS):
    # Chart configuration controls
    chart_type_2 = mo.ui.dropdown(["line", "bar", "area"], value="bar")
    x_axis_2 = mo.ui.dropdown(COLUMNS, value="date")
    y_axis_2 = mo.ui.dropdown(COLUMNS, value="volume")
    
    # Chart creation function
    def create_chart_2(chart_t: str, x: str, y: str) -> alt.Chart:
        base_chart = alt.Chart(pdf)
        mark_methods = {
            "line": lambda c: c.mark_line(),
            "bar": lambda c: c.mark_bar(),
            "area": lambda c: c.mark_area(),
        }
        chart = mark_methods.get(chart_t, lambda c: c.mark_line())(base_chart)
        return chart.encode(x=x, y=y).interactive()
    
    # Create and return chart
    chart_2 = create_chart_2(chart_type_2.value, x_axis_2.value, y_axis_2.value)
    return chart_type_2, x_axis_2, y_axis_2, chart_2

@app.cell
def _(chart_2):
    chart_2  # Display the chart
    return
```

### Chart Types

Supported Altair chart types:
- **Line charts**: `c.mark_line()` - Best for time series
- **Bar charts**: `c.mark_bar()` - Best for categorical data
- **Area charts**: `c.mark_area()` - Best for cumulative data
- **Scatter plots**: `c.mark_circle()` - Best for correlations

Example scatter plot:
```python
@app.cell
def _(alt, pdf):
    scatter_chart = alt.Chart(pdf).mark_circle().encode(
        x="price",
        y="volume",
        size="count",
        color="category"
    ).interactive()
    return scatter_chart
```

## Adding Filters

Add interactive filters to filter your data dynamically.

### Date Filters

```python
@app.cell
def _(mo):
    # Date range filter
    start_date = mo.ui.date(value="2024-01-01", label="Start Date")
    end_date = mo.ui.date(value="2024-12-31", label="End Date")
    return start_date, end_date

@app.cell
def _(pdf, start_date, end_date):
    # Apply date filter
    filtered_df = pdf.filter(
        (pl.col("date") >= start_date.value) &
        (pl.col("date") <= end_date.value)
    )
    return filtered_df
```

### Numeric Filters (Slider)

```python
@app.cell
def _(mo):
    # Slider for numeric range
    min_volume = mo.ui.slider(
        start=0,
        stop=1000000,
        step=1000,
        value=10000,
        label="Minimum Volume"
    )
    
    max_price = mo.ui.slider(
        start=0,
        stop=10000,
        step=100,
        value=5000,
        label="Maximum Price"
    )
    return min_volume, max_price

@app.cell
def _(pdf, min_volume, max_price):
    # Apply numeric filters
    filtered_df = pdf.filter(
        (pl.col("volume") >= min_volume.value) &
        (pl.col("price") <= max_price.value)
    )
    return filtered_df
```

### Numeric Filters (Number Input)

```python
@app.cell
def _(mo):
    # Number input for exact values
    threshold = mo.ui.number(
        start=0,
        stop=1000000,
        step=100,
        value=50000,
        label="Volume Threshold"
    )
    return threshold

@app.cell
def _(pdf, threshold):
    # Filter by threshold
    filtered_df = pdf.filter(pl.col("volume") >= threshold.value)
    return filtered_df
```

### Dropdown Filters

```python
@app.cell
def _(mo, pdf):
    # Get unique values for dropdown
    categories = pdf["category"].unique().to_list()
    
    # Multi-select dropdown
    selected_categories = mo.ui.multiselect(
        options=categories,
        value=categories[:3],  # Default to first 3
        label="Select Categories"
    )
    return selected_categories

@app.cell
def _(pdf, selected_categories):
    # Filter by selected categories
    filtered_df = pdf.filter(
        pl.col("category").is_in(selected_categories.value)
    )
    return filtered_df
```

### Text Input Filters

```python
@app.cell
def _(mo):
    # Text search filter
    search_term = mo.ui.text(
        value="",
        label="Search Token Symbol",
        placeholder="Enter token symbol..."
    )
    return search_term

@app.cell
def _(pdf, search_term):
    # Filter by text search
    if search_term.value:
        filtered_df = pdf.filter(
            pl.col("token_symbol").str.contains(search_term.value, literal=False)
        )
    else:
        filtered_df = pdf
    return filtered_df
```

## Creating Layouts

Organize multiple charts and components using Marimo's layout functions.

### Horizontal Layout (Side by Side)

```python
@app.cell
def _(mo, chart_1, chart_2):
    # Place charts side by side
    mo.hstack([chart_1, chart_2])
    return
```

### Vertical Layout (Stacked)

```python
@app.cell
def _(mo, chart_1, chart_2, chart_3):
    # Stack charts vertically
    mo.vstack([chart_1, chart_2, chart_3])
    return
```

### Grid Layout (Multi-Column)

```python
@app.cell
def _(mo, chart_1, chart_2, chart_3, chart_4):
    # 2x2 grid layout
    mo.hstack([
        mo.vstack([chart_1, chart_3]),
        mo.vstack([chart_2, chart_4])
    ])
    return
```

### Mixed Layouts

```python
@app.cell
def _(mo, filters, chart_1, chart_2, stats):
    # Filters on top, charts side by side, stats below
    mo.vstack([
        filters,  # Filter controls
        mo.hstack([chart_1, chart_2]),  # Charts side by side
        stats  # Statistics below
    ])
    return
```

## Using Marimo's Grid Editor

Marimo includes a visual grid editor for arranging cells:

1. **Enable Grid Mode**: Click the grid icon in the toolbar (or press `G`)
2. **Rearrange Cells**: Drag and drop cells to reorder them
3. **Resize Cells**: Drag cell borders to resize
4. **Create Columns**: Drag cells to create multi-column layouts
5. **Exit Grid Mode**: Click the grid icon again or press `Esc`

### Grid Editor Tips

- **Snap to Grid**: Cells automatically align to a grid
- **Multi-Select**: Hold `Shift` and click to select multiple cells
- **Column Width**: Drag column borders to adjust width
- **Row Height**: Drag row borders to adjust height

## Adding Markdown Documentation

Add markdown cells to document your analysis:

```python
@app.cell
def _(mo):
    mo.md("""
    # Analysis Title
    
    This notebook analyzes [description].
    
    ## Key Findings
    
    - Finding 1
    - Finding 2
    - Finding 3
    """)
    return
```

### Markdown with Variables

```python
@app.cell
def _(mo, pdf):
    row_count = len(pdf)
    mo.md(f"""
    # Data Overview
    
    Loaded **{row_count:,}** rows of data.
    
    Use the filters below to explore the data.
    """)
    return
```

## Adding Data Transformations

Add cells to transform and analyze your data:

```python
@app.cell
def _(pdf):
    # Calculate summary statistics
    summary = pdf.select([
        pl.col("price").mean().alias("avg_price"),
        pl.col("volume").sum().alias("total_volume"),
        pl.col("date").min().alias("start_date"),
        pl.col("date").max().alias("end_date"),
    ])
    return summary

@app.cell
def _(mo, summary):
    # Display summary
    mo.md(f"""
    ## Summary Statistics
    
    - Average Price: ${summary['avg_price'][0]:,.2f}
    - Total Volume: {summary['total_volume'][0]:,.0f}
    - Date Range: {summary['start_date'][0]} to {summary['end_date'][0]}
    """)
    return
```

## Best Practices

### 1. Organize Cells Logically

- **Data Loading**: Keep data loading cells at the top
- **Filters**: Group filter controls together
- **Transformations**: Place data transformations after filters
- **Charts**: Group related charts together
- **Documentation**: Add markdown cells to explain sections

### 2. Use Descriptive Variable Names

```python
# Good
daily_volume_chart = create_chart(...)
price_trend_chart = create_chart(...)

# Less clear
chart1 = create_chart(...)
chart2 = create_chart(...)
```

### 3. Return Variables Explicitly

Always return variables needed by other cells:

```python
@app.cell
def _(pdf):
    filtered_df = pdf.filter(...)
    return filtered_df  # Must return to use in other cells
```

### 4. Handle Empty Data

Add checks for empty dataframes:

```python
@app.cell
def _(mo, filtered_df):
    if len(filtered_df) == 0:
        mo.md("⚠️ No data matches the current filters.")
    else:
        mo.md(f"✅ Showing {len(filtered_df)} rows")
    return
```

### 5. Use Reactive Updates

Marimo automatically updates dependent cells when inputs change. Design your cells to take advantage of this:

```python
# Chart automatically updates when filters change
@app.cell
def _(filtered_df, x_axis, y_axis):
    chart = create_chart(filtered_df, x_axis.value, y_axis.value)
    return chart
```

## Common Patterns

### Filtered Chart Pattern

```python
# 1. Define filters
@app.cell
def _(mo):
    date_range = mo.ui.date_range(...)
    return date_range

# 2. Apply filters
@app.cell
def _(pdf, date_range):
    filtered_df = pdf.filter(...)
    return filtered_df

# 3. Create chart from filtered data
@app.cell
def _(filtered_df):
    chart = create_chart(filtered_df, ...)
    return chart
```

### Multi-Chart Dashboard Pattern

```python
# 1. Load data
@app.cell
def _():
    df = pl.read_parquet("data.parquet")
    return df

# 2. Create multiple charts
@app.cell
def _(df):
    chart1 = create_chart1(df)
    chart2 = create_chart2(df)
    chart3 = create_chart3(df)
    return chart1, chart2, chart3

# 3. Layout charts
@app.cell
def _(mo, chart1, chart2, chart3):
    mo.hstack([
        mo.vstack([chart1, chart2]),
        chart3
    ])
    return
```

## Resources

- [Marimo Documentation](https://marimo.io/) - Official Marimo docs
- [Marimo UI Components](https://docs.marimo.io/api/inputs/) - Complete list of UI components
- [Marimo Layout Guide](https://docs.marimo.io/guides/layouts/) - Layout patterns and examples
- [Altair Documentation](https://altair-viz.github.io/) - Chart library documentation
- [Polars Documentation](https://pola.rs/) - DataFrame operations

## Getting Help

- **Marimo Issues**: [GitHub Issues](https://github.com/marimo-team/marimo/issues)
- **spice-mcp Issues**: [GitHub Issues](https://github.com/Evan-Kim2028/spice-mcp/issues)
- **Marimo Discord**: [Join the Community](https://discord.gg/marimo)

