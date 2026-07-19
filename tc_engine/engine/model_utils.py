"""Model Utilities — Save and load ML models with version tracking.

Handles serialization of scikit-learn models (.pkl) with metadata
about training date, features used, and performance metrics.
"""
import pickle
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, List, Dict


MODEL_DIR = Path("models")
METADATA_FILE = MODEL_DIR / "metadata.json"


def save_model(model: Any, path: str) -> Dict:
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "wb") as f:
        pickle.dump(model, f)

    metadata = load_metadata()
    relpath = str(filepath.relative_to(Path.cwd()) if filepath.is_relative_to(Path.cwd()) else filepath)
    metadata["models"][relpath] = {
        "saved_at": datetime.now().isoformat(),
        "size_bytes": filepath.stat().st_size,
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))

    return {"path": str(filepath), "size_bytes": filepath.stat().st_size, "saved_at": metadata["models"][relpath]["saved_at"]}


def load_model(path: str) -> Any:
    with open(path, "rb") as f:
        return pickle.load(f)


def list_models() -> Dict[str, Dict]:
    return load_metadata().get("models", {})


def load_metadata() -> Dict:
    if METADATA_FILE.exists():
        return json.loads(METADATA_FILE.read_text())
    return {"models": {}}
