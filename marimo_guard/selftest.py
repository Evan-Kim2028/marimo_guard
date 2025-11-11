from __future__ import annotations

import argparse
from pathlib import Path


def find_dataset_paths(nb: Path) -> list[Path]:
    candidates: list[Path] = []
    candidates.append(nb.parent / "data" / f"{nb.stem}.parquet")
    candidates.append(nb.parent.parent / "data" / f"{nb.stem}.parquet")
    root = nb.resolve()
    for p in [root] + list(root.parents):
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            candidates.append(p / "reports" / "data" / f"{nb.stem}.parquet")
            break
    return candidates


def run_selftest(nb_path: str) -> int:
    from marimo_guard.notebooks.marimo_helpers import write_selftest_artifact
    import polars as pl
    import altair as alt
    import datetime as dt

    nb = Path(nb_path).resolve()
    errors: list[str] = []

    ds_path = None
    for cand in find_dataset_paths(nb):
        if cand.exists():
            ds_path = cand
            break
    if not ds_path:
        errors.append("dataset not found for notebook")
        write_selftest_artifact(nb, ok=False, errors=errors)
        return 1

    try:
        df = pl.read_parquet(ds_path)
    except Exception as e:
        errors.append(f"failed to read dataset: {e}")
        write_selftest_artifact(nb, ok=False, errors=errors)
        return 1

    # Generic shape checks; allow different schemas
    if df.height == 0:
        errors.append("empty dataset")

    # Temporal window sanity if a 'day' column exists
    if "day" in df.columns:
        try:
            try:
                df_cast = df.with_columns(pl.col("day").cast(pl.Date))
            except Exception:
                df_cast = df.with_columns(pl.col("day").str.strptime(pl.Date, strict=False))
            anchor = dt.date.today()
            start = anchor - dt.timedelta(days=55)
            df_8w = df_cast.filter((pl.col("day") >= start) & (pl.col("day") <= anchor))
            if df_8w.height == 0:
                errors.append("no rows in last-8-weeks window")
        except Exception as e:
            errors.append(f"temporal window check exception: {e}")

    # Altair serialization sanity on a small subset if possible
    try:
        sample_cols = df.columns[: min(3, len(df.columns))]
        if sample_cols:
            d = df.head(50).to_dicts()
            enc = {}
            if len(sample_cols) >= 1:
                enc["x"] = f"{sample_cols[0]}:N"
            if len(sample_cols) >= 2:
                enc["y"] = f"{sample_cols[1]}:Q"
            chart = alt.Chart(alt.Data(values=d)).mark_bar().encode(**enc)
            _ = chart.to_dict(validate=True)
    except Exception as e:
        errors.append(f"altair serialization failed: {e}")

    write_selftest_artifact(nb, ok=not errors, errors=errors)
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("notebook")
    args = p.parse_args(argv)
    return run_selftest(args.notebook)


if __name__ == "__main__":
    raise SystemExit(main())

