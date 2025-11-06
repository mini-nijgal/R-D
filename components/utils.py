from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Iterable, List, Optional

import pandas as pd
import streamlit as st


def inject_css() -> None:
    css = """
    <style>
      /* Animations */
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
      }
      @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
      
      /* Main container */
      .main .block-container {
        animation: fadeIn 0.6s ease-in;
      }
      
      /* Metrics */
      [data-testid="stMetricValue"] {
        animation: fadeIn 0.8s ease-in;
        font-weight: 700;
      }
      [data-testid="stMetricDelta"] {
        animation: slideIn 0.5s ease-in;
      }
      
      /* Buttons */
      .stButton>button {
        border-radius: 12px;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      }
      .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
      }
      
      /* Tabs */
      .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
      }
      .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
      }
      .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
      }
      
      /* Cards */
      .metric-card { 
        padding: 20px; 
        border-radius: 15px; 
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        animation: fadeIn 0.6s ease-in;
      }
      .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.3);
      }
      
      /* Badges */
      .badge { 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        animation: fadeIn 0.5s ease-in;
      }
      .status-green { 
        background: linear-gradient(135deg, #37d483 0%, #2eb872 100%);
        color: white;
        box-shadow: 0 2px 10px rgba(55, 212, 131, 0.3);
      }
      .status-amber { 
        background: linear-gradient(135deg, #ffcc66 0%, #ffb84d 100%);
        color: #1a1a1a;
        box-shadow: 0 2px 10px rgba(255, 204, 102, 0.3);
      }
      .status-red { 
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        box-shadow: 0 2px 10px rgba(255, 107, 107, 0.3);
      }
      
      /* Sidebar */
      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
      }
      
      /* Logo styling */
      [data-testid="stSidebar"] img {
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        animation: fadeIn 0.8s ease-in;
      }
      
      /* Headers */
      h1, h2, h3 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: fadeIn 0.8s ease-in;
      }
      
      /* Dataframe */
      .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        animation: fadeIn 0.6s ease-in;
      }
      
      /* Expanders */
      [data-testid="stExpander"] {
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
      }
      
      .muted { color: #9aa4b2; }
      
      /* Login page styling */
      .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 60vh;
        padding: 2rem;
        animation: fadeIn 0.8s ease-in;
      }
      .login-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem;
        border-radius: 25px;
        box-shadow: 0 15px 50px rgba(102, 126, 234, 0.4);
        max-width: 450px;
        width: 100%;
        color: white;
        animation: pulse 3s ease-in-out infinite;
      }
      .login-title {
        font-size: 2.2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        text-align: center;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
      }
      .login-subtitle {
        text-align: center;
        opacity: 0.95;
        margin-bottom: 2rem;
        font-size: 1.1rem;
      }
      .login-icon {
        font-size: 5rem;
        text-align: center;
        margin-bottom: 1rem;
        animation: pulse 2s ease-in-out infinite;
      }
      
      /* Scrollbar */
      ::-webkit-scrollbar {
        width: 10px;
      }
      ::-webkit-scrollbar-track {
        background: #1e1e2e;
      }
      ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 5px;
      }
      ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
      }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(list(df.columns))
    for _, row in df.iterrows():
        ws.append([None if pd.isna(v) else v for v in row.tolist()])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def now_ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def dataframe_to_compact_json(df: pd.DataFrame, max_rows: int = 100) -> str:
    sample = df.head(max_rows)
    return json.dumps(json.loads(sample.to_json(orient="records")), ensure_ascii=False, separators=(",", ":"))


def find_date_columns(df: pd.DataFrame) -> List[str]:
    candidates = [
        "date", "Date", "created", "Created", "start", "Start", "start_date",
        "Start Date", "end", "End", "end_date", "End Date",
    ]
    present = [c for c in candidates if c in df.columns]
    extras = [c for c in df.columns if "date" in c.lower() and c not in present]
    return present + extras


def extract_clients(df: pd.DataFrame) -> List[str]:
    # Priority: Summary column for keywords, then other columns
    values: List[str] = []
    
    # First try Summary column for keywords
    summary_cols = [c for c in df.columns if "summary" in c.lower() or "description" in c.lower()]
    for col in summary_cols:
        series = df[col].dropna().astype(str)
        for v in series:
            # Extract potential client names (uppercase words, acronyms, etc.)
            words = v.split()
            for word in words:
                # Look for uppercase words that might be client names
                if word.isupper() and len(word) >= 2:
                    values.append(word.strip())
                # Look for patterns like "VP30", "VAIA", etc.
                if any(c.isupper() for c in word) and len(word) >= 2:
                    cleaned = ''.join(c for c in word if c.isalnum())
                    if cleaned and len(cleaned) >= 2:
                        values.append(cleaned)
    
    # Fallback to other columns
    possible_cols = [
        "Client", "client", "Customer", "customer", "Account", "account",
        "Keywords", "keywords", "Tags", "tags",
    ]
    for col in possible_cols:
        if col in df.columns:
            series = df[col].dropna().astype(str)
            for v in series:
                if ";" in v or "," in v:
                    values.extend([p.strip() for p in v.replace(";", ",").split(",") if p.strip()])
                else:
                    values.append(v.strip())
    
    uniq = sorted({v for v in values if v and len(v) >= 2})
    return uniq


def count_active_filters(status: Iterable[str], clients: Iterable[str], query: str, dates: tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]) -> int:
    n = 0
    if status: n += 1
    if clients: n += 1
    if query and query.strip(): n += 1
    if dates and any(dates): n += 1
    return n


