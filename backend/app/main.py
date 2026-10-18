from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.api.routes import router

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OpenData Sentinel",
    description="AI-Powered Government Data Quality Monitoring and Anomaly Detection Platform",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
is_wildcard = "*" in settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_wildcard else settings.CORS_ORIGINS,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$" if not is_wildcard else None,
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount API routes
app.include_router(router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OpenData Sentinel",
        "version": settings.VERSION,
    }


# Static SPA mounting for production / unified hosting
frontend_dist = settings.BASE_DIR / "frontend" / "dist"
if (frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    async def serve_spa_root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" not in accept and ("application/json" in accept or accept == "*/*"):
            return {
                "service": "OpenData Sentinel",
                "description": "Government Data Quality Monitoring & Anomaly Detection Platform",
                "version": settings.VERSION,
                "docs": "/docs",
                "health": "/health",
                "api_v1": "/api",
            }
        return FileResponse(frontend_dist / "index.html")


    @app.get("/{full_path:path}")
    async def serve_spa_fallback(full_path: str):
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return None
        candidate = frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "service": "OpenData Sentinel",
            "description": "Government Data Quality Monitoring & Anomaly Detection Platform",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health",
            "api_v1": "/api",
        }

