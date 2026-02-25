import time
import os
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_LOCAL_WEBHOOK = "http://n8n:5678/webhook/hermes-trend"
N8N_WEBHOOK_URL_INTERNAL = os.getenv("N8N_WEBHOOK_URL_INTERNAL", "").strip()
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()


def resolve_n8n_webhook_url() -> str:
    return N8N_WEBHOOK_URL_INTERNAL or N8N_WEBHOOK_URL or DEFAULT_LOCAL_WEBHOOK


class SearchRequest(BaseModel):
    query: str
    source: str = "nanoclaw"
    agentId: str = "dolphin"


class SearchResponse(BaseModel):
    final_text: str
    filename: str


@router.post("/search", response_model=SearchResponse)
async def web_search(req: SearchRequest):
    webhook_url = resolve_n8n_webhook_url()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                webhook_url,
                json={
                    "message": req.query,
                    "source": req.source,
                    "agentId": req.agentId,
                    "tavily_api_key": TAVILY_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Search webhook call failed")
        raise HTTPException(status_code=502, detail="Search webhook call failed")

    # n8n response can be a list
    if isinstance(data, list):
        data = data[0] if data else {}

    return SearchResponse(
        final_text=data.get("final_text", ""),
        filename=data.get("filename", f"research_{int(time.time())}.txt"),
    )
