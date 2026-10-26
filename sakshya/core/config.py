"""
Sakshya Core Configuration
SIH 2026 - Problem Statement SIH26261: AI-Powered Application Validation for AICTE
"""

from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "sakshya" / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic_applications"
RULES_DIR = BASE_DIR / "sakshya" / "rules"
DB_PATH = DATA_DIR / "sakshya.db"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Sakshya"
    PROJECT_TITLE: str = "AI-Powered AICTE Document Authentication & Compliance Verification"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # SQLite Database
    DATABASE_URL: str = f"sqlite:///{DB_PATH}"
    
    # Random seed for reproducible synthetic data
    RANDOM_SEED: int = 42
    
    # Confidence routing thresholds
    CONFIDENCE_HIGH_THRESHOLD: float = 0.85
    CONFIDENCE_LOW_THRESHOLD: float = 0.60
    
    # Readiness checklist weightings
    WEIGHT_MANDATORY_DOCS: float = 0.40
    WEIGHT_EXTRACTION_COMPLETENESS: float = 0.25
    WEIGHT_MOCK_ISSUER_STATUS: float = 0.20
    WEIGHT_ANOMALY_CLEANLINESS: float = 0.15
    
    # Mock Issuer Verification Statuses (all 6 required)
    VERIFICATION_STATUSES: list[str] = [
        "verified",
        "mismatch_detected",
        "expired",
        "verification_pending",
        "source_unavailable",
        "manual_review_required"
    ]
    
    # Roles
    ROLE_INSTITUTION: str = "institution"
    ROLE_SCRUTINY_OFFICER: str = "scrutiny_officer"
    ROLE_ADMIN: str = "admin"
    
    # Claude API (Optional / with mock fallback)
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
RULES_DIR.mkdir(parents=True, exist_ok=True)
