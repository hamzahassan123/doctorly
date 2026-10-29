from collections.abc import Callable

import pytest

import doctorly.core.llm as llm
from doctorly.core.config import Settings
from doctorly.core.llm import LLMConfigurationError


def _settings(
    provider: str,
    model: str = "example-model",
    *,
    gemini_api_key: str | None = None,
    openai_api_key: str | None = None,
    groq_api_key: str | None = None,
) -> Settings:
    return Settings(
        _env_file=None,
        llm_provider=provider,
        llm_model=model,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        groq_api_key=groq_api_key,
    )


def test_google_provider_uses_gemini_chat_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: dict[str, object] = {}

    class FakeGoogleModel:
        def __init__(self, **kwargs: object) -> None:
            constructed.update(kwargs)

    monkeypatch.setattr(
        llm,
        "get_settings",
        lambda: _settings(
            "google",
            "gemini-1.5-flash",
            gemini_api_key="gemini-test-key",
        ),
    )
    monkeypatch.setattr(llm, "ChatGoogleGenerativeAI", FakeGoogleModel)

    result = llm.get_llm()

    assert isinstance(result, FakeGoogleModel)
    assert constructed == {
        "model": "gemini-1.5-flash",
        "api_key": "gemini-test-key",
        "temperature": 0,
    }


@pytest.mark.parametrize(
    ("provider", "settings_factory", "expected_key"),
    [
        (
            "openai",
            lambda: _settings("openai", openai_api_key="openai-test-key"),
            "openai-test-key",
        ),
        (
            "groq",
            lambda: _settings("groq", groq_api_key="groq-test-key"),
            "groq-test-key",
        ),
    ],
)
def test_other_providers_use_langchain_model_factory(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    settings_factory: Callable[[], Settings],
    expected_key: str,
) -> None:
    call_args: dict[str, object] = {}

    def fake_init_chat_model(**kwargs: object) -> object:
        call_args.update(kwargs)
        return object()

    monkeypatch.setattr(llm, "get_settings", settings_factory)
    monkeypatch.setattr(llm, "init_chat_model", fake_init_chat_model)

    result = llm.get_llm()

    assert result is not None
    assert call_args == {
        "model": "example-model",
        "model_provider": provider,
        "api_key": expected_key,
        "temperature": 0,
    }


def test_provider_without_key_fails_with_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "get_settings", lambda: _settings("google"))

    with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
        llm.get_llm()


def test_unsupported_provider_fails_with_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "get_settings", lambda: _settings("unsupported"))

    with pytest.raises(LLMConfigurationError, match="LLM_PROVIDER"):
        llm.get_llm()


def test_llm_settings_read_unprefixed_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "DOCTORLY_LLM_PROVIDER",
        "DOCTORLY_LLM_MODEL",
        "DOCTORLY_GEMINI_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.setenv("LLM_MODEL", "gemini-test")
    monkeypatch.setenv("GOOGLE_API_KEY", "environment-test-key")

    settings = Settings(_env_file=None)

    assert settings.llm_provider == "google"
    assert settings.llm_model == "gemini-test"
    assert settings.gemini_api_key == "environment-test-key"


def test_llm_settings_default_to_google_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "LLM_PROVIDER",
        "DOCTORLY_LLM_PROVIDER",
        "LLM_MODEL",
        "DOCTORLY_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_provider == "google"
    assert settings.llm_model == "gemini-1.5-flash"
