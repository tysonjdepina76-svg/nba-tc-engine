#!/bin/bash
cd "$(dirname "$0")/scripts"
streamlit run okc_scs_series_dashboard.py --server.port 8505 --browser.gatherUsageStats=False
