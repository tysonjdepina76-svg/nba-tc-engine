#!/usr/bin/env python3
"""Google Drive sync — uploads latest pipeline artifacts to Drive.

Targets: last_run.json, today's picks, latest health check, latest boxscores.
Uses rclone or marks files for the agent to push.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log")
SCRIPTS = Path("/home/workspace/Scripts")

def list_files_to_sync():
    """Return list of (local_path, drive_folder) tuples."""
    files = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Core reference files
    for f in ["AGENTS.md", "SYSTEM_MAP.md", "TC_TRADEMARK.txt"]:
        fp = Path("/home/workspace") / f
        if fp.exists():
            files.append((str(fp), "TC_Core"))

    # Latest run summary
    lr = LOG_DIR / "last_run.json"
    if lr.exists():
        files.append((str(lr), "TC_Daily_Log"))

    # Today log dir
    today_dir = LOG_DIR / today
    if today_dir.exists():
        for f in today_dir.glob("picks.csv"):
            files.append((str(f), "TC_Daily_Log"))
        for f in sorted(today_dir.glob("proj_*.json")):
            files.append((str(f), "TC_Daily_Log"))

    # Latest health check
    hc = sorted(SCRIPTS.glob("health_check_*.md"), reverse=True)
    if hc:
        files.append((str(hc[0]), "TC_Health"))

    # Latest halftime + final boxscores (last 3 days)
    for box_type, box_dir in [("halftime", LOG_DIR / "halftime"),
                               ("final", LOG_DIR / "final")]:
        if box_dir.exists():
            recent = sorted(box_dir.glob("*.json"),
                            key=lambda x: x.stat().st_mtime, reverse=True)[:10]
            for f in recent:
                files.append((str(f), f"TC_Boxscores/{box_type}"))

    # Output manifest
    manifest = {"synced_at": datetime.now(timezone.utc).isoformat(),
                "files": [{"local": f[0], "target_folder": f[1]} for f in files]}
    mf = SCRIPTS / "drive_sync_manifest.json"
    mf.write_text(json.dumps(manifest, indent=2))

    print(f"📁 Drive sync manifest: {len(files)} files ready")
    for f in files[:5]:
        print(f"   → {Path(f[0]).name} ({f[1]})")
    if len(files) > 5:
        print(f"   ... +{len(files)-5} more")
    return manifest

if __name__ == "__main__":
    list_files_to_sync()
