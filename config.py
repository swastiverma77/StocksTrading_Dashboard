name: Keep Streamlit Warm

on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Streamlit app
        run: |
          curl --fail --silent --show-error --max-time 20 "${{ secrets.APP_URL }}"

