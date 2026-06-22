"""Unified LLM provider client — wraps OpenAI, Anthropic, and Google."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
import yaml
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def _load_model_picing() -> dict[str, tuple[float, float]]:
    """Load model pricing from YAML config file."""
    pricing_file = Path(__file__).parent / "model_pricing.yaml"
    try:
        with open(pricing_file) as f:
            data = yaml.safe_load(f)
        return {model: tuple(prices) for model, prices in data.get("models", {}).items()}
    except Exception as e:
        logger.warning("Failed to load model pricing config", error=str(e))
        return {}


# Pricing per 1M tokens (input, output) in USD — loaded from model_pricing.yaml
MODEL_PRICING: dict[str, tuple[float, float]] = _load_model_picing()


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    usage: dict[str, Any]  # input_tokens, output_tokens, cost


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


class LLMTransientError(Exception):
    """Transient LLM error that should be retried (rate limit, server error)."""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(LLMTransientError),
    reraise=True,
)
async def call_llm(
    provider: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float = 0.3,
) -> LLMResponse:
    """Call an LLM and return a standardized LLMResponse.

    Retries up to 3 times with exponential backoff on transient errors
    (rate limits, server errors). Configuration errors propagate immediately.

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
        raise  # Config errors should propagate immediately
    except Exception as e:
        error_str = str(e).lower()
        # Check if this is a transient error (rate limit, server error, timeout)
        is_transient = any(keyword in error_str for keyword in [
            "rate limit", "429", "500", "502", "503", "504", "timeout", "overloaded"
        ])
        if is_transient:
            logger.warning(
                "LLM transient error, will retry",
                provider=provider,
                model=model_id,
                error=str(e),
            )
            raise LLMTransientError(str(e)) from e
        else:
            logger.error("LLM call failed", provider=provider, model=model_id, error=str(e))
            raise
