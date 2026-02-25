from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

try:
    from agent.agent_router import AGENTS, log_event, route_to_agent
    from agent.shared_config import (
        AGENT_ALIASES,
        VALID_AGENT_IDS,
        canonical_agent_id as canonical_agent_id_shared,
    )
except ImportError:
    from agent_router import AGENTS, log_event, route_to_agent
    from shared_config import (
        AGENT_ALIASES,
        VALID_AGENT_IDS,
        canonical_agent_id as canonical_agent_id_shared,
    )

INBOX_DIR = Path("/app/shared_data/n8n_inbox")
COMMS_ROOT_DIR = Path("/app/shared_data/agent_comms")
COMMS_INBOX_ROOT = COMMS_ROOT_DIR / "inbox"
COMMS_OUTBOX_ROOT = COMMS_ROOT_DIR / "outbox"
COMMS_ARCHIVE_DIR = COMMS_ROOT_DIR / "archive"
COMMS_DEADLETTER_DIR = COMMS_ROOT_DIR / "deadletter"
COMMS_USER_INBOX_DIR = COMMS_INBOX_ROOT / "user"
VAULT_DIR = Path("/app/shared_data/obsidian_vault")
VERIFIED_DIR = Path("/app/shared_data/verified_inbox")

DEFAULT_AGENT = "owl"
DEFAULT_COMM_TARGET = "ace"
AGENT_PREFIXES = {f"{alias.lower()}_": agent_id for alias, agent_id in AGENT_ALIASES.items()}
KST = timezone(timedelta(hours=9))


def wait_until_stable(file_path: Path, retries: int = 20, delay_sec: float = 0.2) -> bool:
    last_size = -1
    same_size_hits = 0

    for _ in range(retries):
        if not file_path.exists():
            return False

        current_size = file_path.stat().st_size
        if current_size == last_size:
            same_size_hits += 1
            if same_size_hits >= 2:
                return True
        else:
            same_size_hits = 0

        last_size = current_size
        time.sleep(delay_sec)

    return file_path.exists()


def render_markdown(text: str) -> str:
    return f"# NanoClaw 리서치 보고서\n\n{text.rstrip()}\n"


def infer_agent_id_from_filename(filename: str) -> str:
    lower = filename.lower()
    for prefix, agent_id in AGENT_PREFIXES.items():
        if lower.startswith(prefix):
            return agent_id
    return DEFAULT_AGENT


def now_kst_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def canonical_agent_id(value: str, fallback: str) -> str:
    return canonical_agent_id_shared(value, fallback)


def _path_is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_user_inbox_file(path: Path) -> bool:
    return _path_is_under(path, COMMS_USER_INBOX_DIR)


def _is_agent_inbox_file(path: Path) -> bool:
    if not _path_is_under(path, COMMS_INBOX_ROOT):
        return False
    return any(_path_is_under(path, COMMS_INBOX_ROOT / agent_id) for agent_id in VALID_AGENT_IDS)


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def move_to_deadletter(source_path: Path, reason: str) -> Path:
    COMMS_DEADLETTER_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    dest_path = COMMS_DEADLETTER_DIR / f"{source_path.stem}_{timestamp}{source_path.suffix}"
    shutil.move(str(source_path), str(dest_path))
    log_event("COMMS_DEADLETTER", f"source={source_path.name} reason={reason} dest={dest_path.name}")
    return dest_path


def archive_done_message(source_path: Path, payload: dict) -> Path:
    day_dir = COMMS_ARCHIVE_DIR / datetime.now(KST).strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    payload.setdefault("meta", {})
    payload["meta"]["status"] = "done"
    payload["meta"]["archived_at_kst"] = now_kst_iso()
    write_json_atomic(source_path, payload)

    dest_path = day_dir / source_path.name
    if dest_path.exists():
        suffix = datetime.now(KST).strftime("%H%M%S")
        dest_path = day_dir / f"{source_path.stem}_{suffix}{source_path.suffix}"

    shutil.move(str(source_path), str(dest_path))
    return dest_path


def extract_prompt(payload: dict) -> str:
    content = payload.get("content")
    if isinstance(content, dict):
        body = str(content.get("body") or "").strip()
        if body:
            return body
        subject = str(content.get("subject") or "").strip()
        if subject:
            return subject
    elif isinstance(content, str):
        content_text = content.strip()
        if content_text:
            return content_text

    instruction = str(payload.get("instruction") or "").strip()
    if instruction:
        return instruction

    return ""


def write_verified_report(target_agent: str, source_name: str, result: str) -> Path:
    VERIFIED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = VERIFIED_DIR / f"{target_agent}_{timestamp}_{Path(source_name).stem}.md"
    report_content = (
        f"# Agent Response ({target_agent})\n\n"
        f"- Source: {source_name}\n"
        f"- Timestamp: {timestamp}\n\n"
        f"{result.strip()}\n"
    )
    report_path.write_text(report_content, encoding="utf-8")
    return report_path


def process_text_file(source_path: Path) -> None:
    if source_path.suffix.lower() != ".txt":
        return
    if not source_path.exists():
        return
    if not wait_until_stable(source_path):
        logging.warning("Skipped unstable text file: %s", source_path.name)
        return

    agent_id = infer_agent_id_from_filename(source_path.name)

    try:
        raw_text = source_path.read_text(encoding="utf-8", errors="replace")
        target_path = VAULT_DIR / f"{source_path.stem}.md"

        markdown_output = render_markdown(raw_text)
        try:
            routed_output = asyncio.run(route_to_agent(agent_id, raw_text, include_memory=agent_id == "ace")).strip()
            if routed_output:
                markdown_output = f"{routed_output}\n"
        except Exception:
            logging.exception("LLM routing failed; fallback used for %s", source_path.name)
            log_event("LLM_FALLBACK", f"text_file={source_path.name} agent={agent_id}")

        target_path.write_text(markdown_output, encoding="utf-8")

        try:
            source_path.unlink()
        except Exception:
            logging.exception("Processed but could not delete source file: %s", source_path.name)
            log_event("DELETE_FAILED", f"text_file={source_path.name}")
            return

        log_event("TXT_PROCESSED", f"source={source_path.name} agent={agent_id} output={target_path.name}")
        logging.info("Processed text file %s -> %s (agent: %s)", source_path.name, target_path.name, agent_id)
    except Exception:
        logging.exception("Failed processing text file: %s", source_path.name)
        log_event("TXT_PROCESS_ERROR", f"source={source_path.name}")


def process_comm_file(source_path: Path) -> None:
    if source_path.suffix.lower() != ".json":
        return
    if not source_path.exists():
        return
    if not wait_until_stable(source_path):
        logging.warning("Skipped unstable comm file: %s", source_path.name)
        return

    try:
        raw_payload = source_path.read_text(encoding="utf-8", errors="replace")
        payload = json.loads(raw_payload)
    except Exception:
        logging.exception("Invalid comm message JSON: %s", source_path.name)
        log_event("COMMS_INVALID_JSON", f"source={source_path.name} (unable to parse)")
        try:
            move_to_deadletter(source_path, "invalid_json")
        except Exception:
            logging.exception("Failed moving invalid JSON to deadletter: %s", source_path.name)
        return

    meta = payload.setdefault("meta", {})
    target_agent = canonical_agent_id(
        str(meta.get("to") or payload.get("to") or DEFAULT_COMM_TARGET),
        DEFAULT_COMM_TARGET,
    )
    meta["to"] = target_agent

    if target_agent not in AGENTS:
        logging.warning("Unknown comm target '%s': %s", target_agent, source_path.name)
        log_event("COMMS_UNKNOWN_TARGET", f"source={source_path.name} target={target_agent}")
        try:
            move_to_deadletter(source_path, f"unknown_target_{target_agent}")
        except Exception:
            logging.exception("Failed moving unknown-target file to deadletter: %s", source_path.name)
        return

    prompt = extract_prompt(payload)
    if not prompt:
        logging.warning("Comm message has no content: %s", source_path.name)
        log_event("COMMS_EMPTY", f"source={source_path.name}")
        try:
            move_to_deadletter(source_path, "empty_content")
        except Exception:
            logging.exception("Failed moving empty-content file to deadletter: %s", source_path.name)
        return

    meta["status"] = "processing"
    meta["processing_started_at_kst"] = now_kst_iso()
    try:
        write_json_atomic(source_path, payload)
    except Exception:
        logging.exception("Failed setting processing status for: %s", source_path.name)
        log_event("COMMS_STATUS_UPDATE_FAILED", f"source={source_path.name} status=processing")

    try:
        routed_output = asyncio.run(
            route_to_agent(target_agent, prompt, include_memory=(target_agent == "ace"))
        ).strip()
    except Exception:
        logging.exception("Comm routing failed; fallback used for %s", source_path.name)
        log_event("COMMS_LLM_FALLBACK", f"source={source_path.name} agent={target_agent}")
        routed_output = render_markdown(prompt)

    try:
        report_path = write_verified_report(target_agent, source_path.name, routed_output)
        meta["status"] = "done"
        meta["processed_by"] = "nanoclaw-agent"
        meta["processed_at_kst"] = now_kst_iso()
        archived_path = archive_done_message(source_path, payload)
        log_event(
            "COMMS_PROCESSED",
            f"source={source_path.name} target={target_agent} output={report_path.name} archived={archived_path.name}",
        )
        logging.info(
            "Processed comm file %s -> %s (agent: %s, archived: %s)",
            source_path.name,
            report_path.name,
            target_agent,
            archived_path.name,
        )
    except Exception:
        logging.exception("Failed finalizing comm file: %s", source_path.name)
        log_event("COMMS_PROCESS_ERROR", f"source={source_path.name} agent={target_agent}")
        if source_path.exists():
            try:
                move_to_deadletter(source_path, "finalize_error")
            except Exception:
                logging.exception("Failed moving errored file to deadletter: %s", source_path.name)


class TextInboxHandler(FileSystemEventHandler):
    def __init__(self, lock: Lock) -> None:
        super().__init__()
        self._lock = lock

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".txt":
            return
        with self._lock:
            process_text_file(path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest_path = getattr(event, "dest_path", None)
        if not dest_path:
            return
        path = Path(dest_path)
        if path.suffix.lower() != ".txt":
            return
        with self._lock:
            process_text_file(path)


class CommsInboxHandler(FileSystemEventHandler):
    def __init__(self, lock: Lock) -> None:
        super().__init__()
        self._lock = lock

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".json":
            return
        if _is_user_inbox_file(path) or not _is_agent_inbox_file(path):
            return
        with self._lock:
            process_comm_file(path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest_path = getattr(event, "dest_path", None)
        if not dest_path:
            return
        path = Path(dest_path)
        if path.suffix.lower() != ".json":
            return
        if _is_user_inbox_file(path) or not _is_agent_inbox_file(path):
            return
        with self._lock:
            process_comm_file(path)


def process_backlog() -> None:
    for txt_file in sorted(INBOX_DIR.glob("*.txt")):
        process_text_file(txt_file)

    for agent_id in sorted(VALID_AGENT_IDS):
        agent_inbox = COMMS_INBOX_ROOT / agent_id
        if not agent_inbox.exists():
            continue
        for comm_file in sorted(agent_inbox.rglob("*.json")):
            process_comm_file(comm_file)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    COMMS_INBOX_ROOT.mkdir(parents=True, exist_ok=True)
    COMMS_OUTBOX_ROOT.mkdir(parents=True, exist_ok=True)
    COMMS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    COMMS_DEADLETTER_DIR.mkdir(parents=True, exist_ok=True)
    COMMS_USER_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    for agent_id in VALID_AGENT_IDS:
        (COMMS_INBOX_ROOT / agent_id).mkdir(parents=True, exist_ok=True)
        (COMMS_OUTBOX_ROOT / agent_id).mkdir(parents=True, exist_ok=True)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    VERIFIED_DIR.mkdir(parents=True, exist_ok=True)

    process_backlog()

    observer = Observer()
    lock = Lock()
    observer.schedule(TextInboxHandler(lock), str(INBOX_DIR), recursive=False)
    observer.schedule(CommsInboxHandler(lock), str(COMMS_INBOX_ROOT), recursive=True)
    observer.start()
    log_event("STARTUP", "NanoClaw watcher started")
    logging.info("NanoClaw monitoring started: inbox=%s comms=%s", INBOX_DIR, COMMS_INBOX_ROOT)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("NanoClaw stopping...")
        log_event("SHUTDOWN", "NanoClaw watcher stopping")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
