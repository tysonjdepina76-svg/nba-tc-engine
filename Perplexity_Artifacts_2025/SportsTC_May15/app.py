import streamlit as st
import subprocess
import sys
import os

st.set_page_config(page_title="Sports TC", page_icon="🏀", layout="wide")

st.title("🏀 Sports TC — Triple Conservative Projections")
st.markdown("**TC = stat × 0.85 | Q = × 0.65 | OUT = 0 | Pace: +8**")

# ── Sidebar controls ──
sport = st.sidebar.selectbox("Sport", ["NBA", "WNBA"], index=1)
game = st.sidebar.text_input("Game (e.g. NYL @ POR)", "NYL @ POR")
show_injury = st.sidebar.checkbox("Show Injury Report", value=True)
refresh = st.sidebar.button("↻ Refresh Projections")

st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Slate (WNBA)**")
if st.sidebar.button("WNBA Full Slate"):
    game = "WNBA_SLATE"

# ── Run engine ──
if refresh or game:
    with st.spinner("Running TC engine..."):
        cmd = [sys.executable, "sports_tc.py", "--sport", sport, "--game", game]
        if show_injury:
            cmd.append("--injury")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
        output = result.stdout + result.stderr

    # ── Parse and display ──
    sections = output.split("═" * 50)
    
    for section in sections:
        lines = [l for l in section.strip().split("\n") if l.strip()]
        if not lines:
            continue
        
        # Game header
        for line in lines[:3]:
            if "@" in line or "SLATE" in line or "TC ROSTER" in line.upper():
                st.subheader(f"🏀 {line.strip()}")
        
        # Injury report section
        if "INJURY REPORT" in section:
            st.markdown("### ⚕ Injury Report")
            for line in lines:
                if any(x in line for x in ["✅", "⚠️", "❌"]) and ("G |" in line or "F |" in line or "C |" in line):
                    st.markdown(line.strip())
        
        # Starting lineup section
        if "STARTING LINEUP" in section:
            st.markdown("### 📋 Starting Lineup")
            for line in lines:
                if "TC_" in line or "Player" in line or any(f"{p} " in line for p in ["Breanna", "Sabrina", "Caitlin", "A'ja"]):
                    if "─" not in line and len(line) > 10:
                        st.markdown(line.strip())
        
        # TC projections table
        if "TC PROJECTIONS" in section:
            st.markdown("### 📊 TC Projections")
            for line in lines:
                if any(x in line for x in ["TC_PTS", "TC_LINE", "TC_EDGE", "TC_REB", "TC_AST", "TC_3PM"]):
                    st.markdown(f"`{line.strip()}`")
        
        # Summary
        if "TC SUMMARY" in section or "TC Final" in section:
            st.markdown("### 📈 TC Summary")
            for line in lines:
                if any(x in line for x in ["TC", "Line", "Edge", "Signal", "OVER", "UNDER"]):
                    if "─" not in line:
                        st.markdown(line.strip())

    # ── Raw output ──
    with st.expander("📄 Raw Engine Output"):
        st.text(output)

st.markdown("---")
st.caption("Sports TC v4.0 | NBA + WNBA | TC = stat × 0.85 | Q = × 0.65 | OUT = 0")