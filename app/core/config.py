from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    app_name: str = "gym-call-agent"
    env: str = "dev"  # dev|prod
    log_level: str = "INFO"

    # Network
    public_base_url: str = "http://localhost:8000"  # used later for Twilio webhooks

    # Twilio (optional for now)
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    twilio_validate_signature: bool = False  # Set to True in production

    # Redis (optional for now)
    redis_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()