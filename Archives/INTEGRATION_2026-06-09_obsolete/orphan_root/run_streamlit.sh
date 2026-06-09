#!/bin/bash
cd /home/workspace/tc-workspace
python3 -c "
import sys; sys.path.insert(0, '.')
from sports_tc_app import run_streamlit
run_streamlit()
" -- --server.port 8501 --browser.gatherUsageStats=False
