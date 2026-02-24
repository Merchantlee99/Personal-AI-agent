import time
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")


class SearchRequest(BaseModel):
    query: str
    source: str = "nanoclaw"
    agentId: str = "dolphin"


class SearchResponse(BaseModel):
    final_text: str
    filename: str


@router.post("/search", response_model=SearchResponse)
async def web_search(req: SearchRequest):
    if not N8N_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="N8N_WEBHOOK_URL not configured")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                N8N_WEBHOOK_URL,
                json={"message": req.query, "source": req.source, "agentId": req.agentId},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # n8n response can be a list
    if isinstance(data, list):
        data = data[0] if data else {}

    return SearchResponse(
        final_text=data.get("final_text", ""),
        filename=data.get("filename", f"research_{int(time.time())}.txt"),
    )
