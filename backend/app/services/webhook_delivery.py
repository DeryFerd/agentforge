"""Webhook delivery service — sends HTTP POST with retry logic."""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx
import structlog

logger = structlog.get_logger()

MAX_RETRIES = 3
RETRY_BACKOFF = [1, 5, 30]  # seconds between retries
REQUEST_TIMEOUT = 10  # seconds


async def deliver_webhook(
    url: str,
    payload: dict,
    secret: str,
) -> dict:
    """Deliver a webhook payload with HMAC signature and retry logic.

    Args:
        url: Target URL to POST to
        payload: JSON payload to send
        secret: Webhook secret for HMAC-SHA256 signature

    Returns:
        dict with delivery result: status_code, success, attempts
    """
    body = json.dumps(payload, default=str).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AgentForge-Signature": f"sha256={signature}",
        "X-AgentForge-Timestamp": datetime.now(timezone.utc).isoformat(),
        "User-Agent": "AgentForge-Webhook/1.0",
    }

    attempts = 0
    last_error = None

    for attempt in range(MAX_RETRIES):
        attempts += 1
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(url, content=body, headers=headers)

                if response.status_code < 300:
                    logger.info(
                        "Webhook delivered",
                        url=url,
                        status=response.status_code,
                        attempt=attempts,
                    )
                    return {
                        "status_code": response.status_code,
                        "success": True,
                        "attempts": attempts,
                        "delivered_at": datetime.now(timezone.utc).isoformat(),
                    }
                elif response.status_code < 500:
                    # 4xx errors are not retryable
                    logger.warning(
                        "Webhook delivery failed (client error)",
                        url=url,
                        status=response.status_code,
                    )
                    return {
                        "status_code": response.status_code,
                        "success": False,
                        "attempts": attempts,
                        "error": f"Client error: {response.status_code}",
                    }
                else:
                    # 5xx errors are retryable
                    last_error = f"Server error: {response.status_code}"
                    logger.warning(
                        "Webhook delivery failed (server error), will retry",
                        url=url,
                        status=response.status_code,
                        attempt=attempts,
                    )

        except httpx.TimeoutException:
            last_error = "Request timed out"
            logger.warning("Webhook delivery timed out", url=url, attempt=attempts)
        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning("Webhook delivery error", url=url, error=str(e), attempt=attempts)

        # Wait before retry
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])

    logger.error("Webhook delivery failed after all retries", url=url, attempts=attempts)
    return {
        "status_code": 0,
        "success": False,
        "attempts": attempts,
        "error": last_error,
    }


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify a webhook's HMAC-SHA256 signature.

    Args:
        body: Raw request body
        signature: Signature from X-AgentForge-Signature header (format: sha256=...)
        secret: Webhook secret

    Returns:
        True if signature is valid
    """
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
