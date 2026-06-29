from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="TC Sports Live Combos Health")


@app.get("/live-combos/health")
def health():
    return {
        "status": "ok",
        "service": "tc-live-combos",
        "timestamp": datetime.now().isoformat(),
    }