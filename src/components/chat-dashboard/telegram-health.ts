import type { CSSProperties } from "react";
import { TELEGRAM_CODES, type TelegramCode } from "@/lib/telegram-codes";

export type DashboardAgentId = "ace" | "owl" | "dolphin";

export type TelegramHealthAgent = {
  agent_id: DashboardAgentId;
  agent_name: string;
  token_configured: boolean;
  allow_chat_ids_count: number;
  allowed_commands: string[];
  polling_enabled: boolean;
};

export type TelegramHealthBridge = {
  bridge_enabled: boolean;
  poll_interval_sec: number;
  enabled_agents: string[];
  agents: TelegramHealthAgent[];
  background_running: boolean;
};

export type TelegramHealthPayload = {
  status: "ok" | "error";
  code: TelegramCode;
  message: string;
  retryable: boolean;
  telegram?: TelegramHealthBridge;
};

export type TelegramBadgeTone = "ok" | "warn" | "error" | "off" | "muted";

export type TelegramBadge = {
  label: string;
  tone: TelegramBadgeTone;
  code: string;
};

export const TELEGRAM_BADGE_STYLE: Record<TelegramBadgeTone, CSSProperties> = {
  ok: {
    background: "rgba(16,185,129,0.16)",
    border: "1px solid rgba(16,185,129,0.42)",
    color: "#6EE7B7",
  },
  warn: {
    background: "rgba(234,179,8,0.14)",
    border: "1px solid rgba(234,179,8,0.4)",
    color: "#FDE68A",
  },
  error: {
    background: "rgba(244,63,94,0.14)",
    border: "1px solid rgba(244,63,94,0.4)",
    color: "#FDA4AF",
  },
  off: {
    background: "rgba(100,116,139,0.16)",
    border: "1px solid rgba(100,116,139,0.42)",
    color: "#CBD5E1",
  },
  muted: {
    background: "rgba(148,163,184,0.12)",
    border: "1px solid rgba(148,163,184,0.28)",
    color: "#94A3B8",
  },
};

function isDashboardAgentId(value: string): value is DashboardAgentId {
  return value === "ace" || value === "owl" || value === "dolphin";
}

export function normalizeTelegramHealthAgent(raw: unknown): TelegramHealthAgent | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const candidate = raw as Partial<TelegramHealthAgent>;
  if (!isDashboardAgentId(String(candidate.agent_id ?? ""))) {
    return null;
  }
  return {
    agent_id: candidate.agent_id as DashboardAgentId,
    agent_name: String(candidate.agent_name ?? candidate.agent_id),
    token_configured: Boolean(candidate.token_configured),
    allow_chat_ids_count: Number(candidate.allow_chat_ids_count ?? 0),
    allowed_commands: Array.isArray(candidate.allowed_commands)
      ? candidate.allowed_commands.map((item) => String(item))
      : [],
    polling_enabled: Boolean(candidate.polling_enabled),
  };
}

export function buildBridgeAgentMap(telegramHealth: TelegramHealthPayload | null) {
  const map: Partial<Record<DashboardAgentId, TelegramHealthAgent>> = {};
  const bridgeAgents = telegramHealth?.telegram?.agents ?? [];
  for (const rawAgent of bridgeAgents) {
    const normalized = normalizeTelegramHealthAgent(rawAgent);
    if (normalized) {
      map[normalized.agent_id] = normalized;
    }
  }
  return map;
}

export function resolveTelegramBadge(
  agentId: DashboardAgentId,
  telegramHealth: TelegramHealthPayload | null,
  bridgeAgentMap: Partial<Record<DashboardAgentId, TelegramHealthAgent>>
): TelegramBadge {
  if (!telegramHealth) {
    return { label: "TG -", tone: "muted", code: TELEGRAM_CODES.HEALTH_UNKNOWN };
  }

  const bridge = telegramHealth.telegram;
  const bridgeAgent = bridgeAgentMap[agentId];

  if (!bridge?.bridge_enabled) {
    return { label: "TG OFF", tone: "off", code: String(telegramHealth.code) };
  }
  if (!bridgeAgent) {
    return { label: "TG ?", tone: "warn", code: String(telegramHealth.code) };
  }
  if (!bridgeAgent.token_configured) {
    return { label: "NO TOKEN", tone: "error", code: String(telegramHealth.code) };
  }
  if (bridgeAgent.allow_chat_ids_count < 1) {
    return { label: "NO CHAT", tone: "warn", code: String(telegramHealth.code) };
  }
  if (!bridgeAgent.polling_enabled) {
    return { label: "TG OFF", tone: "off", code: String(telegramHealth.code) };
  }

  switch (telegramHealth.code) {
    case TELEGRAM_CODES.HEALTH_OK:
      return { label: "TG ON", tone: "ok", code: String(telegramHealth.code) };
    case TELEGRAM_CODES.POLLER_STOPPED:
      return { label: "POLLER STOP", tone: "warn", code: String(telegramHealth.code) };
    case TELEGRAM_CODES.NOT_CONFIGURED:
      return { label: "NOT CFG", tone: "warn", code: String(telegramHealth.code) };
    case TELEGRAM_CODES.BRIDGE_DISABLED:
      return { label: "TG OFF", tone: "off", code: String(telegramHealth.code) };
    case TELEGRAM_CODES.NETWORK_ERROR:
    case TELEGRAM_CODES.UNAUTHORIZED:
    case TELEGRAM_CODES.SEND_FAILED:
      return { label: "TG ERR", tone: "error", code: String(telegramHealth.code) };
    default:
      return {
        label: telegramHealth.retryable ? "TG RETRY" : "TG CHECK",
        tone: telegramHealth.retryable ? "warn" : "muted",
        code: String(telegramHealth.code),
      };
  }
}
