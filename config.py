import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "papertrail-dev-insecure-secret-key-change-in-prod-2026")
    
    # Database
    DB_PATH = BASE_DIR / "instance" / "papertrail.db"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set True when behind HTTPS in production
    PERMANENT_SESSION_LIFETIME = 3600 * 8  # 8 hours
    
    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600 * 24
    
    # Test-persona registration is opt-in outside automated tests.
    ALLOW_DEV_REGISTRATION = os.environ.get("PAPERTRAIL_ALLOW_DEV_REGISTRATION", "false").lower() in ("true", "1")
    
    # Challenge Mode indicator (for cybersecurity lab evaluation)
    CHALLENGE_MODE = os.environ.get("PAPERTRAIL_CHALLENGE_MODE", "false").lower() in ("true", "1")
    CHALLENGE_FLAG = os.environ.get("PAPERTRAIL_CHALLENGE_FLAG", "FLAG{papertrail_enterprise_workflow_audit_passed_2026}")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = False  # Keep debug mode off by default as requested in prompt
    TESTING = False


class TestingConfig(Config):
    """Testing configuration with in-memory SQLite."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # Disabled during automated HTTP client testing
    SECRET_KEY = "test-secret-key-for-automated-tests"


class ProductionConfig(Config):
    """Production configuration for Ubuntu Server 24.04 LTS."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
