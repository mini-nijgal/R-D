from __future__ import annotations

import streamlit as st
import pandas as pd

from components.authentication import require_auth, logout_button, get_user
from components.data_loader import load_data_with_ui, clear_data_cache
from components.filters import sidebar_filters, apply_dataframe_filters
from components.charts import (
    chart_projects_by_status,
    chart_projects_by_keywords,
    chart_created_vs_due_date,
    chart_by_resource,
    chart_status_over_time,
    chart_priority_breakdown,
    chart_progress_funnel,
)
from components.ai_chat import chat_ui
from components import utils
from components.report import generate_report_html


def page_setup() -> None:
    st.set_page_config(
        page_title="R&D Tickets Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    utils.inject_css()


def kpi_area(df: pd.DataFrame) -> None:
    total = len(df)
    # Heuristic columns - check multiple case variations
    status_col = None
    for col in df.columns:
        if col.lower() == "status":
            status_col = col
            break
    
    active_count = 0
    completed_count = 0
    in_progress_count = 0
    pending_count = 0
    if status_col:
        vals = df[status_col].astype(str).str.strip()
        vals_lower = vals.str.lower()
        
        # Check case-insensitive patterns
        active_count = int(vals_lower.isin(["active", "ongoing"]).sum())
        in_progress_count = int(vals_lower.isin(["in progress", "in-progress", "inprogress"]).sum())
        completed_count = int(vals_lower.isin(["done", "completed", "closed", "finished"]).sum())
        pending_count = int(vals_lower.isin(["pending", "backlog", "todo", "paused", "blocked"]).sum())
    
    pending_in_progress = pending_count + in_progress_count

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Tickets", total)
    with c2:
        pct = (active_count / total * 100) if total else 0
        st.metric("Active Tickets", active_count, delta=f"{pct:.1f}% of total")
    with c3:
        st.metric("Completed Tickets", completed_count)
    with c4:
        st.metric("Pending / In-Progress Tickets", pending_in_progress)


def main() -> None:
    try:
        page_setup()
    except Exception as e:
        st.error(f"Page setup error: {e}")
        st.stop()
    
    try:
        require_auth()
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.stop()
    
    # Logo in sidebar above logout - big and looping GIF
    logo_path = "Untitled design.gif"
    try:
        import os
        from pathlib import Path
        logo_file = Path(logo_path)
        if logo_file.exists():
            # Use HTML img tag for better GIF support
            logo_bytes = logo_file.read_bytes()
            import base64
            logo_b64 = base64.b64encode(logo_bytes).decode()
            st.sidebar.markdown(
                f"""
                <div style='text-align: center; margin: 20px 0; padding: 10px;'>
                    <img src="data:image/gif;base64,{logo_b64}" 
                         style="width: 250px; height: auto; border-radius: 15px; box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);" 
                         alt="Logo">
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.sidebar.markdown("### 📊")
            st.sidebar.caption("Logo file not found")
    except Exception as e:
        # Fallback to Streamlit image
        try:
            st.sidebar.image(logo_path, width=250, use_column_width=False)
        except:
            st.sidebar.markdown("### 📊")
            st.sidebar.caption(f"Logo error: {str(e)[:50]}")
    
    logout_button()

    meta = st.empty()

    # Data controls (fixed published source)
    st.sidebar.header("Data")
    if st.sidebar.button("🔁 Refresh Data"):
        clear_data_cache()
        st.rerun()

    # Show title immediately so user sees something
    st.title("R&D Tickets Dashboard")
    
    # IMPORTANT: Load demo data FIRST so UI renders immediately
    # Then try to load real data in background/on demand
    from components.data_loader import _demo_df, OPENPYXL_AVAILABLE
    
    # Use session state to cache loaded data and avoid re-fetching on every rerun
    if 'dashboard_df' not in st.session_state or 'dashboard_last_updated' not in st.session_state:
        # Initialize with demo data immediately
        st.session_state.dashboard_df = _demo_df()
        st.session_state.dashboard_last_updated = "Demo (loading...)"

    # Try to load real data, but don't block on it
    PUBLISHED_XLSX_URL = (
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vSD5oqmdQWQ5OpCLqAAssj-r84JVt7GLBC80FLkgiE37EyyWHEjogG7JJzJQU4bXQ_fIQR4lpeNFj-9/pub?output=xlsx"
    )
    
    # Only try XLSX if openpyxl is available
    xlsx_url = PUBLISHED_XLSX_URL if OPENPYXL_AVAILABLE else None
    
    # Load data with timeout protection - use demo data if it takes too long
    load_real_data = st.sidebar.checkbox("🔄 Load live data", value=False, help="Check to attempt loading data from external sources")
    
    if load_real_data:
        status_container = st.sidebar.empty()
        try:
            status_container.info("⏳ Loading data...")
            df, last_updated = load_data_with_ui(
                spreadsheet_key_override=None,
                gid_override=None,
                published_url_override=xlsx_url,
            )
            if df is not None and not df.empty:
                st.session_state.dashboard_df = df
                st.session_state.dashboard_last_updated = last_updated
                status_container.success("✅ Data loaded!")
            else:
                status_container.warning("⚠️ No data loaded, using demo data")
        except Exception as e:
            status_container.error(f"❌ Error: {str(e)[:50]}")
            st.session_state.dashboard_df = _demo_df()
            st.session_state.dashboard_last_updated = "Demo"
    else:
        st.sidebar.info("ℹ️ Using demo data. Check 'Load live data' to fetch from external sources.")
    
    # Always use session state data (either demo or loaded)
    df = st.session_state.dashboard_df
    last_updated = st.session_state.dashboard_last_updated
    
    # Final safety check
    if df is None or df.empty:
        df = _demo_df()
        last_updated = "Demo"
        st.session_state.dashboard_df = df
        st.session_state.dashboard_last_updated = last_updated

    meta.caption(f"Last updated: {last_updated}")

    # Filters
    status_pick, keyword_pick, query, date_range = sidebar_filters(df)
    filtered = apply_dataframe_filters(df, status_pick, keyword_pick, query, date_range)

    # KPIs
    kpi_area(filtered)

    # Charts (tabs)
    st.subheader("Visualizations")
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "By Status", "By Keywords", "Created vs Due", "By Resource", 
        "Status Over Time", "Priority", "Progress Funnel"
    ])
    with t1:
        chart_projects_by_status(filtered)
    with t2:
        chart_projects_by_keywords(filtered)
    with t3:
        chart_created_vs_due_date(filtered)
    with t4:
        chart_by_resource(filtered)
    with t5:
        chart_status_over_time(filtered)
    with t6:
        chart_priority_breakdown(filtered)
    with t7:
        chart_progress_funnel(filtered)

    # Data table and exports
    st.subheader("Data Table")
    st.caption(f"Rows: {len(filtered)}")
    st.dataframe(filtered, use_container_width=True)

    exp_c1, exp_c2, exp_c3 = st.columns([1, 1, 1])
    with exp_c1:
        st.download_button(
            "Download CSV",
            data=utils.to_csv_bytes(filtered),
            file_name=f"rnd-dashboard-{utils.now_ts().replace(' ', '_').replace(':','-')}.csv",
            mime="text/csv",
        )
    with exp_c2:
        if utils.openpyxl_available():
            st.download_button(
                "Download Excel",
                data=utils.to_excel_bytes(filtered),
                file_name=f"rnd-dashboard-{utils.now_ts().replace(' ', '_').replace(':','-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.error("⚠️ Excel export unavailable. openpyxl is not installed. Please ensure 'openpyxl' is in requirements.txt.")
    with exp_c3:
        html_bytes = generate_report_html(filtered)
        st.download_button(
            "Download Dashboard Report (HTML)",
            data=html_bytes,
            file_name=f"rnd-dashboard-report-{utils.now_ts().replace(' ', '_').replace(':','-')}.html",
            mime="text/html",
        )

    st.divider()
    # Token-free local chat (always available)
    with st.expander("💬 Data Assistant", expanded=False):
        from components.local_chat import local_chat_ui
        local_chat_ui(filtered)
    
    # Optional AI chat (requires OpenRouter API key)
    with st.expander("🤖 AI Chatbot  )", expanded=False):
        chat_ui(filtered)


if __name__ == "__main__":
    main()


