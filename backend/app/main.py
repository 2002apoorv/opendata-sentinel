from fastapi import FastAPI
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router)


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


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OpenData Sentinel",
        "version": settings.VERSION,
    }
