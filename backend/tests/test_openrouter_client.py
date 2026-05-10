import httpx
import pytest

from app.services.openrouter import OpenRouterError, chat


def _mock_transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


async def test_chat_returns_text_and_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = request.read().decode()
        assert '"messages"' in body
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )

    r = await chat(
        [{"role": "user", "content": "hi"}],
        model="anthropic/claude-haiku-4-5",
        api_key="test-key",
        transport=_mock_transport(handler),
    )
    assert r.text == "hello"
    assert r.prompt_tokens == 5
    assert r.completion_tokens == 2


async def test_chat_raises_on_4xx():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    with pytest.raises(OpenRouterError):
        await chat(
            [{"role": "user", "content": "hi"}],
            model="anthropic/claude-haiku-4-5",
            api_key="test-key",
            transport=_mock_transport(handler),
        )


async def test_chat_requires_api_key(monkeypatch):
    monkeypatch.setattr("app.services.openrouter.settings.openrouter_api_key", "")
    with pytest.raises(OpenRouterError):
        await chat(
            [{"role": "user", "content": "hi"}],
            model="anthropic/claude-haiku-4-5",
        )
