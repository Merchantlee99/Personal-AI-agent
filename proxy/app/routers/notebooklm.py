from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.agent_registry import normalize_agent_id

router = APIRouter()

KST = timezone(timedelta(hours=9))
NOTEBOOKLM_ROOT = Path("/app/shared_data/agent_comms/notebooklm")
PENDING_DIR = NOTEBOOKLM_ROOT / "pending"
APPROVED_DIR = NOTEBOOKLM_ROOT / "approved"
UPLOADED_DIR = NOTEBOOKLM_ROOT / "uploaded"
FAILED_DIR = NOTEBOOKLM_ROOT / "failed"
REJECTED_DIR = NOTEBOOKLM_ROOT / "rejected"
VAULT_DIR = Path("/app/vault")


class NotebookLMStageRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    source: str = "clio_manual"
    tags: list[str] = Field(default_factory=list)
    created_by: str = "owl"


class NotebookLMStageFromVaultRequest(BaseModel):
    vault_file: str = Field(min_length=1)
    title: Optional[str] = None
    source: str = "clio_vault"
    tags: list[str] = Field(default_factory=list)
    created_by: str = "owl"


class NotebookLMApproveRequest(BaseModel):
    id: str = Field(min_length=1)
    approve: bool = True


def _now_kst_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    for directory in [PENDING_DIR, APPROVED_DIR, UPLOADED_DIR, FAILED_DIR, REJECTED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def _item_path(directory: Path, item_id: str) -> Path:
    normalized = "".join(ch for ch in item_id if ch.isalnum() or ch in {"-", "_"}).strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid notebook item id")
    return directory / f"{normalized}.json"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _move(path: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / path.name
    path.replace(destination)
    return destination


def _build_item_payload(
    *,
    title: str,
    content: str,
    source: str,
    tags: list[str],
    created_by: str,
    vault_file: str | None = None,
) -> dict[str, Any]:
    normalized_creator = normalize_agent_id(created_by)
    if normalized_creator != "owl":
        raise HTTPException(status_code=400, detail="Only Clio(owl) can stage NotebookLM payloads")

    item_id = str(uuid.uuid4())
    return {
        "id": item_id,
        "title": title.strip(),
        "content": content.strip(),
        "source": source.strip() or "clio_manual",
        "tags": [tag.strip() for tag in tags if tag.strip()],
        "created_by": normalized_creator,
        "created_at": _now_kst_iso(),
        "status": "pending",
        "vault_file": vault_file or "",
    }


def _connector_enabled() -> bool:
    value = os.getenv("NOTEBOOKLM_CONNECTOR_ENABLED", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _connector_url() -> str:
    return os.getenv("NOTEBOOKLM_CONNECTOR_URL", "").strip()


def _connector_api_key() -> str:
    return os.getenv("NOTEBOOKLM_CONNECTOR_API_KEY", "").strip()


def _connector_timeout() -> float:
    raw = os.getenv("NOTEBOOKLM_CONNECTOR_TIMEOUT_SEC", "30").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 30.0
    return min(max(value, 5.0), 120.0)


async def _upload_to_connector(item: dict[str, Any]) -> tuple[bool, str]:
    url = _connector_url()
    if not _connector_enabled() or not url:
        return False, "connector_disabled"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    api_key = _connector_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "content": item.get("content", ""),
        "source": item.get("source", ""),
        "tags": item.get("tags", []),
        "created_at": item.get("created_at", ""),
        "created_by": item.get("created_by", "owl"),
    }
    timeout = _connector_timeout()
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
    if 200 <= response.status_code < 300:
        return True, "uploaded"
    return False, f"connector_error:{response.status_code}"


def _resolve_vault_file(relative_file: str) -> Path:
    candidate = (VAULT_DIR / relative_file).resolve()
    try:
        candidate.relative_to(VAULT_DIR.resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="vault_file must be inside /app/vault")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="vault_file not found")
    return candidate


@router.get("/notebooklm/health")
async def notebooklm_health():
    _ensure_dirs()
    return {
        "status": "ok",
        "connector_enabled": _connector_enabled(),
        "connector_url_configured": bool(_connector_url()),
        "pending_count": len(list(PENDING_DIR.glob("*.json"))),
    }


@router.get("/notebooklm/pending")
async def notebooklm_pending(limit: int = 20):
    _ensure_dirs()
    files = sorted(PENDING_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    capped = files[: max(1, min(limit, 200))]
    items: list[dict[str, Any]] = []
    for file_path in capped:
        try:
            parsed = _read_json(file_path)
            items.append(
                {
                    "id": parsed.get("id", file_path.stem),
                    "title": parsed.get("title", ""),
                    "source": parsed.get("source", ""),
                    "created_at": parsed.get("created_at", ""),
                    "created_by": parsed.get("created_by", ""),
                    "tags": parsed.get("tags", []),
                    "file": file_path.name,
                }
            )
        except Exception:
            continue
    return {"status": "ok", "pending": items}


@router.post("/notebooklm/stage")
async def notebooklm_stage(req: NotebookLMStageRequest):
    _ensure_dirs()
    payload = _build_item_payload(
        title=req.title,
        content=req.content,
        source=req.source,
        tags=req.tags,
        created_by=req.created_by,
    )
    pending_path = _item_path(PENDING_DIR, str(payload["id"]))
    _write_json_atomic(pending_path, payload)
    return {
        "status": "pending",
        "id": payload["id"],
        "path": str(pending_path),
    }


@router.post("/notebooklm/stage-from-vault")
async def notebooklm_stage_from_vault(req: NotebookLMStageFromVaultRequest):
    _ensure_dirs()
    vault_file = _resolve_vault_file(req.vault_file)
    content = vault_file.read_text(encoding="utf-8")
    title = req.title or vault_file.stem.replace("-", " ").strip().title()
    payload = _build_item_payload(
        title=title,
        content=content,
        source=req.source,
        tags=req.tags,
        created_by=req.created_by,
        vault_file=str(vault_file.relative_to(VAULT_DIR)),
    )
    pending_path = _item_path(PENDING_DIR, str(payload["id"]))
    _write_json_atomic(pending_path, payload)
    return {
        "status": "pending",
        "id": payload["id"],
        "path": str(pending_path),
        "vault_file": payload["vault_file"],
    }


@router.post("/notebooklm/approve")
async def notebooklm_approve(req: NotebookLMApproveRequest):
    _ensure_dirs()
    pending_path = _item_path(PENDING_DIR, req.id)
    if not pending_path.exists():
        raise HTTPException(status_code=404, detail="Pending notebook item not found")

    payload = _read_json(pending_path)
    payload["reviewed_at"] = _now_kst_iso()

    if not req.approve:
        payload["status"] = "rejected"
        rejected_path = _move(pending_path, REJECTED_DIR)
        _write_json_atomic(rejected_path, payload)
        return {"status": "rejected", "id": payload.get("id", req.id), "path": str(rejected_path)}

    uploaded, reason = await _upload_to_connector(payload)
    if uploaded:
        payload["status"] = "uploaded"
        payload["uploaded_at"] = _now_kst_iso()
        destination = _move(pending_path, UPLOADED_DIR)
        _write_json_atomic(destination, payload)
        return {"status": "uploaded", "id": payload.get("id", req.id), "path": str(destination)}

    if reason == "connector_disabled":
        payload["status"] = "approved_local"
        destination = _move(pending_path, APPROVED_DIR)
        _write_json_atomic(destination, payload)
        return {
            "status": "approved_local",
            "id": payload.get("id", req.id),
            "path": str(destination),
            "message": "Connector disabled. Item approved locally.",
        }

    payload["status"] = "failed"
    payload["error"] = reason
    destination = _move(pending_path, FAILED_DIR)
    _write_json_atomic(destination, payload)
    raise HTTPException(
        status_code=502,
        detail=f"NotebookLM connector upload failed ({reason})",
    )
