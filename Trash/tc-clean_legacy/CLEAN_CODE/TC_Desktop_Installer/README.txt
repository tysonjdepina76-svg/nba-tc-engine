═══════════════════════════════════════════════════════
  TC TRIPLE CONSERVATIVE — Chromebook Install Guide
  Sports Betting Engine · NBA · WNBA · NCAAB · MLB · NHL
═══════════════════════════════════════════════════════

SETUP (one time, ~3 minutes)
─────────────────────────────
1. On your Chromebook, open Settings → Advanced → Developers
2. Turn on "Linux development environment"
3. Wait for the Linux terminal to finish installing
4. Move this entire folder (TC_Desktop_Installer) into your
   Chromebook's Linux files area:
       Linux files > home > <your-username>
   (you can drag/drop from Chrome's Files app)

RUN THE APP
───────────
1. Open the Terminal app from your Chromebook launcher
2. Type:
       cd ~/TC_Desktop_Installer
       chmod +x run_tc_app.sh
       bash run_tc_app.sh
3. First run takes ~1 minute to install Python packages
4. When you see "Starting TC app at http://localhost:8501"
   open Chrome and go to:  http://localhost:8501

STOP THE APP
────────────
Press Ctrl+C in the Terminal window.

NEXT RUN
────────
Just open Terminal → bash run_tc_app.sh (skip setup)

NOTE
────
The app uses The Odds API. Your API key is read from the
environment variable ODDS_API_KEY. If you don't have one yet,
open the app and the URL field works without a key for
limited testing.
═══════════════════════════════════════════════════════
