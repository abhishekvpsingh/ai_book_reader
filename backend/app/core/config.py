from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "ai_book_reader"
    environment: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./app.db"

    data_root: str = "/data"
    pdf_dir: str = "/data/pdfs"
    image_dir: str = "/data/images"
    audio_dir: str = "/data/audio"

    redis_url: str = "redis://redis:6379/0"
    rq_default_timeout: int = 1200
    rate_limit_per_min: int = 60

    llm_provider: str = "ollama"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3"

    max_summary_chars: int = 18000
    large_content_threshold: int = 22000

    tts_backend: str = "gtts"
    piper_bin: str | None = None
    piper_model: str | None = None
    tts_allow_network: bool = True
    tts_lang: str = "en-in"

    log_level: str = "INFO"


settings = Settings()
