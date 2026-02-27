from __future__ import annotations

from app.utils.telegram_bridge_config import allowed_commands


def build_help_text(agent_id: str) -> str:
    allowed = sorted(allowed_commands(agent_id))
    command_help = ", ".join(f"/{cmd}" for cmd in allowed) if allowed else "-"
    return f"사용 가능한 명령: {command_help}\n예시: /chat 오늘 우선순위 정리해줘"


def parse_command(text: str) -> tuple[str, str] | None:
    normalized = text.strip()
    if not normalized:
        return None

    if normalized.startswith("/"):
        parts = normalized.split(maxsplit=1)
        command = parts[0][1:].split("@", 1)[0].strip().lower()
        argument = parts[1].strip() if len(parts) > 1 else ""
        return command, argument

    return None


def build_agent_prompt(command: str, argument: str) -> str:
    if command == "read":
        return (
            "다음 입력을 빠르게 읽고 핵심만 정리해줘.\n"
            "- 결론 1줄\n"
            "- 핵심 근거 2줄\n"
            "- 다음 액션 1줄\n\n"
            f"[입력]\n{argument}"
        )
    if command == "summary":
        return (
            "다음 내용을 간결하게 요약해줘.\n"
            "- 핵심 요약 3줄\n"
            "- 중요 포인트 목록\n\n"
            f"[입력]\n{argument}"
        )
    if command == "trend":
        return (
            "아래 요청을 Hermes 방식으로 처리해줘.\n"
            "- HOT / INSIGHT / MONITOR 분류\n"
            "- 출처가 약하면 ⚠️ 확인 필요 표기\n"
            "- 추천 액션 3개\n\n"
            f"[요청]\n{argument}"
        )
    return argument
