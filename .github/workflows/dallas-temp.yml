name: Dallas Temperature Email

on:
  schedule:
    - cron: "0 */4 * * *"   # every 4 hours (UTC)
  workflow_dispatch:         # manual run button

jobs:
  send:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install requests

      - name: Fetch Dallas temperature and email it
        env:
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
        run: python dallas_temp_agent.py
