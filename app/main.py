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

# Newswire endpoints
@app.get("/newswire")
def get_newswire(origin_country: str = None, limit: int = 20):
    """Get enriched newswire items, optionally filtered by origin country"""
    # TODO: Replace with actual data source (database query)
    # For now, return mock data structure
    mock_items = []
    if origin_country == "FI":
        mock_items = [
            {
                "id": "fi-sample-1",
                "title": "Suomen keskuspankki nostaa ohjauskorkoa",
                "source_name": "YLE",
                "source_url": "https://yle.fi/example",
                "published_at": "2025-08-11T10:00:00Z",
                "origin_country": "FI",
                "category_guess": "talous",
                "kicker": "Korkojen nousu kiihtyy",
                "lede": "Suomen Pankki nosti ohjauskorkoa 0,25 prosenttiyksiköllä 4,75 prosenttiin inflaation hillitsemiseksi. Päätös vaikuttaa suoraan asuntolainojen korkoihin ja kulutukseen. Asiantuntijat odottavat lisäkorotuksia syksyllä.",
                "why_it_matters": "- Asuntolainojen korot nousevat 0,25 % heti\n- Kuluttajien ostovoimaa heikkenee 200-300 €/kk keskivertotyöntekijällä\n- Rakennusala odottaa 15-20 % kysynnän laskua",
                "analysis": "Suomen Pankin korkokorotus on suora vastaus kuluttajahintojen 3,8 prosentin nousuun, joka ylittää selvästi 2 prosentin tavoitteen. Päätös heijastaa eurooppalaista trendiä, jossa keskuspankit kiristävät rahapolitiikkaa inflaation hillitsemiseksi. Korkokorotuksen vaikutukset näkyvät nopeimmin asuntolainoissa, joista 80 prosenttia Suomessa on vaihtuvakorkoisia. Keskimääräinen asuntolainan korko nousee nyt 4,2 prosentista 4,45 prosenttiin, mikä tarkoittaa 200 000 euron lainassa noin 50 euron kuukausimaksun nousua. Rakennusalalla odotetaan kysynnän laskua 15-20 prosenttia seuraavan vuoden aikana, kun investointihalukkuus heikkenee. Kulutushyödykkeissä vaikutus näkyy erityisesti autokaupoissa ja kalliimmissa kodinkoneissa, joiden rahoitus kallistuu merkittävästi. Työmarkkinoilla korkojen nousu voi hillitä palkkapainetta, kun inflaatio-odotukset maltillistuvat. Valtiontalouden näkökulmasta korkojen nousu nostaa lainanhoitokustannuksia noin 200 miljoonaa euroa vuositasolla, mikä pakottaa tarkistamaan menokehyksiä. Pankkisektorin kannattavuus sen sijaan paranee, kun korkokate kasvaa nopeammin kuin luottotappiot.",
                "cta": "Seuraa seuraavan kokouksen päätöstä syyskuussa",
                "tags": ["korko", "inflaatio", "suomen-pankki", "asuntolainat"],
                "local_fi": "Korkokorotus vaikuttaa erityisesti Suomen asuntomarkkinoihin, joissa 80% lainoista on vaihtuvakorkoisia. Rakennusala ja kulutushyödykkeet kärsivät eniten.",
                "local_fi_score": 0.95,
                "enriched_at": "2025-08-11T10:05:00Z",
                "model_version": "gpt-4o-fi-v1"
            }
        ]
    else:
        # Mock global items
        mock_items = [
            {
                "id": "global-sample-1", 
                "title": "Federal Reserve signals rate pause",
                "source_name": "Reuters",
                "source_url": "https://reuters.com/example",
                "published_at": "2025-08-11T09:30:00Z",
                "origin_country": "US",
                "category_guess": "finance",
                "kicker": "Fed holds steady at 5.25%",
                "lede": "The Federal Reserve maintained its benchmark interest rate at 5.25% following two consecutive quarters of declining inflation. Chair Powell emphasized data-dependent approach while markets anticipate cuts in Q4. Bond yields fell 15 basis points on the announcement.",
                "why_it_matters": "- Mortgage rates stabilize around 7.2% for 30-year fixed\n- Corporate borrowing costs remain elevated at 6.8% average\n- Dollar weakened 1.2% against major currencies",
                "analysis": "The Federal Reserve's decision to pause rate hikes reflects growing confidence that inflation is sustainably declining toward the 2% target. Powell's emphasis on data dependency signals that future moves will hinge on employment figures and core PCE readings rather than predetermined schedules. The 15 basis point decline in 10-year Treasury yields suggests markets are pricing in a 65% probability of rate cuts by December, up from 40% before the announcement. Corporate credit spreads tightened by 8 basis points, indicating improved risk appetite and easier financing conditions for investment-grade borrowers. The dollar's 1.2% decline against the DXY basket creates headwinds for US exporters but provides relief for emerging market debtors with dollar-denominated obligations. Regional bank stocks rallied 3.2% on prospects of stable net interest margins, while growth stocks in technology and consumer discretionary sectors gained 2.8% as discount rates effectively decreased. Housing market dynamics remain complex, with mortgage demand showing minimal response despite the rate pause, suggesting affordability constraints persist at current price levels. The Fed's dot plot revision will be crucial in September, particularly regarding 2025 projections that currently show three additional cuts. Labor market cooling continues with job openings down 15% year-over-year, though wage growth remains sticky at 4.1% annually.",
                "cta": "Monitor September FOMC meeting for potential pivot signals",
                "tags": ["fed", "interest-rates", "inflation", "monetary-policy"],
                "local_fi": "Fed:n päätös tukee Euroopan keskuspankin toimia ja voi vähentää painetta Suomen korkojen nousulle. Vientiteollisuus hyötyy dollarin heikkenemisestä.",
                "local_fi_score": 0.4,
                "enriched_at": "2025-08-11T09:35:00Z",
                "model_version": "gpt-4o-en-v1"
            }
        ]
    
    # Apply limit
    return {
        "items": mock_items[:limit],
        "total": len(mock_items),
        "origin_country_filter": origin_country
    }

@app.get("/newswire/fi")
def get_newswire_fi(limit: int = 20):
    """Get Finnish newswire items"""
    return get_newswire(origin_country="FI", limit=limit)

# Self-learning feedback endpoint
@app.post("/feedback")
def receive_feedback(request: Request):
    """Receive user feedback for self-learning system"""
    import json
    import sys
    from pathlib import Path
    
    # Add project root to path for imports
    project_root = Path(__file__).parent.parent
    sys.path.append(str(project_root))
    
    try:
        from src.hybrid.collector import FeedbackCollector
        
        # Parse request body
        body = request.json() if hasattr(request, 'json') else {}
        
        event_id = body.get('event_id')
        feedback_type = body.get('type', 'user')  # 'user' or 'editor'
        feedback_data = body.get('data', {})
        
        if not event_id:
            return {"error": "Missing event_id"}
        
        # Log feedback
        collector = FeedbackCollector()
        collector.append_feedback(event_id, feedback_type, feedback_data)
        
        return {
            "status": "success",
            "event_id": event_id,
            "feedback_type": feedback_type
        }
        
    except Exception as e:
        return {"error": f"Failed to process feedback: {str(e)}"}

@app.get("/selflearn/status")
def get_selflearn_status():
    """Get self-learning system status"""
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    sys.path.append(str(project_root))
    
    try:
        from src.hybrid.calibrator import CostController
        from src.hybrid.bandit import BanditRouter
        
        cost_controller = CostController()
        bandit_router = BanditRouter()
        
        # Load latest cycle results
        latest_cycle_path = project_root / "artifacts/selflearn/latest_cycle.json"
        latest_cycle = {}
        if latest_cycle_path.exists():
            import json
            with open(latest_cycle_path, 'r') as f:
                latest_cycle = json.load(f)
        
        return {
            "budget_status": cost_controller.get_status(),
            "bandit_stats": bandit_router.bandit.get_statistics(),
            "latest_cycle": latest_cycle
        }
        
    except Exception as e:
        return {"error": f"Failed to get status: {str(e)}"}

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
