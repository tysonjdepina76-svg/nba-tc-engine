#!/bin/bash
cd /home/workspace/Projects
streamlit run tc_dashboard.py --server.port 8510 --server.address 0.0.0.0 --server.baseUrlPath /nba-tc
