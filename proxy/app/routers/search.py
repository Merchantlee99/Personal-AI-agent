import logging
import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.agent_context import fetch_n8n_search

router = APIRouter()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str
    source: str = "nanoclaw"
    agentId: str = "dolphin"


class SearchResponse(BaseModel):
    final_text: str
    filename: str


@router.post("/search", response_model=SearchResponse)
async def web_search(req: SearchRequest):
    tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
    try:
        final_text, filename = await fetch_n8n_search(
            req.query,
            tavily_api_key,
            req.agentId,
            req.source,
        )
    except Exception:
        logger.exception("Search webhook call failed")
        raise HTTPException(status_code=502, detail="Search webhook call failed")

    return SearchResponse(
        final_text=final_text,
        filename=filename or f"research_{int(time.time())}.txt",
    )
