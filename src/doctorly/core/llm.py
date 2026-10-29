from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from doctorly.core.config import get_settings


class LLMConfigurationError(RuntimeError):
    pass


def get_llm() -> BaseChatModel:
    settings = get_settings()
    provider = settings.llm_provider.strip().lower()
    model = settings.llm_model.strip()
    if not model:
        raise LLMConfigurationError("LLM_MODEL must not be empty")

    if provider == "google":
        if not settings.gemini_api_key:
            raise LLMConfigurationError(
                "Set GEMINI_API_KEY or GOOGLE_API_KEY to use the Google LLM provider"
            )
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=settings.gemini_api_key,
            temperature=0,
        )

    provider_keys = {
        "openai": settings.openai_api_key,
        "groq": settings.groq_api_key,
    }
    if provider not in provider_keys:
        raise LLMConfigurationError(
            "LLM_PROVIDER must be one of: google, openai, groq"
        )
    api_key = provider_keys[provider]
    if not api_key:
        raise LLMConfigurationError(
            f"Set {provider.upper()}_API_KEY for LLM_PROVIDER={provider}"
        )

    try:
        return init_chat_model(
            model=model,
            model_provider=provider,
            api_key=api_key,
            temperature=0,
        )
    except ImportError as exc:
        raise LLMConfigurationError(
            f"The LangChain integration for {provider} is not installed"
        ) from exc
