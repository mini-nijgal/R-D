from __future__ import annotations

import time
from typing import Tuple, Optional
import io
import requests

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

def _demo_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"Project": "Orion Compute", "Status": "In Progress", "Client": "Acme", "Start": "2025-07-01", "End": "2026-02-15"},
        {"Project": "Nova Analytics", "Status": "Pending", "Client": "Globex", "Start": "2025-09-10", "End": "2026-03-30"},
        {"Project": "Quasar Edge", "Status": "Blocked", "Client": "Initech", "Start": "2025-05-12", "End": "2026-01-20"},
        {"Project": "Helix Studio", "Status": "Completed", "Client": "Acme", "Start": "2025-01-10", "End": "2025-12-10"},
        {"Project": "Atlas Sync", "Status": "In Progress", "Client": "Umbrella", "Start": "2025-08-01", "End": "2026-05-12"},
    ])


def _get_client() -> gspread.client.Client:
    info = None
    try:
        info = st.secrets["gcp_service_account"]  # type: ignore[index]
    except Exception:
        info = None
    if not info:
        raise RuntimeError("Missing gcp_service_account in secrets")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_sheet(spreadsheet_key: str, gid: Optional[int] = None) -> Tuple[pd.DataFrame, float]:
    # Try service account first
    try:
        client = _get_client()
        sh = client.open_by_key(spreadsheet_key)
        ws = None
        if gid is not None:
            try:
                ws = sh.get_worksheet_by_id(gid)
            except Exception:
                ws = None
        if ws is None:
            ws = sh.get_worksheet(0)
        if ws is None:
            return pd.DataFrame(), time.time()
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        return df, time.time()
    except Exception:
        # Fallback: public CSV export. Allow overriding gid via secrets.
        try:
            gid_val = 0 if gid is None else gid
            if gid is None:
                try:
                    gid_val = int(st.secrets.get("sheets", {}).get("gid", 0))  # type: ignore[arg-type]
                except Exception:
                    gid_val = 0
            # Attempt export endpoint
            export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_key}/export?format=csv&gid={gid_val}"
            resp = requests.get(export_url, timeout=20)
            if resp.status_code == 200 and resp.text.strip():
                df = pd.read_csv(io.StringIO(resp.text))
                return df, time.time()
            # Attempt published endpoint (requires File → Share → Publish to web)
            pub_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_key}/pub?output=csv&gid={gid_val}"
            resp2 = requests.get(pub_url, timeout=20)
            resp2.raise_for_status()
            df = pd.read_csv(io.StringIO(resp2.text))
            return df, time.time()
        except Exception as e:
            # Provide clearer guidance for common 400/403 cases
            if isinstance(e, requests.HTTPError) and e.response is not None:
                code = e.response.status_code
                detail = f"HTTP {code}"
                hint = ""
                if code in (400, 401, 403):
                    hint = (
                        " Sheet is not publicly accessible. Options: "
                        "(1) Share with your service account and add credentials to secrets; "
                        "(2) Publish the sheet to the web (File → Share → Publish to web) and retry."
                    )
                # Fall back to demo so the app remains usable
                import streamlit as st  # local import to avoid circular in cache
                st.info(f"CSV export failed: {detail}.{hint} Using demo data for now.")
                return _demo_df(), time.time()
            # Non-HTTP error: fall back to demo as well
            import streamlit as st  # local import
            st.info("Unable to fetch Google Sheet. Using demo data for now.")
            return _demo_df(), time.time()


def _load_published_xlsx(published_url: str) -> Tuple[pd.DataFrame, float]:
    resp = requests.get(published_url, timeout=30)
    resp.raise_for_status()
    bio = io.BytesIO(resp.content)
    df = pd.read_excel(bio)
    return df, time.time()


def load_data_with_ui(
    spreadsheet_key_override: Optional[str] = None,
    gid_override: Optional[int] = None,
    published_url_override: Optional[str] = None,
) -> tuple[pd.DataFrame, str]:
    key = None
    if spreadsheet_key_override:
        key = spreadsheet_key_override
    else:
        try:
            key = st.secrets["sheets"]["spreadsheet_key"]  # type: ignore[index]
        except Exception:
            key = None
    # If user provided a published XLSX URL, try that first
    if published_url_override and published_url_override.strip():
        try:
            with st.spinner("Fetching published XLSX…"):
                df, ts = _load_published_xlsx(published_url_override.strip())
            last_updated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
            return df, last_updated
        except Exception as e:
            st.error(f"Failed to load published XLSX: {e}")
            # continue to other methods as fallback

    # Default to your provided sheet key when secrets are absent
    if not key:
        key = "1RbibIdg2iqeoj7Iw0PphfypL7g2eREg4Ee9lgPzkoDU"
        st.caption("Trying public CSV. For reliability, add service account secrets or publish the sheet to the web.")
    try:
        with st.spinner("Fetching Google Sheets data..."):
            df, ts = fetch_sheet(key, gid_override)
        last_updated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
        if df.empty:
            st.info("Sheet loaded but appears empty.")
        return df, last_updated
    except Exception as e:
        st.info(f"Using demo data due to load error: {e}")
        return _demo_df(), "Demo"
    try:
        with st.spinner("Fetching Google Sheets data..."):
            df, ts = fetch_sheet(key)
        last_updated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
        return df, last_updated
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(), ""


def clear_data_cache() -> None:
    fetch_sheet.clear()


