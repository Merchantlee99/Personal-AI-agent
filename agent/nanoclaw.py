from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

try:
    from agent.agent_router import AGENTS, log_event, route_to_agent
except ImportError:
    from agent_router import AGENTS, log_event, route_to_agent

INBOX_DIR = Path("/app/shared_data/n8n_inbox")
COMMS_DIR = Path("/app/shared_data/agent_comms")
VAULT_DIR = Path("/app/shared_data/obsidian_vault")
VERIFIED_DIR = Path("/app/shared_data/verified_inbox")

DEFAULT_AGENT = "owl"
AGENT_PREFIXES = {
    "ace_": "ace",
    "owl_": "owl",
    "dolphin_": "dolphin",
}


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
        log_event("COMMS_INVALID_JSON", f"source={source_path.name}")
        return

    target_agent = str(payload.get("to", DEFAULT_AGENT)).strip().lower()
    if target_agent not in AGENTS:
        logging.warning("Unknown target agent '%s' in %s. Fallback to %s", target_agent, source_path.name, DEFAULT_AGENT)
        log_event("COMMS_UNKNOWN_AGENT", f"source={source_path.name} target={target_agent}")
        target_agent = DEFAULT_AGENT

    prompt = str(payload.get("content") or payload.get("instruction") or "").strip()
    if not prompt:
        logging.warning("Comm message has no content: %s", source_path.name)
        log_event("COMMS_EMPTY", f"source={source_path.name}")
        return

    try:
        routed_output = asyncio.run(
            route_to_agent(target_agent, prompt, include_memory=target_agent == "ace")
        ).strip()
    except Exception:
        logging.exception("Comm routing failed; fallback used for %s", source_path.name)
        log_event("COMMS_LLM_FALLBACK", f"source={source_path.name} agent={target_agent}")
        routed_output = render_markdown(prompt)

    try:
        report_path = write_verified_report(target_agent, source_path.name, routed_output)
        source_path.unlink()
        log_event("COMMS_PROCESSED", f"source={source_path.name} target={target_agent} output={report_path.name}")
        logging.info("Processed comm file %s -> %s (agent: %s)", source_path.name, report_path.name, target_agent)
    except Exception:
        logging.exception("Failed finalizing comm file: %s", source_path.name)
        log_event("COMMS_PROCESS_ERROR", f"source={source_path.name}")


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
        with self._lock:
            process_comm_file(path)


def process_backlog() -> None:
    for txt_file in sorted(INBOX_DIR.glob("*.txt")):
        process_text_file(txt_file)

    for comm_file in sorted(COMMS_DIR.glob("*.json")):
        process_comm_file(comm_file)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    COMMS_DIR.mkdir(parents=True, exist_ok=True)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    VERIFIED_DIR.mkdir(parents=True, exist_ok=True)

    process_backlog()

    observer = Observer()
    lock = Lock()
    observer.schedule(TextInboxHandler(lock), str(INBOX_DIR), recursive=False)
    observer.schedule(CommsInboxHandler(lock), str(COMMS_DIR), recursive=False)
    observer.start()
    log_event("STARTUP", "NanoClaw watcher started")
    logging.info("NanoClaw monitoring started: inbox=%s comms=%s", INBOX_DIR, COMMS_DIR)

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
