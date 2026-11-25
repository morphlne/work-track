from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_path: str = "data/worktrack.db"
    api_cache_ttl_seconds: int = 43200
    default_latitude: float = 53.9006
    default_longitude: float = 27.5590
    default_city_name: str = "Минск"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_sender_email: str = ""
    lead_recipient_email: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_settings() -> Settings:
    return Settings()
