"""Snapshot hook - create a snapshot before any risky change.

Wraps any function: if it fails, you can restore the prior state.
"""
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

SNAPSHOT_DIR = Path("/home/workspace/tc-sports-app/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def create_snapshot(source: str, label: str = "") -> str:
    """Snapshot a file or directory. Returns snapshot path."""
    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = label.replace(" ", "_").replace("/", "_")[:50] if label else "snap"
    dest = SNAPSHOT_DIR / f"{safe_label}_{timestamp}"
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / src.name)
    manifest = {
        "snapshot_path": str(dest),
        "source": str(src),
        "label": label,
        "timestamp": datetime.now().isoformat(),
    }
    manifest_file = dest / "manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)
    return str(dest)


def list_snapshots() -> list:
    snapshots = []
    for p in sorted(SNAPSHOT_DIR.iterdir(), reverse=True):
        if p.is_dir():
            manifest = p / "manifest.json"
            if manifest.exists():
                with open(manifest) as f:
                    snapshots.append(json.load(f))
    return snapshots


def restore_snapshot(snapshot_path: str) -> bool:
    """Restore from a snapshot to its original location."""
    snap = Path(snapshot_path)
    manifest = snap / "manifest.json"
    if not manifest.exists():
        return False
    with open(manifest) as f:
        info = json.load(f)
    src = Path(info["source"])
    if src.exists():
        if src.is_dir():
            shutil.rmtree(src)
        else:
            src.unlink()
    if snap.is_dir():
        files = [p for p in snap.iterdir() if p.name != "manifest.json"]
        if len(files) == 1 and files[0].is_file():
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(files[0], src)
        else:
            shutil.copytree(snap, src)
    return True
