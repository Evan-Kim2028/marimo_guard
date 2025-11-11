from __future__ import annotations

"""Lightweight chart registry for guard validation.

Notebooks can call ``register_chart(name, obj, lib=...)`` in chart cells.
The safeguard then imports the registry and validates registered charts
precisely, yielding better diagnostics than module-wide scanning.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ChartEntry:
    name: str
    obj: Any
    lib: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


_REGISTRY: List[ChartEntry] = []


def clear_registry() -> None:
    del _REGISTRY[:]


def _infer_lib(obj: Any) -> str:
    mod = getattr(obj.__class__, "__module__", "")
    if mod.startswith("altair"):
        return "altair"
    if mod.startswith("plotly"):
        return "plotly"
    if mod.startswith("bokeh"):
        return "bokeh"
    if mod.startswith("matplotlib"):
        return "matplotlib"
    if mod.startswith("holoviews"):
        return "holoviews"
    if mod.startswith("pyecharts"):
        return "pyecharts"
    if mod.startswith("folium"):
        return "folium"
    if mod.startswith("pydeck"):
        return "pydeck"
    if mod.startswith("plotnine"):
        return "plotnine"
    if mod.startswith("graphviz"):
        return "graphviz"
    return mod or "unknown"


def register_chart(name: str, obj: Any, *, lib: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None:
    entry = ChartEntry(name=name, obj=obj, lib=lib or _infer_lib(obj), meta=meta)
    _REGISTRY.append(entry)


def register_altair(name: str, chart: Any, *, meta: Optional[Dict[str, Any]] = None) -> None:
    register_chart(name, chart, lib="altair", meta=meta)


def register_plotly(name: str, fig: Any, *, meta: Optional[Dict[str, Any]] = None) -> None:
    register_chart(name, fig, lib="plotly", meta=meta)


def register_bokeh(name: str, model: Any, *, meta: Optional[Dict[str, Any]] = None) -> None:
    register_chart(name, model, lib="bokeh", meta=meta)


def snapshot_registry() -> List[ChartEntry]:
    return list(_REGISTRY)


def describe_registry() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in _REGISTRY:
        d = asdict(ChartEntry(name=e.name, obj="<object>", lib=e.lib, meta=e.meta))
        out.append(d)
    return out

