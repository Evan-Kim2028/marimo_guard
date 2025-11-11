from __future__ import annotations

from typing import Any, Optional


def render_plotly_safe(mo: Any, fig: Any, *, name: str = "plotly_chart", include_js: str = "cdn", register: bool = True) -> Any:
    """Render a Plotly figure robustly in Marimo.

    Tries marimo's native plotly UI wrapper first; on failure, falls back to
    embedding HTML that includes a Plotly JS reference so the chart renders
    without relying on the front-end environment.
    """
    if register:
        try:
            from .chart_registry import register_chart

            register_chart(name, fig, lib="plotly", meta={"wrapper": "render_plotly_safe"})
        except Exception:
            pass

    try:
        if hasattr(mo.ui, "plotly"):
            return mo.ui.plotly(fig)
    except Exception:
        pass

    try:
        import plotly.io as pio  # type: ignore

        html = pio.to_html(fig, include_plotlyjs=include_js, full_html=False)
        try:
            return mo.ui.html(html)
        except Exception:
            return getattr(mo, "Html")(html)
    except Exception as e:  # pragma: no cover
        return mo.md(f"Plotly render error: {e}")


def render_bokeh_safe(mo: Any, model: Any, *, name: str = "bokeh_chart", register: bool = True) -> Any:
    """Render a Bokeh model robustly in Marimo via inline HTML embedding."""
    if register:
        try:
            from .chart_registry import register_chart

            register_chart(name, model, lib="bokeh", meta={"wrapper": "render_bokeh_safe"})
        except Exception:
            pass

    try:
        from bokeh.embed import file_html  # type: ignore
        from bokeh.resources import CDN  # type: ignore

        html = file_html(model, CDN, title=name)
        return mo.ui.html(html)
    except Exception as e:  # pragma: no cover
        return mo.md(f"Bokeh render error: {e}")


def render_holoviews_safe(mo: Any, hv_obj: Any, *, name: str = "hv_chart", register: bool = True) -> Any:
    """Render a HoloViews object using Bokeh backend into Marimo.

    Falls back to exporting static HTML and embedding if needed.
    """
    if register:
        try:
            from .chart_registry import register_chart

            register_chart(name, hv_obj, lib="holoviews", meta={"wrapper": "render_holoviews_safe"})
        except Exception:
            pass

    try:
        import holoviews as hv  # type: ignore
        hv.extension("bokeh")
        # Attempt to get static HTML via bokeh renderer
        renderer = hv.renderer("bokeh")
        html = renderer.static_html(hv_obj)
        return mo.ui.html(html)
    except Exception as e:
        return mo.md(f"HoloViews render error: {e}")


def render_pyecharts_safe(mo: Any, chart: Any, *, name: str = "echarts", register: bool = True) -> Any:
    """Render a Pyecharts chart via embedded HTML."""
    if register:
        try:
            from .chart_registry import register_chart

            register_chart(name, chart, lib="pyecharts", meta={"wrapper": "render_pyecharts_safe"})
        except Exception:
            pass

    try:
        html = chart.render_embed()
        return mo.ui.html(html)
    except Exception as e:
        return mo.md(f"Pyecharts render error: {e}")

