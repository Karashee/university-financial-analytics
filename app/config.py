from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    database_url: str
    test_database_url: str
    sqlite_test_database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    debug: bool = False
    
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
