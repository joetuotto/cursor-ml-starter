from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

@app.get("/artifacts/report.enriched.json")
def enriched_report():
    # Try different paths for enriched report
    paths = [
        "/app/artifacts/report.enriched.json",
        "./artifacts/report.enriched.json",
        "artifacts/report.enriched.json"
    ]
    
    for path in paths:
        if os.path.exists(path):
            return FileResponse(path, media_type="application/json",
                               headers={"Cache-Control": "public, max-age=60"})
    
    return JSONResponse({"error": "enriched report not found", "checked_paths": paths}, status_code=404)

@app.post("/predict")
def predict(x: PredictIn):
    # TODO: replace with your actual model call
    fertility = 2.5 - 0.3*x.emf + 0.0001*x.income - 0.8*x.urbanization
    return {"fertility_rate": fertility, "model_version": MODEL_VERSION}

# Mount static files for the newswire UI
# Check if static files exist (for local dev vs container)
static_path = "/app/static" if os.path.exists("/app/static") else "./web/dist"
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    
    # Serve the main UI at /newswire and root
    @app.get("/newswire/{path:path}")
    @app.get("/newswire/")
    @app.get("/")
    def serve_ui(path: str = ""):
        index_file = os.path.join(static_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file, media_type="text/html")
        return JSONResponse({"error": "UI not available"}, status_code=404)
