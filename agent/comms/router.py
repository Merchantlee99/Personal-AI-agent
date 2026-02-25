from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from agent.shared_config import (
        VALID_AGENT_IDS,
        canonical_agent_id as canonical_agent_id_shared,
    )
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from shared_config import (
        VALID_AGENT_IDS,
        canonical_agent_id as canonical_agent_id_shared,
    )

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def now_kst_iso() -> str:
    return now_kst().isoformat(timespec="seconds")


def canonical_agent_id(value: str) -> str:
    return canonical_agent_id_shared(value, "")


def resolve_comms_root() -> Path:
    env_root = os.getenv("AGENT_COMMS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    container_root = Path("/app/shared_data/agent_comms")
    if container_root.exists():
        return container_root

    return (Path(__file__).resolve().parents[2] / "shared_data" / "agent_comms").resolve()


def setup_logger(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    suffix = now_kst().strftime("%H%M%S")
    return path.with_name(f"{path.stem}_{suffix}{path.suffix}")


def move_deadletter(source: Path, deadletter_root: Path, reason: str) -> None:
    deadletter_root.mkdir(parents=True, exist_ok=True)
    suffix = now_kst().strftime("%Y%m%d_%H%M%S")
    destination = deadletter_root / f"{source.stem}_{suffix}{source.suffix}"
    shutil.move(str(source), str(destination))
    logging.error("Moved to deadletter: %s (reason=%s)", destination, reason)


def archive_done(source: Path, payload: dict, archive_root: Path) -> None:
    day_dir = archive_root / now_kst().strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    payload.setdefault("meta", {})
    payload["meta"]["status"] = "archived"
    payload["meta"]["archived_at_kst"] = now_kst_iso()
    write_json_atomic(source, payload)
    destination = unique_destination(day_dir / source.name)
    shutil.move(str(source), str(destination))
    logging.info("Archived message: %s", destination)


def deliver_from_outbox(outbox_root: Path, inbox_root: Path, deadletter_root: Path) -> None:
    for source in sorted(outbox_root.glob("*/*.json")):
        try:
            payload = load_json(source)
            meta = payload.setdefault("meta", {})

            from_agent = canonical_agent_id(str(meta.get("from") or source.parent.name))
            to_agent = canonical_agent_id(str(meta.get("to") or ""))
            if from_agent not in VALID_AGENT_IDS or to_agent not in VALID_AGENT_IDS:
                raise ValueError(f"invalid routing: from={from_agent}, to={to_agent}")

            meta["from"] = from_agent
            meta["to"] = to_agent
            meta["status"] = "delivered"
            meta["delivered_at_kst"] = now_kst_iso()

            destination_dir = inbox_root / to_agent
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = unique_destination(destination_dir / source.name)

            write_json_atomic(destination, payload)
            source.unlink()
            logging.info("Delivered: %s -> %s", source, destination)
        except Exception as exc:
            logging.exception("Failed delivering outbox file: %s", source)
            if source.exists():
                move_deadletter(source, deadletter_root, f"deliver_error:{exc}")


def archive_done_from_inbox(inbox_root: Path, archive_root: Path, deadletter_root: Path) -> None:
    for source in sorted(inbox_root.glob("*/*.json")):
        try:
            payload = load_json(source)
            status = str(payload.get("meta", {}).get("status", "")).strip().lower()
            if status != "done":
                continue
            archive_done(source, payload, archive_root)
        except Exception as exc:
            logging.exception("Failed archiving inbox file: %s", source)
            if source.exists():
                move_deadletter(source, deadletter_root, f"archive_error:{exc}")


def run_once(comms_root: Path) -> None:
    outbox_root = comms_root / "outbox"
    inbox_root = comms_root / "inbox"
    archive_root = comms_root / "archive"
    deadletter_root = comms_root / "deadletter"

    for agent in VALID_AGENT_IDS:
        (outbox_root / agent).mkdir(parents=True, exist_ok=True)
        (inbox_root / agent).mkdir(parents=True, exist_ok=True)
    archive_root.mkdir(parents=True, exist_ok=True)
    deadletter_root.mkdir(parents=True, exist_ok=True)

    deliver_from_outbox(outbox_root, inbox_root, deadletter_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route async agent messages from outbox to inbox.")
    parser.add_argument("--once", action="store_true", help="Run one routing pass and exit.")
    parser.add_argument("--watch", action="store_true", help="Run continuously.")
    parser.add_argument("--interval", type=int, default=10, help="Watch interval in seconds.")
    parser.add_argument(
        "--archive-done",
        action="store_true",
        help="Also archive done messages from inbox (disabled by default to avoid overlap with nanoclaw).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    comms_root = resolve_comms_root()
    setup_logger(comms_root / "router.log")

    if args.watch:
        logging.info("Router started in watch mode (interval=%ss)", args.interval)
        while True:
            run_once(comms_root)
            if args.archive_done:
                archive_done_from_inbox(
                    comms_root / "inbox",
                    comms_root / "archive",
                    comms_root / "deadletter",
                )
            time.sleep(max(args.interval, 1))
    else:
        run_once(comms_root)
        if args.archive_done:
            archive_done_from_inbox(
                comms_root / "inbox",
                comms_root / "archive",
                comms_root / "deadletter",
            )
        logging.info("Router finished one pass.")


if __name__ == "__main__":
    main()
