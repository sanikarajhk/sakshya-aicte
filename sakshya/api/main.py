"""
Sakshya FastAPI Application Server
Provides REST API service for AICTE document validation, mock authority checks,
readiness evaluations, and hash-chained audit trails.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sakshya.core.config import settings
from sakshya.core.database import init_db
from sakshya.api.routes import router

app = FastAPI(
    title=settings.PROJECT_TITLE,
    description="Sakshya - AI-Powered Application Validation, Document Authentication & Regulatory Compliance for AICTE (SIH 2026 Problem Statement SIH26261)",
    version=settings.VERSION
)

# CORS middleware for Streamlit or web UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.API_V1_PREFIX, tags=["Validation & Audit"])


@app.on_event("startup")
def on_startup():
    """Initialize database tables on server start."""
    init_db()


@app.get("/")
def root():
    return {
        "message": "Welcome to Sakshya AICTE Compliance & Authentication Engine",
        "docs_url": "/docs",
        "api_prefix": settings.API_V1_PREFIX
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sakshya.api.main:app", host="0.0.0.0", port=8000, reload=True)
