import json
import logging
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _redact_pii(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _redact_pii(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_redact_pii(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_pii(item) for item in value)
    if isinstance(value, set):
        return {_redact_pii(item) for item in value}
    if not isinstance(value, str):
        return value

    redacted = re.sub(
        r"(?i)([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        "[REDACTED_EMAIL]",
        value,
    )
    redacted = re.sub(
        r"(?<!\w)(?:\+?92|0)?\d[\d\s().-]{7,}\d(?!\w)",
        "[REDACTED_PHONE]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+",
        r"\1[REDACTED_TOKEN]",
        redacted,
    )
    return redacted


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_pii(record.getMessage()),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                continue
            if key.startswith("_"):
                continue
            payload[key] = _redact_pii(value)

        return json.dumps(payload, default=str, ensure_ascii=False)


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
    llm_provider: str = Field(
        default="google",
        validation_alias=AliasChoices("LLM_PROVIDER", "DOCTORLY_LLM_PROVIDER"),
    )
    llm_model: str = Field(
        default="gemini-1.5-flash",
        validation_alias=AliasChoices("LLM_MODEL", "DOCTORLY_LLM_MODEL"),
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "DOCTORLY_GEMINI_API_KEY",
        ),
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "DOCTORLY_OPENAI_API_KEY"),
    )
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "DOCTORLY_GROQ_API_KEY"),
    )
    faq_max_cosine_distance: float = Field(default=0.55, gt=0, le=2)
    emergency_response_template: str = (
        "Your message may describe a medical emergency. Go to the Emergency "
        "Department or call the hospital Emergency Department line "
        "(051-111-555-911) immediately. In Pakistan, you can also call Rescue "
        "1122 or Edhi 115. Do not wait for an appointment or a chat response. "
        "This service cannot diagnose or provide emergency medical care."
    )
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
    langsmith_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "DOCTORLY_LANGSMITH_API_KEY"),
    )
    langsmith_project: str = Field(
        default="doctorly",
        validation_alias=AliasChoices("LANGSMITH_PROJECT", "DOCTORLY_LANGSMITH_PROJECT"),
    )
    langsmith_tracing: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGSMITH_TRACING", "DOCTORLY_LANGSMITH_TRACING"),
    )
    langsmith_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_ENDPOINT", "DOCTORLY_LANGSMITH_ENDPOINT"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "DOCTORLY_LOG_LEVEL"),
    )
    smtp_host: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_HOST", "DOCTORLY_SMTP_HOST"),
    )
    smtp_port: int = Field(
        default=587,
        validation_alias=AliasChoices("SMTP_PORT", "DOCTORLY_SMTP_PORT"),
    )
    smtp_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_USERNAME", "DOCTORLY_SMTP_USERNAME"),
    )
    smtp_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_PASSWORD", "DOCTORLY_SMTP_PASSWORD"),
    )
    smtp_use_tls: bool = Field(
        default=True,
        validation_alias=AliasChoices("SMTP_USE_TLS", "DOCTORLY_SMTP_USE_TLS"),
    )
    email_from: str = Field(
        default="no-reply@doctorly.local",
        validation_alias=AliasChoices("EMAIL_FROM", "DOCTORLY_EMAIL_FROM"),
    )


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(get_settings().log_level.upper())
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        return

    for handler in root.handlers:
        handler.setFormatter(JsonFormatter())


def configure_langsmith() -> None:
    settings = get_settings()
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langsmith_tracing else "false"


@lru_cache
def get_settings() -> Settings:
    return Settings()
