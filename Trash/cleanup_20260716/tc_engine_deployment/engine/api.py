from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import json

app = FastAPI(title="TC Engine API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
    }


@app.get("/model/metrics")
async def model_metrics():
    model_dir = os.environ.get("MODEL_DIR", "/app/models")
    metrics_path = os.path.join(model_dir, "training_metrics.json")
    if not os.path.exists(metrics_path):
        return {"model_loaded": False, "message": "Run train_with_shap.py first"}
    with open(metrics_path) as f:
        metrics = json.load(f)
    return {"model_loaded": True, **metrics}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
