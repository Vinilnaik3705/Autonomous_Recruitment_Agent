"""Single provider switch for Gemini and local Ollama.

Models are constructed lazily, only when an extraction is requested.
"""

from backend.config import Settings


def create_chat_model(settings: Settings):
    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0,
            timeout=30,
            max_retries=0,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            client_kwargs={"timeout": 30},
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
