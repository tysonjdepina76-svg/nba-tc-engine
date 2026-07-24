# api/docs.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import json

def setup_docs(app: FastAPI) -> FastAPI:
    @app.get("/openapi.json", include_in_schema=False)
    async def openapi():
        return get_openapi(
            title="TC Sports API",
            version="1.0.0",
            description="TC Sports App API",
            routes=app.routes,
        )
    return app

def save_openapi_spec(app: FastAPI, path: str = "docs/openapi.json"):
    spec = get_openapi(
        title="TC Sports API",
        version="1.0.0",
        description="TC Sports App API",
        routes=app.routes,
    )
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)
    return path
