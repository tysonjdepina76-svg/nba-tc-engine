import os
import glob
import shutil
from datetime import datetime

def cleanup_obsolete():
    project_root = "/home/workspace/Projects"
    print(f"🧹 Starting cleanup in {project_root}...")

    # Patterns to remove
    patterns = [
        "**/*.DEPRECATED*",
        "**/zombie_results_mlb_*.json",
        "**/results_mlb_*.json",
        "tc_unified.py",
        "**/old_*",
        "**/__pycache__"
    ]

    removed = 0
    for pattern in patterns:
        for f in glob.glob(os.path.join(project_root, pattern), recursive=True):
            try:
                if os.path.isfile(f):
                    os.remove(f)
                    print(f"Removed file: {f}")
                    removed += 1
                elif os.path.isdir(f):
                    shutil.rmtree(f)
                    print(f"Removed dir: {f}")
                    removed += 1
            except Exception as e:
                print(f"Warning skipping {f}: {e}")

    print(f"✅ Cleanup complete. Removed {removed} items.")

if __name__ == "__main__":
    cleanup_obsolete()
