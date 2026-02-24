FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/agent/requirements.txt
RUN pip install --no-cache-dir -r /app/agent/requirements.txt

COPY nanoclaw.py /app/agent/nanoclaw.py
COPY llm_client.py /app/agent/llm_client.py
COPY agent_router.py /app/agent/agent_router.py
COPY __init__.py /app/agent/__init__.py
COPY personas/ /app/agent/personas/

RUN useradd -m appuser \
    && mkdir -p /app/shared_data/n8n_inbox /app/shared_data/obsidian_vault /app/shared_data/verified_inbox /app/shared_data/agent_comms /app/shared_data/logs \
    && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "agent.nanoclaw"]
