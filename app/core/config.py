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

    # Deepgram (ASR)
    deepgram_api_key: str | None = None

    # OpenAI (LLM)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # ElevenLabs TTS - Natural conversational voice
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" - natural conversational female
    elevenlabs_model: str = "eleven_turbo_v2_5"  # Fast, high quality model
    
    # OpenAI TTS - used for phone calls (24kHz = clean 3:1 ratio to 8kHz)
    tts_model: str = "tts-1-hd"  # Higher quality model
    tts_voice: str = "nova"     # Natural conversational female voice
    tts_speed: float = 1.0

    # Redis (optional for now)
    redis_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()