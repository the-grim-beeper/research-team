from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings


class OpenRouterError(RuntimeError):
    """Raised on a non-2xx response from OpenRouter or any transport failure."""


@dataclass
class ChatResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    raw: dict[str, Any]


async def chat(
    messages: list[dict[str, str]],
    *,
    model: str,
    max_tokens: int = 1000,
    api_key: str | None = None,
    base_url: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ChatResult:
    """Call OpenRouter chat-completions and return text + usage."""
    key = api_key or settings.openrouter_api_key
    if not key:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured")
    url = f"{(base_url or settings.openrouter_base_url).rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": settings.openrouter_app_url,
        "X-Title": settings.openrouter_app_title,
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}

    async with httpx.AsyncClient(transport=transport, timeout=120.0) as cx:
        try:
            resp = await cx.post(url, headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise OpenRouterError(f"Transport error: {e}") from e

    if resp.status_code >= 400:
        raise OpenRouterError(
            f"OpenRouter {resp.status_code}: {resp.text[:500]}"
        )

    body = resp.json()
    try:
        text = body["choices"][0]["message"]["content"] or ""
        usage = body.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
    except (KeyError, IndexError, TypeError) as e:
        raise OpenRouterError(f"Unexpected response shape: {body!r}") from e

    return ChatResult(
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        raw=body,
    )
