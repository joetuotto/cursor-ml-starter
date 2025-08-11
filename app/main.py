from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, os.path, time

app = FastAPI(title="PARANOID Models API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://paranoidmodels.com", "https://www.paranoidmodels.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOOT = time.time()
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "/app/artifacts/feed_item_schema.json")
MODEL_VERSION = os.getenv("MODEL_VERSION", "gb-1.0.0")

# Paths for static assets
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
INDEX_PATH = os.path.join(ASSETS_DIR, "index.html")

# Mount static assets
if os.path.exists(os.path.join(ASSETS_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(ASSETS_DIR, "assets"), html=False), name="assets")

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

@app.head("/health")
def health_head():
    return Response(status_code=200)

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

# Root page (GET/HEAD) - serve index.html
@app.get("/")
def root():
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH, media_type="text/html")
    return JSONResponse({"error": "UI not available"}, status_code=404)

@app.head("/")
def root_head():
    return Response(status_code=200)

# SPA fallback - any unknown path returns index.html
@app.get("/{full_path:path}")
def spa_fallback(full_path: str, request: Request):
    # Return assets directly if they exist
    candidate = os.path.join(ASSETS_DIR, full_path)
    if os.path.isfile(candidate):
        return FileResponse(candidate)

    # Otherwise SPA fallback to index.html
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH, media_type="text/html")
    return JSONResponse({"error": "UI not available"}, status_code=404)

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
