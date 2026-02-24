from fastapi import FastAPI

from app.routers import agent, llm, search

app = FastAPI(title="NanoClaw LLM Proxy", version="1.0.0")
app.include_router(llm.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "llm-proxy"}
