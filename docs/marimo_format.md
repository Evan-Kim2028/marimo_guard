# Marimo Notebook Format Guide

## Overview

spice-mcp generates Marimo notebooks for interactive data visualization. This document explains the notebook format requirements and troubleshooting.

## ⚠️ Critical Format Requirement

**Marimo 0.17+ requires notebooks to use `@app.cell` decorators, NOT Jupyter-style `# %%` cell markers.**

Using `# %%` markers will result in blank notebooks that don't display properly. Always use `@app.cell` decorators.

## Format Requirements

### Marimo 0.17+ Format

Marimo 0.17+ requires notebooks to use `@app.cell` decorators, **NOT** Jupyter-style `# %%` cell markers.

#### ✅ Correct Format (Marimo 0.17+)

**Always use `@app.cell` decorators:**

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
    df.head(10)
    return df

if __name__ == "__main__":
    app.run()
```

**Key points:**
- Every cell must be a function decorated with `@app.cell`
- Dependencies are declared via function parameters
- Variables must be returned to be available to other cells
- `app = marimo.App()` must be defined at the top

#### ❌ Incorrect Format (Jupyter-style - will show blank)

**Never use `# %%` markers - they will cause blank notebooks:**

```python
# %% [markdown]  # ❌ WRONG - Will not work in Marimo 0.17+
"""
# Title
"""

# %% [python]  # ❌ WRONG - Will not work in Marimo 0.17+
import marimo as mo
import polars as pl

df = pl.read_parquet("data.parquet")
```

**Why this fails:**
- Marimo 0.17+ doesn't recognize `# %%` markers
- Notebook will open but display blank/empty cells
- No error messages - just empty display

## Key Differences

| Aspect | Jupyter `# %%` | Marimo `@app.cell` |
|--------|----------------|-------------------|
| Cell marker | `# %% [python]` | `@app.cell` decorator |
| Cell function | Not required | Must be a function |
| Dependencies | Implicit | Explicit via function parameters |
| Returns | Not required | Must return exported variables |
| App definition | Not needed | `app = marimo.App()` required |

## Scaffolder Implementation

The `MarimoNotebookScaffolder` class generates proper Marimo 0.17+ format:

```python
from spice_mcp.notebooks.scaffolder import MarimoNotebookScaffolder

scaffolder = MarimoNotebookScaffolder(query_service, reports_root)
result = scaffolder.create_report(spec)
```

### Generated Structure

1. **App initialization**: `import marimo` and `app = marimo.App()`
2. **Import cell**: All required libraries
3. **Data loading cell**: Path configuration and data loading
4. **Content cells**: Markdown, charts, analysis (each as `@app.cell`)
5. **App runner**: `if __name__ == "__main__": app.run()`

### Cell Dependencies

Marimo cells declare dependencies via function parameters:

```python
@app.cell
def _(df, mo):  # Depends on 'df' and 'mo'
    mo.md(f"Rows: {len(df)}")
    return
```

Variables must be returned to be available to other cells:

```python
@app.cell
def _():
    df = pl.read_parquet("data.parquet")
    return df  # Export 'df' for other cells
```

## Troubleshooting

### Blank Notebook Display

**Symptoms**: Notebook opens in browser but shows empty/blank cells.

**Most Common Cause**: Using `# %%` markers instead of `@app.cell` decorators.

**Causes**:
1. ❌ **Using old `# %%` format instead of `@app.cell`** (most common)
2. Missing `app = marimo.App()` definition
3. Cells not returning exported variables
4. Syntax errors preventing execution

**Solutions**:
1. **Verify notebook uses `@app.cell` decorators** - Check the `.py` file directly
2. Check for `app = marimo.App()` at the top
3. Ensure all cells return their exports
4. Run `marimo check notebook.py` to validate syntax

**Quick Check**:
```bash
# Check if notebook uses correct format
grep -n "@app.cell" notebook.py  # Should find decorators
grep -n "# %%" notebook.py       # Should NOT find Jupyter markers
```

### Cell Execution Errors

**Symptoms**: Cells show error messages or don't execute.

**Common Issues**:
- Missing imports in dependency chain
- Variables not returned from previous cells
- Circular dependencies between cells

**Solution**: Check the cell dependency graph in Marimo's UI (shows which cells depend on which).

### Import Errors

**Symptoms**: `ModuleNotFoundError` when opening notebook.

**Solution**: Install required dependencies:
```bash
pip install marimo altair polars pandas
```

## Best Practices

1. **Always use the scaffolder**: Don't manually create notebooks - use `MarimoNotebookScaffolder`
2. **Check Marimo version**: Ensure `marimo >= 0.17.0`
3. **Test generated notebooks**: Run `marimo edit notebook.py` to verify
4. **Follow cell structure**: Each logical section should be a separate `@app.cell`
5. **Return exports**: Always return variables needed by other cells

## Migration from Old Format

If you have notebooks using `# %%` markers:

1. **Regenerate**: Use the scaffolder to create a new notebook
2. **Manual conversion**: Convert each `# %%` cell to `@app.cell`:
   ```python
   # Old:
   # %% [python]
   df = load_data()
   
   # New:
   @app.cell
   def _():
       df = load_data()
       return df
   ```

## References

- [Marimo Documentation](https://docs.marimo.io/)
- [Marimo Cell Model](https://docs.marimo.io/guides/cells/)
- [spice-mcp Scaffolder Source](../src/spice_mcp/notebooks/scaffolder.py)

