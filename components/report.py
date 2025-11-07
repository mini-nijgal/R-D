from __future__ import annotations

import base64
from io import BytesIO
from typing import Tuple

import pandas as pd

# Plotly import - required for report generation
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    px = None  # type: ignore


def _fig_to_base64_png(fig) -> str:
    png = fig.to_image(format="png", scale=2)
    return base64.b64encode(png).decode("ascii")


def _build_kpis(df: pd.DataFrame) -> Tuple[int, int, int, int]:
    total = len(df)
    status_col = "Status" if "Status" in df.columns else ("status" if "status" in df.columns else None)
    active = completed = pending = 0
    if status_col:
        vals = df[status_col].astype(str).str.lower()
        active = int(vals.isin(["active", "in progress", "in-progress", "ongoing"]).sum())
        completed = int(vals.isin(["done", "completed", "closed", "finished"]).sum())
        pending = int(vals.isin(["pending", "backlog", "todo", "paused", "blocked"]).sum())
    return total, active, completed, pending


def _status_chart(df: pd.DataFrame):
    col = "Status" if "Status" in df.columns else ("status" if "status" in df.columns else None)
    if not col:
        return None
    counts = df[col].value_counts().reset_index()
    counts.columns = ["status", "count"]
    return px.pie(counts, values="count", names="status", hole=0.4, title="Tickets by Status")


def _client_chart(df: pd.DataFrame):
    agg = {}
    for c in df.columns:
        if any(k in c.lower() for k in ["client", "customer", "account", "keyword", "tag"]):
            for v in df[c].fillna("").astype(str):
                for p in [s.strip() for s in v.replace(";", ",").split(",") if s.strip()]:
                    agg[p] = agg.get(p, 0) + 1
    if not agg:
        return None
    dd = pd.DataFrame({"client": list(agg.keys()), "count": list(agg.values())}).sort_values("count", ascending=False)
    return px.bar(dd, x="client", y="count", title="Tickets by Client")


def _timeline_chart(df: pd.DataFrame):
    start = next((c for c in df.columns if "start" in c.lower() or c.lower() == "date"), None)
    end = next((c for c in df.columns if "end" in c.lower()), None)
    label = next((c for c in df.columns if c.lower() in ("project", "name", "title")), df.columns[0] if len(df.columns) else None)
    if not start or not label:
        return None
    tdf = df.copy()
    tdf["start"] = pd.to_datetime(tdf[start], errors="coerce")
    tdf["end"] = pd.to_datetime(tdf[end], errors="coerce") if end else tdf["start"]
    tdf = tdf.dropna(subset=["start"]) 
    if tdf.empty:
        return None
    fig = px.timeline(tdf, x_start="start", x_end="end", y=label, title="Ticket Timeline")
    fig.update_yaxes(autorange="reversed")
    return fig


def _trend_chart(df: pd.DataFrame):
    date_col = next((c for c in df.columns if "date" in c.lower() or c.lower() in ("created", "start")), None)
    if not date_col:
        return None
    tdf = df.copy()
    tdf["dt"] = pd.to_datetime(tdf[date_col], errors="coerce")
    tdf = tdf.dropna(subset=["dt"]) 
    if tdf.empty:
        return None
    tdf["month"] = tdf["dt"].dt.to_period("M").astype(str)
    counts = tdf.groupby("month").size().reset_index(name="count")
    return px.line(counts, x="month", y="count", markers=True, title="Ticket Trend Over Time")


def generate_report_html(df: pd.DataFrame, title: str = "R&D Tickets Dashboard Report") -> bytes:
    total, active, completed, pending = _build_kpis(df)

    figs = [
        ("status", _status_chart(df)),
        ("client", _client_chart(df)),
        ("timeline", _timeline_chart(df)),
        ("trend", _trend_chart(df)),
    ]
    images = []
    for name, fig in figs:
        if fig is None:
            continue
        b64 = _fig_to_base64_png(fig)
        images.append((name, b64, fig.layout.title.text if fig.layout.title else name))

    table_html = df.to_html(index=False, escape=False)

    parts = [
        f"<h1>{title}</h1>",
        "<h2>KPIs</h2>",
        f"<ul><li>Total Tickets: {total}</li><li>Active Tickets: {active}</li><li>Completed Tickets: {completed}</li><li>Pending/In-Progress Tickets: {pending}</li></ul>",
        "<h2>Charts</h2>",
    ]
    for name, b64, caption in images:
        parts.append(f"<div><h3>{caption}</h3><img alt='{name}' style='max-width:100%;' src='data:image/png;base64,{b64}'/></div>")
    parts += [
        "<h2>Filtered Data</h2>",
        table_html,
    ]
    html = "\n".join(parts)
    return html.encode("utf-8")


