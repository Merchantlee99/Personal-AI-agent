from typing import Optional

import httpx

PROXY_URL = "http://llm-proxy:8000"


async def call_llm(
    prompt: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """llm-proxy를 통해 LLM API 호출"""
    payload = {
        "provider": provider,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if model:
        payload["model"] = model
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{PROXY_URL}/api/llm", json=payload)
        resp.raise_for_status()
        return resp.json()["content"]


async def web_search(query: str) -> dict:
    """llm-proxy의 search 엔드포인트를 통해 웹검색 수행"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{PROXY_URL}/api/search",
            json={"query": query},
        )
        resp.raise_for_status()
        return resp.json()
