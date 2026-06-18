import os
import sys

from pydantic_settings import BaseSettings

# Allow HTTP in development (Authlib enforces HTTPS by default)
if sys.flags.dev_mode or "pytest" in sys.modules:
    os.environ.setdefault("AUTHLIB_INSECURE_TRANSPORT", "1")
# Always set it for now since we're in early development
os.environ.setdefault("AUTHLIB_INSECURE_TRANSPORT", "1")


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    database_url: str = "sqlite+aiosqlite:///oauth.db"

    # OAuth Server
    issuer: str = "http://localhost:8000"
    access_token_expires_minutes: int = 60
    refresh_token_expires_days: int = 30
    authorization_code_expires_minutes: int = 10

    # Session
    secret_key: str = "change-me-to-a-random-secret-key-in-production"
    session_cookie_name: str = "oauth_session"

    # PBKDF2
    pbkdf2_iterations: int = 600_000


settings = Settings()
