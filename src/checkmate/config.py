from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    github_app_id: int
    github_app_private_key_path: str
    github_webhook_secret: str

    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://checkmate:checkmate@localhost:5432/checkmate"

    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
