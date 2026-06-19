"""Unified LLM provider client — wraps OpenAI, Anthropic, and Google."""

from dataclasses import dataclass
from typing import Any

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    usage: dict[str, Any]  # input_tokens, output_tokens, cost


# Pricing per 1M tokens (input, output) in USD — updated June 2026
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-oss:20b-cloud": (0.50, 1.50),
    "gpt-oss:120b-cloud": (1.00, 3.00),
    "qwen3-coder:480b-cloud": (1.50, 4.50),
    "deepseek-v3.1:671b-cloud": (1.20, 3.60),
    "o3-mini": (1.10, 4.40),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
}


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Try prefix match
        for key, val in MODEL_PRICING.items():
            if model.startswith(key.split("-")[0]):
                pricing = val
                break
    if not pricing:
        return 0.0
    input_cost, output_cost = pricing
    return ((input_tokens / 1_000_000) * input_cost) + ((output_tokens / 1_000_000) * output_cost)


def _get_chat_model(provider: str, model_id: str, temperature: float = 0.3) -> Any:
    """Get the appropriate LangChain chat model for a provider."""
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        kwargs = {
            "model": model_id,
            "temperature": temperature,
            "api_key": settings.openai_api_key,
        }
        # Support custom base URL for OpenAI-compatible APIs (e.g., Ollama)
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return ChatOpenAI(**kwargs)
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return ChatAnthropic(
            model=model_id,
            temperature=temperature,
            api_key=settings.anthropic_api_key,
        )
    elif provider == "google":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            google_api_key=settings.google_api_key,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def call_llm(
    provider: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float = 0.3,
) -> LLMResponse:
    """Call an LLM and return a standardized LLMResponse.

    Args:
        provider: "openai" | "anthropic" | "google"
        model_id: Model identifier (e.g., "gpt-4o-mini")
        system: System prompt
        user: User message
        temperature: Sampling temperature
    """
    try:
        chat_model = _get_chat_model(provider, model_id, temperature)
        messages = [SystemMessage(content=system), HumanMessage(content=user)]
        response = await chat_model.ainvoke(messages)

        # Extract usage metadata
        usage_meta = response.response_metadata.get("usage") or response.response_metadata.get("token_usage") or {}
        input_tokens = usage_meta.get("input_tokens") or usage_meta.get("prompt_tokens") or 0
        output_tokens = usage_meta.get("output_tokens") or usage_meta.get("completion_tokens") or 0

        cost = _calculate_cost(model_id, input_tokens, output_tokens)

        logger.info(
            "LLM call completed",
            provider=provider,
            model=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        return LLMResponse(
            content=response.content if isinstance(response.content, str) else str(response.content),
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
            },
        )

    except ValueError:
        raise  # Config errors should propagate
    except Exception as e:
        logger.error("LLM call failed", provider=provider, model=model_id, error=str(e))
        raise
