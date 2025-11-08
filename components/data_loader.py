from __future__ import annotations

import time
from typing import Tuple, Optional
import io
import requests

import pandas as pd
import streamlit as st

# Optional imports for Google Sheets API (only needed if using service account)
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    gspread = None  # type: ignore
    Credentials = None  # type: ignore


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


def _get_client():
    if not GSPREAD_AVAILABLE:
        raise RuntimeError("gspread is not installed. Install it with: pip install gspread google-auth")
    info = None
    try:
        info = st.secrets["gcp_service_account"]  # type: ignore[index]
    except Exception:
        info = None
    if not info:
        raise RuntimeError("Missing gcp_service_account in secrets")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)  # type: ignore


@st.cache_data(ttl=60, show_spinner=True)
def fetch_sheet(spreadsheet_key: str, gid: Optional[int] = None) -> Tuple[pd.DataFrame, float]:
    # Try service account first (only if gspread is available)
    if GSPREAD_AVAILABLE:
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
            pass  # Fall through to public CSV method
    
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
        resp = requests.get(export_url, timeout=5)
        if resp.status_code == 200 and resp.text.strip():
            df = pd.read_csv(io.StringIO(resp.text))
            return df, time.time()
        # Attempt published endpoint (requires File → Share → Publish to web)
        pub_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_key}/pub?output=csv&gid={gid_val}"
        resp2 = requests.get(pub_url, timeout=5)
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


# Check if openpyxl is available at module level
try:
    import openpyxl  # noqa: F401
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def _load_published_xlsx(published_url: str) -> Tuple[pd.DataFrame, float]:
    """Load XLSX from published URL. Requires openpyxl."""
    if not OPENPYXL_AVAILABLE:
        raise ImportError(
            "openpyxl is required to read XLSX files. Please install it: pip install openpyxl"
        )
    
    # Use shorter timeout to fail fast
    resp = requests.get(published_url, timeout=10)
    resp.raise_for_status()
    bio = io.BytesIO(resp.content)
    try:
        df = pd.read_excel(bio, engine='openpyxl')
    except Exception as e:
        raise RuntimeError(f"Failed to parse XLSX file: {e}") from e
    return df, time.time()


def load_data_with_ui(
    spreadsheet_key_override: Optional[str] = None,
    gid_override: Optional[int] = None,
    published_url_override: Optional[str] = None,
) -> tuple[pd.DataFrame, str]:
    # Show something immediately
    status_placeholder = st.empty()
    
    # Skip XLSX if openpyxl is not available - fail fast
    if published_url_override and published_url_override.strip() and OPENPYXL_AVAILABLE:
        try:
            status_placeholder.info("🔄 Fetching published XLSX…")
            df, ts = _load_published_xlsx(published_url_override.strip())
            status_placeholder.empty()
            last_updated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
            if not df.empty:
                return df, last_updated
            else:
                status_placeholder.warning("XLSX file is empty. Trying other sources...")
        except ImportError:
            status_placeholder.warning("⚠️ openpyxl not installed. Skipping XLSX. Trying other sources...")
        except Exception as e:
            status_placeholder.warning(f"Failed to load XLSX: {str(e)[:100]}. Trying other sources...")
    elif published_url_override and published_url_override.strip() and not OPENPYXL_AVAILABLE:
        status_placeholder.warning("⚠️ openpyxl not installed. Cannot load XLSX. Using other sources...")

    # Get spreadsheet key
    key = None
    if spreadsheet_key_override:
        key = spreadsheet_key_override
    else:
        try:
            key = st.secrets["sheets"]["spreadsheet_key"]  # type: ignore[index]
        except Exception:
            key = None
    
    # Default to your provided sheet key when secrets are absent
    if not key:
        key = "1RbibIdg2iqeoj7Iw0PphfypL7g2eREg4Ee9lgPzkoDU"
    
    # Try Google Sheets with shorter timeout
    try:
        status_placeholder.info("🔄 Fetching Google Sheets data...")
        df, ts = fetch_sheet(key, gid_override)
        status_placeholder.empty()
        last_updated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
        if not df.empty:
            return df, last_updated
        else:
            status_placeholder.info("Sheet is empty. Using demo data.")
            return _demo_df(), "Demo"
    except Exception as e:
        status_placeholder.info(f"Using demo data. (Sheet fetch failed: {str(e)[:50]})")
        return _demo_df(), "Demo"


def clear_data_cache() -> None:
    fetch_sheet.clear()


