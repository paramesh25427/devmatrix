import os
from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_canonical_paths():
    """Derives canonical paths for data, storage, and database."""
    # Find root directory of the Devmatrix project
    # config.py is at <root>/backend/app/core/config.py
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root_dir = os.path.dirname(backend_dir)
    
    data_dir = os.environ.get("DEVMATRIX_DATA_DIR", os.path.join(root_dir, "data"))
    storage_dir = os.environ.get("DEVMATRIX_STORAGE_DIR", os.path.join(root_dir, "storage"))
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    
    canonical_db_file = os.path.join(data_dir, "devmatrix.db").replace(os.sep, "/")
    default_db_url = f"sqlite:///{canonical_db_file}"
    return root_dir, data_dir, storage_dir, default_db_url


_ROOT_DIR, _DATA_DIR, _STORAGE_DIR, _DEFAULT_DB_URL = get_canonical_paths()


class Settings(BaseSettings):
    """DevMatrix AI backend configuration settings."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DevMatrix AI Backend"
    app_env: str = "development"
    debug: bool = True
    demo_mode: bool = Field(default_factory=lambda: os.environ.get("DEMO_MODE", "false").lower() in ("true", "1", "yes"))

    # Canonical database URL
    database_url: str = Field(default_factory=lambda: os.environ.get("DATABASE_URL", _DEFAULT_DB_URL))

    # Security & JWT Auth
    jwt_secret_key: str = Field(default="devmatrix_insecure_jwt_secret_key_change_in_production_2026")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Uploads and storage configuration
    storage_dir: str = Field(default_factory=lambda: _STORAGE_DIR)
    max_upload_size_bytes: int = 15 * 1024 * 1024  # 15 MB per file
    allowed_extensions: List[str] = Field(
        default_factory=lambda: ["pdf", "docx", "xlsx", "csv", "txt", "md"]
    )

    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # ==========================================
    # AI Provider Configurations
    # ==========================================

    # Primary: Google Gemini API
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_enabled: bool = True
    gemini_timeout_seconds: float = 60.0
    gemini_max_retries: int = 2

    # Second Fallback: NVIDIA NIM API
    nvidia_nim_api_key: Optional[str] = None
    nvidia_nim_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_nim_endpoint: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_enabled: bool = True
    nvidia_nim_timeout_seconds: float = 120.0
    nvidia_nim_max_retries: int = 2
    nvidia_nim_max_tokens: int = 4096

    # Optional: xAI Grok API (Disabled by default)
    grok_api_key: Optional[str] = None
    grok_model: str = "grok-2-latest"
    grok_base_url: str = "https://api.x.ai/v1"
    grok_enabled: bool = False
    grok_timeout_seconds: float = 30.0
    grok_max_retries: int = 1

    # General AI Retry & Backoff Configuration
    initial_retry_delay_seconds: float = 2.0

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforces that production deployments cannot use placeholder JWT secrets."""
        if str(self.app_env).strip().lower() in ("production", "prod"):
            insecure_placeholders = {
                "devmatrix_insecure_jwt_secret_key_change_in_production_2026",
                "secret",
                "changeme",
                "default",
                "your-secret-key",
            }
            if not self.jwt_secret_key or self.jwt_secret_key in insecure_placeholders or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "FATAL SECURITY MISCONFIGURATION: Insecure or default JWT secret key detected in production environment! "
                    "You must configure a strong, random JWT_SECRET_KEY of at least 32 characters."
                )
        return self

    @property
    def uploads_dir(self) -> str:
        d = os.path.join(self.storage_dir, "uploads")
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def extracted_dir(self) -> str:
        d = os.path.join(self.storage_dir, "extracted")
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def requirements_dir(self) -> str:
        d = os.path.join(self.storage_dir, "requirements")
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def reports_dir(self) -> str:
        d = os.path.join(self.storage_dir, "reports")
        os.makedirs(d, exist_ok=True)
        return d


settings = Settings()

# Ensure directories exist
os.makedirs(settings.uploads_dir, exist_ok=True)
os.makedirs(settings.extracted_dir, exist_ok=True)
os.makedirs(settings.requirements_dir, exist_ok=True)
os.makedirs(settings.reports_dir, exist_ok=True)
