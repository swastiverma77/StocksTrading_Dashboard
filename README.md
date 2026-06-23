# Institutional Nifty 50 Local-Cache Scanner

Streamlit Community Cloud starter app for a Breeze-backed Nifty 50 scanner.

## Structure

- `app.py` - Streamlit entrypoint and page orchestration.
- `src/ui/` - dashboard layout, sidebar, cards, tables, and CSS.
- `src/session/` - ICICI Breeze credential/session handling.
- `src/data_updates/` - local CSV cache loading, normalization, and incremental update flow.
- `src/scanners/` - pluggable scanners and scanner registry.
- `data/` - stock CSV cache directory only. Keep app code outside this folder.

## Local Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets

Create `.streamlit/secrets.toml` locally or add these in Streamlit Community Cloud secrets:

```toml
BREEZE_API_KEY = "..."
BREEZE_SECRET_KEY = "..."
BREEZE_SESSION_TOKEN = "..."
APP_URL = "https://your-app.streamlit.app"
```

## Keepalive

`.github/workflows/keepalive.yml` pings the deployed Streamlit app. Add `APP_URL` as a GitHub Actions secret. This helps reduce hibernation, but Streamlit Community Cloud is still best treated as a prototype/runtime UI, not guaranteed infrastructure.
