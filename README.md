# R&D Tickets Dashboard (Streamlit)

A production-ready Streamlit app for tracking R&D tickets with Google Sheets as a datasource, Plotly visualizations, exports, and AI chat via OpenRouter (Kimi-K2 free).

## Features
- **Authentication**: Username/password login with session persistence (default: admin/admin123)
- **Data Source**: Fixed published Google Sheets XLSX (no GCP setup required for basic usage)
- **Filters**: Sidebar filters for status, client, date range, and full-text search
- **KPIs**: Total, Active, Completed, and Pending ticket metrics
- **Visualizations**: 5 interactive Plotly charts (Status, Client, Timeline, Trend, Resource) with PNG download
- **Data Table**: Sortable, searchable table with CSV/Excel/HTML report exports
- **AI Chat**: Optional AI assistant using `moonshotai/kimi-k2:free` via OpenRouter (requires API key)
- **Resource Analysis**: Workload and status breakdown by assignee/resource
- **Ready for Streamlit Cloud**: Deploy-ready with secrets management

## Quick Start

1. **Install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Run locally** (works without secrets - uses demo data or published sheet)
```bash
streamlit run app.py
```

3. **Login**: Use `admin` / `admin123` (or configure in secrets)

## Configuration (Optional)

### Basic Setup (No Secrets Required)
- App works out of the box with the hardcoded published XLSX source
- Login uses default credentials (admin/admin123)
- AI chat shows a setup message if API key is missing

### Full Setup (With Secrets)

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`:

```toml
[auth]
users = { admin = "your-secure-password" }

[openrouter]
api_key = "your-openrouter-api-key"  # Get free key at https://openrouter.ai/keys

# Optional: For authenticated Google Sheets access (instead of published XLSX)
[gcp_service_account]
type = "service_account"
project_id = "..."
# ... full service account JSON
```

**To enable AI chat:**
- Get a free API key from https://openrouter.ai/keys
- Add `[openrouter].api_key` to secrets

**To use authenticated Google Sheets (instead of published XLSX):**
- Create a GCP service account with Sheets/Drive readonly scopes
- Share your sheet with the service account email
- Add full service account JSON to `[gcp_service_account]` in secrets

## Deployment to Streamlit Cloud

1. Push this repository to GitHub
2. Connect to Streamlit Cloud
3. Add secrets in Cloud dashboard (Settings → Secrets):
   - Copy all sections from your local `.streamlit/secrets.toml`
   - At minimum, add `[auth].users` for production passwords

## Data Source

The app is configured to use a fixed published Google Sheets XLSX URL. To change the source:
- Edit `PUBLISHED_XLSX_URL` in `app.py`
- Or configure service account authentication in secrets for direct API access

## Notes

- **PNG Export**: Requires `kaleido` (included in requirements)
- **Performance**: Install `watchdog` for faster file watching during development
- **Caching**: Data is cached for 60 seconds; use "Refresh Data" button for immediate updates
- **AI Chat**: Uses free Kimi-K2 model via OpenRouter; requires API key but no cost for basic usage


