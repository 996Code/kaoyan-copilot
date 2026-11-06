"""LLM 客户端（OpenAI 兼容 /chat/completions），配置在 backend/.env：

LLM_BASE_URL=https://api.openai.com/v1   # 任何 OpenAI 兼容接口
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
"""

from typing import AsyncIterator

import httpx

from app.core.config import settings


def llm_ready() -> bool:
    return bool(settings.llm_base_url and settings.llm_api_key and settings.llm_model)


async def chat_complete(messages: list[dict], temperature: float = 0.3) -> str:
    """非流式补全，返回文本。"""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def chat_stream(messages: list[dict], temperature: float = 0.3) -> AsyncIterator[str]:
    """流式补全，逐段 yield 增量文本。"""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    break
                try:
                    import json

                    delta = json.loads(data)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]
                except (ValueError, KeyError, IndexError):
                    continue
