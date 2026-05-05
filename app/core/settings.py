from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    app_base_url: str = "http://localhost:8080"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/webtrak"

    jwt_secret: str = "replace_me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 1440
    refresh_token_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8080/api/v1/auth/google/callback"
    company_email_domain: str = "webknot.in"
    frontend_redirect_uri: str = "http://localhost:3000"
    oauth_auto_create_user: bool = False
    admin_bootstrap_key: str = "wkwkwk123"
    enable_role_checks: bool = True
    enable_scheduler: bool = True
    scheduler_timezone: str = "UTC"

    cookie_secure: bool = False
    cookie_domain: str | None = None

    # SMTP configuration for email delivery (used by the Java-parity EmailService).
    # When `app_env` is not `prod`, recipients are redirected to `smtp_sender`
    # to prevent accidental email delivery to real users.
 
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "varshini.k@webknot.in"
    smtp_password: str = "ueoj wslc cqqu sogt"
    smtp_use_tls: bool = True
    smtp_sender: str = "varshini.k@webknot.in"


@lru_cache
def get_settings() -> Settings:
    return Settings()
