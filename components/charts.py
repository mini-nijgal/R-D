from __future__ import annotations

import io
from typing import Optional

import pandas as pd
import streamlit as st

# Plotly imports - required for charts
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    px = None  # type: ignore
    go = None  # type: ignore


def _check_plotly() -> bool:
    """Check if plotly is available, show error if not."""
    if not PLOTLY_AVAILABLE:
        st.error("⚠️ Plotly is not installed. Charts are unavailable. Please ensure 'plotly' is in requirements.txt.")
        return False
    return True


def _download_button_for_figure(fig: go.Figure, filename: str, label: str = "Download PNG") -> None:
    if not PLOTLY_AVAILABLE:
        return
    try:
        png = fig.to_image(format="png", scale=2)
        st.download_button(label, data=png, file_name=filename, mime="image/png")
    except Exception as e:
        st.caption(f"PNG export unavailable: {e}")


def chart_projects_by_status(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    col = "Status" if "Status" in df.columns else ("status" if "status" in df.columns else None)
    if not col:
        st.info("No status column found.")
        return
    counts = df[col].value_counts().reset_index()
    counts.columns = ["status", "count"]
    fig = px.pie(counts, values="count", names="status", hole=0.4, title="Tickets by Status")
    st.plotly_chart(fig, use_container_width=True)
    _download_button_for_figure(fig, "projects_by_status.png")


def chart_projects_by_keywords(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    # Extract clients from Summary column first, then other columns
    client_counts: dict[str, int] = {}
    
    # Priority: Summary column
    summary_cols = [c for c in df.columns if "summary" in c.lower() or "description" in c.lower()]
    for col in summary_cols:
        for v in df[col].fillna("").astype(str):
            words = v.split()
            for word in words:
                # Extract uppercase words/acronyms (likely client names)
                if word.isupper() and len(word) >= 2:
                    client_counts[word.strip()] = client_counts.get(word.strip(), 0) + 1
                # Extract patterns like VP30, VAIA
                cleaned = ''.join(c for c in word if c.isalnum())
                if cleaned and len(cleaned) >= 2 and any(c.isupper() for c in cleaned):
                    client_counts[cleaned] = client_counts.get(cleaned, 0) + 1
    
    # Fallback to other columns
    for col in df.columns:
        if any(k in col.lower() for k in ["client", "customer", "account", "keyword", "tag"]):
            for v in df[col].fillna("").astype(str):
                parts = [p.strip() for p in v.replace(";", ",").split(",") if p.strip()]
                for p in parts:
                    client_counts[p] = client_counts.get(p, 0) + 1
    
    if not client_counts:
        st.info("No client-related data detected.")
        return
    counts = pd.DataFrame({"client": list(client_counts.keys()), "count": list(client_counts.values())})
    counts = counts.sort_values("count", ascending=False).head(20)  # Top 20
    fig = px.bar(counts, x="client", y="count", title="Tickets by Keywords", color="count", color_continuous_scale="viridis")
    fig.update_layout(xaxis_title="Keywords", yaxis_title="Tickets")
    st.plotly_chart(fig, use_container_width=True)
    _download_button_for_figure(fig, "projects_by_keywords.png")


def chart_created_vs_due_date(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    # Find created and due date columns
    created_col = None
    due_col = None
    
    for c in df.columns:
        c_lower = c.lower()
        if "created" in c_lower and created_col is None:
            created_col = c
        if "due" in c_lower and due_col is None:
            due_col = c
    
    if not created_col or not due_col:
        st.info("Need both 'Created' and 'Due' date columns for scatter plot.")
        return
    
    sdf = df.copy()
    sdf["created_dt"] = pd.to_datetime(sdf[created_col], errors="coerce")
    sdf["due_dt"] = pd.to_datetime(sdf[due_col], errors="coerce")
    sdf = sdf.dropna(subset=["created_dt", "due_dt"]).copy()
    
    if sdf.empty:
        st.info("No valid created/due dates to plot.")
        return
    
    # Add status for color coding if available
    status_col = None
    for c in df.columns:
        if c.lower() == "status":
            status_col = c
            break
    
    if status_col:
        fig = px.scatter(
            sdf,
            x="created_dt",
            y="due_dt",
            color=status_col,
            title="Created Date vs Due Date",
            labels={"created_dt": "Created Date", "due_dt": "Due Date"},
            hover_data=[c for c in df.columns if c not in [created_col, due_col]][:3],
        )
    else:
        fig = px.scatter(
            sdf,
            x="created_dt",
            y="due_dt",
            title="Created Date vs Due Date",
            labels={"created_dt": "Created Date", "due_dt": "Due Date"},
        )
    
    st.plotly_chart(fig, use_container_width=True)
    _download_button_for_figure(fig, "created_vs_due_date.png")


def chart_by_resource(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    # Use Assignee column specifically
    resource_col = None
    for c in df.columns:
        if c.lower() == "assignee":
            resource_col = c
            break
    if resource_col is None:
        st.info("No 'Assignee' column found.")
        return

    status_col = None
    for c in df.columns:
        if c.lower() in ("status",):
            status_col = c
            break
        if "status" in c.lower():
            status_col = c
            break

    # Normalize values
    rdf = df.copy()
    rdf[resource_col] = rdf[resource_col].fillna("(unassigned)").astype(str)

    # 1) Workload by resource (count of tickets)
    counts = rdf.groupby(resource_col).size().reset_index(name="tickets")
    counts = counts.sort_values("tickets", ascending=False)
    fig1 = px.bar(counts, x=resource_col, y="tickets", title="Tickets by Resource")
    fig1.update_layout(xaxis_title="Resource", yaxis_title="Tickets")
    st.plotly_chart(fig1, use_container_width=True)
    _download_button_for_figure(fig1, "tickets_by_resource.png")

    # 2) Stacked by status per resource (if status available)
    if status_col is not None:
        sdf = rdf.copy()
        sdf[status_col] = sdf[status_col].fillna("(unknown)").astype(str)
        fig2 = px.bar(
            sdf,
            x=resource_col,
            color=status_col,
            title="Tickets by Resource and Status",
        )
        fig2.update_layout(xaxis_title="Resource", yaxis_title="Tickets")
        st.plotly_chart(fig2, use_container_width=True)
        _download_button_for_figure(fig2, "tickets_by_resource_status.png")


def chart_status_over_time(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    """Status distribution over time"""
    date_col = None
    status_col = None
    
    for c in df.columns:
        if "created" in c.lower() or ("date" in c.lower() and date_col is None):
            date_col = c
        if c.lower() == "status":
            status_col = c
    
    if not date_col or not status_col:
        st.info("Need date and status columns for this chart.")
        return
    
    tdf = df.copy()
    tdf["dt"] = pd.to_datetime(tdf[date_col], errors="coerce")
    tdf = tdf.dropna(subset=["dt", status_col]).copy()
    
    if tdf.empty:
        st.info("No valid data for status over time.")
        return
    
    tdf["month"] = tdf["dt"].dt.to_period("M").astype(str)
    counts = tdf.groupby([status_col, "month"]).size().reset_index(name="count")
    
    fig = px.line(counts, x="month", y="count", color=status_col, markers=True, title="Status Distribution Over Time")
    st.plotly_chart(fig, use_container_width=True)
    _download_button_for_figure(fig, "status_over_time.png")


def chart_priority_breakdown(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    """Priority/severity breakdown if available"""
    priority_col = None
    for c in df.columns:
        if "priority" in c.lower() or "severity" in c.lower():
            priority_col = c
            break
    
    if not priority_col:
        st.info("No priority/severity column found.")
        return
    
    counts = df[priority_col].value_counts().reset_index()
    counts.columns = ["priority", "count"]
    
    fig = px.bar(counts, x="priority", y="count", title="Tickets by Priority", color="priority")
    st.plotly_chart(fig, use_container_width=True)
    _download_button_for_figure(fig, "priority_breakdown.png")


def chart_progress_funnel(df: pd.DataFrame) -> None:
    if not _check_plotly():
        return
    """Funnel chart showing ticket progression"""
    status_col = None
    for c in df.columns:
        if c.lower() == "status":
            status_col = c
            break
    
    if not status_col:
        st.info("Need status column for funnel chart.")
        return
    
    # Categorize statuses
    status_map = {
        "pending": "Pending",
        "backlog": "Pending",
        "todo": "Pending",
        "in progress": "In Progress",
        "in-progress": "In Progress",
        "inprogress": "In Progress",
        "active": "Active",
        "completed": "Completed",
        "done": "Completed",
        "closed": "Completed",
    }
    
    sdf = df.copy()
    sdf["category"] = sdf[status_col].astype(str).str.lower().map(status_map).fillna("Other")
    counts = sdf["category"].value_counts().reset_index()
    counts.columns = ["stage", "count"]
    
    # Order: Pending -> In Progress -> Active -> Completed
    order = ["Pending", "In Progress", "Active", "Completed", "Other"]
    counts["stage"] = pd.Categorical(counts["stage"], categories=order, ordered=True)
    counts = counts.sort_values("stage")
    
    fig = px.funnel(
        counts,
        x="count",
        y="stage",
        title="Ticket Progress Funnel",
        color="stage",
    )
    fig.update_layout(yaxis_title="Stage", xaxis_title="Number of Tickets")
    st.plotly_chart(fig, use_container_width=True)
    _download_button_for_figure(fig, "progress_funnel.png")


