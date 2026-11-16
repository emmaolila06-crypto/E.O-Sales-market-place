from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "E.O SALES LTD API"
    environment: str = "development"
    database_url: str = "sqlite:///./eo_sales.db"
    jwt_secret: str = "replace-this-development-secret"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    marketplace_commission_percent: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
