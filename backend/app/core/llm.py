"""LLM 客户端（OpenAI 兼容 /chat/completions）。配置来自 system_settings 表（管理页可改）。"""

from typing import AsyncIterator

import httpx


def llm_ready(cfg: dict) -> bool:
    return bool(cfg.get("llm_base_url") and cfg.get("llm_api_key") and cfg.get("llm_model"))


async def chat_complete(messages: list[dict], cfg: dict, temperature: float = 0.3, timeout: float = 120) -> str:
    """非流式补全，返回文本。"""
    url = cfg["llm_base_url"].rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {cfg['llm_api_key']}"},
            json={"model": cfg["llm_model"], "messages": messages, "temperature": temperature},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def chat_stream(messages: list[dict], cfg: dict, temperature: float = 0.3) -> AsyncIterator[str]:
    """流式补全，逐段 yield 增量文本。"""
    import json

    url = cfg["llm_base_url"].rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {cfg['llm_api_key']}"},
            json={
                "model": cfg["llm_model"],
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
                    delta = json.loads(data)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]
                except (ValueError, KeyError, IndexError):
                    continue
