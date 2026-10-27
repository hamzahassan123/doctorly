from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCTORLY_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://doctorly:doctorly@localhost:5432/doctorly"
    )
    jwt_secret_key: str | None = None
    jwt_access_token_minutes: int = Field(default=30, gt=0, le=1440)
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "DOCTORLY_OTEL_EXPORTER_OTLP_ENDPOINT",
        ),
    )
    otel_service_name: str = Field(
        default="doctorly-api",
        validation_alias=AliasChoices("OTEL_SERVICE_NAME", "DOCTORLY_OTEL_SERVICE_NAME"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
