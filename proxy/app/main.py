from fastapi import FastAPI

from app.middleware.security import SecurityMiddleware
from app.routers import agent, calendar, hermes_briefing, llm, notebooklm, search, telegram, usage
from app.utils.telegram_bridge import ensure_background_poller, stop_background_poller

app = FastAPI(title="NanoClaw LLM Proxy", version="1.0.0")
app.add_middleware(SecurityMiddleware)
app.include_router(llm.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(hermes_briefing.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")
app.include_router(notebooklm.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "llm-proxy"}


@app.on_event("startup")
async def startup_event():
    ensure_background_poller()


@app.on_event("shutdown")
async def shutdown_event():
    await stop_background_poller()
