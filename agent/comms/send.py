from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

VALID_AGENTS = {"ace", "owl", "dolphin"}
AGENT_ALIASES = {
    "ace": "ace",
    "에이스": "ace",
    "morpheus": "ace",
    "모르피어스": "ace",
    "owl": "owl",
    "clio": "owl",
    "클리오": "owl",
    "dolphin": "dolphin",
    "hermes": "dolphin",
    "헤르메스": "dolphin",
}
MESSAGE_TYPES = {"report", "request", "handoff", "alert"}
PRIORITY_LEVELS = {"high", "normal", "low"}
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def resolve_comms_root() -> Path:
    env_root = os.getenv("AGENT_COMMS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    container_root = Path("/app/shared_data/agent_comms")
    if container_root.exists():
        return container_root

    return (Path(__file__).resolve().parents[2] / "shared_data" / "agent_comms").resolve()


def canonical_agent_id(raw: str) -> str:
    value = raw.strip().lower()
    return AGENT_ALIASES.get(value, value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an async agent message in outbox.")
    parser.add_argument("--from", dest="from_agent", required=True, help="Sender agent id or alias")
    parser.add_argument("--to", required=True, help="Receiver agent id or alias")
    parser.add_argument("--type", dest="message_type", choices=sorted(MESSAGE_TYPES), required=True)
    parser.add_argument("--priority", choices=sorted(PRIORITY_LEVELS), default="normal")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--requires-response", action="store_true")
    parser.add_argument("--deadline", help="ISO datetime with timezone (optional)")
    parser.add_argument("--callback-to", help="Agent id or alias for callback")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    from_agent = canonical_agent_id(args.from_agent)
    to_agent = canonical_agent_id(args.to)
    callback_to = canonical_agent_id(args.callback_to) if args.callback_to else from_agent

    if from_agent not in VALID_AGENTS:
        raise SystemExit(f"Invalid --from agent: {from_agent}")
    if to_agent not in VALID_AGENTS:
        raise SystemExit(f"Invalid --to agent: {to_agent}")
    if callback_to not in VALID_AGENTS:
        raise SystemExit(f"Invalid --callback-to agent: {callback_to}")

    now = now_kst()
    timestamp_kst = now.isoformat(timespec="seconds")
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    file_name = f"{from_agent}_{to_agent}_{date_part}_{time_part}_{args.message_type}.json"

    payload = {
        "meta": {
            "id": str(uuid.uuid4()),
            "from": from_agent,
            "to": to_agent,
            "timestamp_kst": timestamp_kst,
            "type": args.message_type,
            "priority": args.priority,
            "status": "pending",
        },
        "content": {
            "subject": args.subject,
            "body": args.body,
            "attachments": [],
        },
        "routing": {
            "requires_response": bool(args.requires_response),
            "deadline": args.deadline or "",
            "callback_to": callback_to,
        },
    }

    comms_root = resolve_comms_root()
    outbox_dir = comms_root / "outbox" / from_agent
    outbox_dir.mkdir(parents=True, exist_ok=True)

    output_path = outbox_dir / file_name
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
