import os


class Config:
    """Application settings, read from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-me"

    # Example: postgresql://postgres:change_me@db:5432/stockflow
    # "db" is the name of the PostgreSQL service in docker-compose.yml
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
