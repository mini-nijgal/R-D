from __future__ import annotations

from typing import List, Tuple

import pandas as pd
import streamlit as st

from .utils import count_active_filters, extract_clients, find_date_columns


def sidebar_filters(df: pd.DataFrame) -> tuple[list[str], list[str], str, tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    # Returns: status_pick, keyword_pick, query, date_range
    st.sidebar.header("Filters")

    status_vals = sorted({str(v) for v in df.get("Status", df.get("status", pd.Series(dtype=str))).dropna().unique().tolist()})
    keywords = extract_clients(df)  # Reusing extract_clients but calling it keywords

    status_pick = st.sidebar.multiselect("Current Status", options=status_vals, default=[])
    keyword_pick = st.sidebar.multiselect("Keywords", options=keywords, default=[])

    date_cols = find_date_columns(df)
    # Default date range: Sep 1 - Dec 1 2025
    default_start = pd.Timestamp("2025-09-01")
    default_end = pd.Timestamp("2025-12-01")
    
    date_range: Tuple[pd.Timestamp | None, pd.Timestamp | None] = (default_start, default_end)
    if date_cols:
        col = st.sidebar.selectbox("Date column", options=date_cols, index=0)
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(default_start.date(), default_end.date()),  # type: ignore[arg-type]
            min_value=None,
            max_value=None,
        )
        if date_range and len(date_range) == 2:
            date_range = (pd.Timestamp(date_range[0]) if date_range[0] else None, pd.Timestamp(date_range[1]) if date_range[1] else None)
        else:
            date_range = (default_start, default_end)

    query = st.sidebar.text_input("Search (all columns)")

    c1, c2, c3 = st.sidebar.columns([1, 1, 1])
    with c1:
        apply_clicked = st.button("Apply Filters")
    with c2:
        clear_clicked = st.button("Clear All")
    with c3:
        st.metric("Active", count_active_filters(status_pick, keyword_pick, query, date_range))

    if clear_clicked:
        status_pick = []
        keyword_pick = []
        query = ""
        date_range = (None, None)

    # Apply immediately (Streamlit reruns) – apply_clicked used for UX only
    return status_pick, keyword_pick, query, date_range


def apply_dataframe_filters(
    df: pd.DataFrame,
    status_pick: List[str],
    keyword_pick: List[str],
    query: str,
    date_range: Tuple[pd.Timestamp | None, pd.Timestamp | None],
) -> pd.DataFrame:
    out = df.copy()
    # Status
    if status_pick:
        col = "Status" if "Status" in out.columns else ("status" if "status" in out.columns else None)
        if col:
            out = out[out[col].astype(str).isin(status_pick)]
    # Keywords (search in Summary first, then other columns)
    if keyword_pick:
        mask = pd.Series(False, index=out.index)
        # Priority: Summary column
        summary_cols = [c for c in out.columns if "summary" in c.lower() or "description" in c.lower()]
        for col in summary_cols:
            col_series = out[col].fillna("").astype(str)
            for kp in keyword_pick:
                mask = mask | col_series.str.contains(kp, case=False, regex=False)
        # Fallback to other columns
        for col in out.columns:
            if any(k in col.lower() for k in ["client", "customer", "account", "keyword", "tag"]):
                col_series = out[col].fillna("").astype(str)
                for kp in keyword_pick:
                    mask = mask | col_series.str.contains(kp, case=False, regex=False)
        out = out[mask]
    # Date range - apply to created date or first date column
    if date_range and any(date_range):
        start, end = date_range
        # Prefer created date, then any date column
        date_cols = [c for c in out.columns if "created" in c.lower()]
        if not date_cols:
            date_cols = [c for c in out.columns if "date" in c.lower() or c.lower() in ("start", "end")]
        if date_cols:
            dc = date_cols[0]
            s = pd.to_datetime(out[dc], errors="coerce")
            if start is not None:
                out = out[s >= pd.to_datetime(start)]
            if end is not None:
                out = out[s <= pd.to_datetime(end)]
    # Query across all columns
    if query and query.strip():
        q = query.strip().lower()
        contains = out.apply(lambda row: any(q in str(v).lower() for v in row.values), axis=1)
        out = out[contains]
    return out


