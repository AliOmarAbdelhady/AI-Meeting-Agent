from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
CREDENTIALS_DIR = BASE_DIR / "credentials"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "AI Meeting Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'meeting_agent.db'}"
    database_url_sync: str = f"sqlite:///{DATA_DIR / 'meeting_agent.db'}"

    # ── OpenAI / LLM ────────────────────────────────────────────────────
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.3
    openai_base_url: Optional[str] = None  # e.g. https://api.x.ai/v1 for Grok, or a local server

    # ── Whisper (Speech-to-Text) ────────────────────────────────────────
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: Optional[str] = None  # None = auto-detect

    # ── Email (SendGrid) ────────────────────────────────────────────────
    sendgrid_api_key: Optional[SecretStr] = None
    email_from_address: str = "meeting-agent@example.com"
    email_from_name: str = "AI Meeting Agent"
    email_provider: str = "sendgrid"  # "sendgrid" or "smtp"

    # ── Email (SMTP fallback) ───────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True

    # ── Meeting Bot ─────────────────────────────────────────────────────
    bot_headless: bool = True
    bot_browser_timeout: int = 30
    # Persistent browser profile — keeps the Google session between runs so the
    # bot only needs to be signed in once. Holds sensitive cookies (gitignored).
    bot_user_data_dir: str = str(DATA_DIR / "browser-profile")
    # How long to wait for the authenticated "Ask to join" / "Join now" screen,
    # allowing time for a manual Google sign-in on the first run.
    bot_login_timeout_seconds: int = 180
    bot_audio_sample_rate: int = 16000
    bot_audio_channels: int = 1
    bot_google_email: Optional[str] = None
    bot_google_password: Optional[SecretStr] = None

    # ── Google Calendar ─────────────────────────────────────────────────
    google_calendar_credentials_path: str = str(CREDENTIALS_DIR / "google-credentials.json")
    google_calendar_token_path: str = str(CREDENTIALS_DIR / "google-token.json")

    # ── Audio Recording ─────────────────────────────────────────────────
    audio_output_dir: str = str(AUDIO_DIR)
    audio_format: str = "wav"
    audio_max_duration_seconds: int = 14400  # 4 hours

    # ── Scheduler ───────────────────────────────────────────────────────
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    scheduler_check_interval_seconds: int = 60

    def get_openai_api_key(self) -> str:
        """Get the OpenAI API key as a plain string."""
        return self.openai_api_key.get_secret_value()

    def get_sendgrid_api_key(self) -> Optional[str]:
        """Get the SendGrid API key as a plain string."""
        if self.sendgrid_api_key:
            return self.sendgrid_api_key.get_secret_value()
        return None

    def get_smtp_password(self) -> str:
        """Get the SMTP password as a plain string."""
        return self.smtp_password.get_secret_value()


# Singleton settings instance
settings = Settings()

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
