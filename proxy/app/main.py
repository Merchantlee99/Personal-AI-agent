from fastapi import FastAPI

from app.middleware.security import SecurityMiddleware
from app.routers import agent, calendar, hermes_briefing, llm, search

app = FastAPI(title="NanoClaw LLM Proxy", version="1.0.0")
app.add_middleware(SecurityMiddleware)
app.include_router(llm.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(hermes_briefing.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "llm-proxy"}
