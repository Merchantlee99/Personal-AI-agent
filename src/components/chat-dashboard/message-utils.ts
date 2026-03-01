import type { ChatMessage } from "@/components/chat-dashboard/types";

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Seoul",
  });
}

export function buildApiHistory(history: ChatMessage[]) {
  return history
    .filter((item) => item.role === "user" || item.role === "assistant")
    .map((item) => ({ role: item.role, content: item.content }));
}

export function normalizeAssistantContent(content: string): string {
  return content
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
