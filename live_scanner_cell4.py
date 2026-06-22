# ... (imports and NIFTY50_SYMBOLS remain the same)

# --- ENVIRONMENT CONFIGURATION ---
# UPDATED: Now pointing to your local 'data/' folder
DRIVE_FOLDER = "data/" 

# ... (rest of the file remains the same)
```

### How the Auto-Scan and Manual Refresh Logic Works:

* **Manual Refresh:** In the Dashboard (`streamlit_app.py`), whenever you click "Load & Run Backtest" or refresh the page, it reads the current state of the CSVs in the `data/` folder. If your live scanner has updated those files with the latest ICICI data, the Dashboard will show the most recent prices immediately.
* **Auto-Scan Logic:** Your `live_scanner_cell4.py` is designed to be a continuous loop. To enable the 5-minute auto-scan, you should wrap the `run_rolling_framework()` in a loop that checks the time.

To ensure it runs every 5 minutes automatically, you can add this block at the end of your `live_scanner_cell4.py`:

```python
# Add this to the bottom of live_scanner_cell4.py to enable the 5-min auto-loop
if __name__ == "__main__":
    while True:
        # Check if the market is likely open (e.g., 09:15 to 15:30)
        current_time = datetime.now().time()
        if datetime(2026, 6, 22, 9, 15).time() <= current_time <= datetime(2026, 6, 22, 15, 35).time():
            run_rolling_framework()
        
        # Wait until the next 5-minute interval
        time.sleep(300)
