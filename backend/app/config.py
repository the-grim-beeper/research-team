from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://research:research@localhost:5432/research"
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 43200  # 30 days
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_url: str = "https://research-team.local"
    openrouter_app_title: str = "Research Team"
    summary_model: str = "openai/gpt-4o-mini"
    max_tokens_default: int = 1000
    daily_run_hour_utc: int = 3


settings = Settings()
