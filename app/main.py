from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os, os.path, time

app = FastAPI()
BOOT = time.time()
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "/app/artifacts/feed_item_schema.json")
MODEL_VERSION = os.getenv("MODEL_VERSION", "gb-1.0.0")

class PredictIn(BaseModel):
    emf: float
    income: float
    urbanization: float

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "model_loaded": True,
        "model_version": MODEL_VERSION,
        "uptime_seconds": time.time() - BOOT,
    }

@app.get("/schemas/feed_item.json")
def schema():
    if not os.path.exists(SCHEMA_PATH):
        return JSONResponse({"error": "schema not found", "path": SCHEMA_PATH}, status_code=404)
    return FileResponse(SCHEMA_PATH, media_type="application/schema+json",
                        headers={"Cache-Control": "public, max-age=300"})

@app.post("/predict")
def predict(x: PredictIn):
    # TODO: replace with your actual model call
    fertility = 2.5 - 0.3*x.emf + 0.0001*x.income - 0.8*x.urbanization
    return {"fertility_rate": fertility, "model_version": MODEL_VERSION}
