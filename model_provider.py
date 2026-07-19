"""One place to pick the LLM, so the agent code never hard-codes a provider.

DeepAgents (like LangChain) accepts any chat model that implements the
`BaseChatModel` interface, so switching providers is just swapping the object
you pass to `create_deep_agent(model=...)`. This factory returns the right one
based on the MODEL_PROVIDER env var (or an explicit argument).

Supported:
    anthropic  -> Claude              (ANTHROPIC_API_KEY)
    azure      -> Azure OpenAI        (AZURE_OPENAI_* vars)
    gemini     -> Google Gemini       (GOOGLE_API_KEY)
    local      -> any OpenAI-compatible server: vLLM, Ollama, LM Studio,
                  SGLang, TGI, ... (LOCAL_MODEL_BASE_URL)

Examples:
    MODEL_PROVIDER=anthropic MODEL_NAME=claude-sonnet-5
    MODEL_PROVIDER=azure     MODEL_NAME=gpt-4o           # = your deployment name
    MODEL_PROVIDER=gemini    MODEL_NAME=gemini-2.0-flash
    MODEL_PROVIDER=local     MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct \\
        LOCAL_MODEL_BASE_URL=http://localhost:8000/v1
"""

import os

from langchain_core.language_models.chat_models import BaseChatModel


def get_model(provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """Return a chat model for the chosen provider.

    Args:
        provider: one of anthropic | azure | gemini | local.
            Defaults to the MODEL_PROVIDER env var, then "anthropic".
        model: model / deployment name. Defaults to the MODEL_NAME env var.
    """
    provider = (provider or os.getenv("MODEL_PROVIDER", "anthropic")).lower()
    model = model or os.getenv("MODEL_NAME")

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model or "claude-sonnet-5", max_tokens=4096)

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        # azure_deployment is your deployment name; endpoint/version/key come
        # from AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION, AZURE_OPENAI_API_KEY.
        return AzureChatOpenAI(azure_deployment=model or os.getenv("AZURE_OPENAI_DEPLOYMENT"))

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model or "gemini-2.0-flash")

    if provider == "local":
        from langchain_openai import ChatOpenAI

        # Any OpenAI-compatible endpoint. Most local servers ignore the key,
        # but the client still requires one to be set.
        base_url = os.getenv("LOCAL_MODEL_BASE_URL", "http://localhost:8000/v1")
        return ChatOpenAI(
            model=model or "local-model",
            base_url=base_url,
            api_key=os.getenv("LOCAL_MODEL_API_KEY", "not-needed"),
        )

    raise ValueError(
        f"Unknown provider {provider!r}. Use: anthropic | azure | gemini | local."
    )
