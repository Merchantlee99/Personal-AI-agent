"use client";

import { type CSSProperties, useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  buildBridgeAgentMap,
  resolveTelegramBadge,
  type TelegramBadge,
} from "@/components/chat-dashboard/telegram-health";
import {
  AGENT_THEME,
  CHAT_PANEL_LAYOUT,
  DASHBOARD_LAYOUT,
  resolveDashboardLayout,
  type DashboardAgentId,
  type DashboardAgentTheme,
} from "@/components/chat-dashboard/design-tokens";
import { DashboardSlot } from "@/components/chat-dashboard/dashboard-slot";
import {
  CHAT_PANEL_ACTION_PRIORITY,
  INITIAL_CHAT_PANEL_STATE,
  isChatPanelOpen,
  isChatPanelResizing,
  reduceChatPanelState,
  type ChatPanelAction,
} from "@/components/chat-dashboard/chat-panel-state";
import { LeftPanel } from "@/components/chat-dashboard/left-panel";
import { RightPanel } from "@/components/chat-dashboard/right-panel";
import { useTelegramHealth } from "@/components/chat-dashboard/use-telegram-health";
import { useUsageSummary, type UsageProviderId } from "@/components/chat-dashboard/use-usage-summary";
import { emitUxMetric } from "@/components/chat-dashboard/ux-metrics";
import { TELEGRAM_CODES } from "@/lib/telegram-codes";
import { cn } from "@/lib/utils";

type AgentId = DashboardAgentId;
type AgentStatus = "online" | "busy" | "idle";
type ReactionState = "neutral" | "thinking" | "warning";

type Agent = {
  id: AgentId;
  name: string;
  legacyName: string;
  role: string;
  model: string;
  status: AgentStatus;
  tabooWord: string;
  reportStyle: string;
};

type ChatMessage = {
  id: string;
  role: "assistant" | "user" | "system";
  content: string;
  createdAt: string;
  origin?: "manual" | "proactive";
};

type AgentUpdate = {
  id: string;
  agentId: AgentId;
  agentName: string;
  title: string;
  content: string;
  type: string;
  source: string;
  createdAt: string;
  ackKey: string;
};

const SEEN_UPDATE_CACHE_LIMIT = 4000;

const AGENTS: Agent[] = [
  {
    id: "ace",
    name: "Morpheus",
    legacyName: "에이스",
    role: "총괄 조언자",
    model: "claude-opus-4-6",
    status: "online",
    tabooWord: "\"아마\"(근거 없는 추측)",
    reportStyle: "결론 1줄 → 근거 2줄 → 다음 액션 1줄",
  },
  {
    id: "owl",
    name: "Clio",
    legacyName: "지식관리자",
    role: "지식 체계화",
    model: "claude-sonnet-4-5-20250929",
    status: "online",
    tabooWord: "\"대충\"(비구조화 요약)",
    reportStyle: "요약 3줄 → 구조화 목록 → 연결 노트 1줄",
  },
  {
    id: "dolphin",
    name: "Hermes",
    legacyName: "트렌드트래커",
    role: "트렌드 조사",
    model: "claude-sonnet-4-5-20250929",
    status: "busy",
    tabooWord: "\"출처 없음\"(검증 없는 인용)",
    reportStyle: "HOT/INSIGHT/MONITOR + 출처 2개 + 추천 액션",
  }
];

const QUICK_PROMPT_BY_AGENT: Record<AgentId, { label: string; value: string }> = {
  ace: { label: "@morpheus 전략 요약", value: "@ace 현재 상황 기준으로 우선순위 3가지를 요약해줘." },
  owl: { label: "@clio 문서화", value: "@owl 이 대화 내용을 옵시디언 문서 포맷으로 정리해줘." },
  dolphin: { label: "@hermes 트렌드", value: "@dolphin 2025 한국 관광 트렌드 핵심 이슈 5개만 정리해줘." }
};

const PARTICLE_PRESETS = [
  { angle: 0, delay: 0.0 },
  { angle: 36, delay: 0.45 },
  { angle: 72, delay: 0.9 },
  { angle: 108, delay: 1.35 },
  { angle: 144, delay: 1.8 },
  { angle: 180, delay: 2.25 },
  { angle: 216, delay: 2.7 },
  { angle: 252, delay: 3.15 },
  { angle: 288, delay: 3.6 },
  { angle: 324, delay: 4.05 }
] as const;

const PROVIDER_PANEL_META = [
  { id: "anthropic", label: "Anthropic", dailyBudgetUsd: 80 },
  { id: "openai", label: "OpenAI", dailyBudgetUsd: 60 },
  { id: "gemini", label: "Gemini", dailyBudgetUsd: 50 },
] as const satisfies Array<{
  id: UsageProviderId;
  label: "Anthropic" | "OpenAI" | "Gemini";
  dailyBudgetUsd: number;
}>;

const INITIAL_CREATED_AT = "2026-02-24T00:00:00.000Z";

const INITIAL_HISTORIES: Record<AgentId, ChatMessage[]> = {
  ace: [
    {
      id: "ace-initial",
      role: "assistant",
      content: "Morpheus 연결 완료. 전략/우선순위/실행 플랜을 함께 정리하겠습니다.",
      createdAt: INITIAL_CREATED_AT,
      origin: "manual"
    }
  ],
  owl: [
    {
      id: "owl-initial",
      role: "assistant",
      content: "Clio 연결 완료. 노트 구조화와 지식 연결을 도와드릴게요.",
      createdAt: INITIAL_CREATED_AT,
      origin: "manual"
    }
  ],
  dolphin: [
    {
      id: "dolphin-initial",
      role: "assistant",
      content: "Hermes 연결 완료. 최신 트렌드 조사와 정리를 수행합니다.",
      createdAt: INITIAL_CREATED_AT,
      origin: "manual"
    }
  ]
};

const INITIAL_UNREAD: Record<AgentId, number> = {
  ace: 0,
  owl: 0,
  dolphin: 0
};

const INITIAL_DRAFTS: Record<AgentId, string> = {
  ace: "",
  owl: "",
  dolphin: "",
};

const INITIAL_RETRY_BY_AGENT: Record<AgentId, string | null> = {
  ace: null,
  owl: null,
  dolphin: null,
};

function isAgentId(value: string): value is AgentId {
  return AGENTS.some((agent) => agent.id === value);
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Seoul"
  });
}

function buildApiHistory(history: ChatMessage[]) {
  return history
    .filter((item) => item.role === "user" || item.role === "assistant")
    .map((item) => ({ role: item.role, content: item.content }));
}

function normalizeAssistantContent(content: string): string {
  return content
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function getReactionState(history: ChatMessage[], pending: boolean): ReactionState {
  if (pending) {
    return "thinking";
  }
  const latestMessage = [...history].reverse().find((message) => message.role !== "user");
  if (latestMessage?.role === "system") {
    return "warning";
  }
  return "neutral";
}

function AgentGlyph({
  agent,
  reaction,
  size = 260,
  compact = false,
}: {
  agent: Agent;
  reaction: ReactionState;
  size?: number;
  compact?: boolean;
}) {
  const visualByAgent: Record<AgentId, {
    rgb: string;
    fill: string;
    glow: string;
    glowSoft: string;
  }> = {
    ace: {
      rgb: "99,102,241",
      fill: "rgba(99, 102, 241, 0.15)",
      glow: "#6366F1",
      glowSoft: "rgba(67, 56, 202, 0.5)",
    },
    owl: {
      rgb: "249,115,22",
      fill: "rgba(249, 115, 22, 0.15)",
      glow: "#F97316",
      glowSoft: "rgba(234, 88, 12, 0.5)",
    },
    dolphin: {
      rgb: "16,185,129",
      fill: "rgba(16, 185, 129, 0.15)",
      glow: "#10B981",
      glowSoft: "rgba(5, 150, 105, 0.5)",
    }
  };
  const visual = visualByAgent[agent.id];

  const reactionClass =
    reaction === "thinking"
      ? "agent-glyph-thinking"
      : reaction === "warning"
        ? "agent-glyph-warning"
        : "agent-glyph-neutral";

  return (
    <div
      className={cn("agent-glyph", reactionClass, compact && "agent-glyph-compact")}
      style={
        {
          width: size,
          height: size,
          "--glyph-size": `${size}px`,
          "--shape-size": compact ? "44px" : "80px",
          "--agent-rgb": visual.rgb,
          "--agent-glow": visual.glow,
          "--agent-glow-soft": visual.glowSoft,
        } as CSSProperties
      }
    >
      <span className="agent-glyph-aura" />
      <span className="agent-glyph-orbit agent-glyph-orbit-outer">
        <span className="agent-glyph-orbit-ring" />
      </span>
      <span className="agent-glyph-orbit agent-glyph-orbit-middle" />
      <span className="agent-glyph-orbit agent-glyph-orbit-inner" />
      <span className="agent-glyph-core-ripple agent-glyph-core-ripple-1" />
      <span className="agent-glyph-core-ripple agent-glyph-core-ripple-2" />
      <span className="agent-glyph-core-ripple agent-glyph-core-ripple-3" />
      <span className="agent-glyph-core-flare" />
      <span className="agent-glyph-particles">
        {PARTICLE_PRESETS.map((particle, idx) => (
          <span
            // eslint-disable-next-line react/no-array-index-key
            key={`${agent.id}-particle-${idx}`}
            className="agent-glyph-particle"
            style={
              {
                "--particle-angle": `${particle.angle}deg`,
                "--particle-delay": `${particle.delay}s`,
                "--particle-color":
                  idx % 2 === 0
                    ? "rgba(255,255,255,0.62)"
                    : `rgba(${visual.rgb},0.72)`,
              } as CSSProperties
            }
          />
        ))}
      </span>
      <span className="agent-glyph-shape">
        {agent.id === "ace" ? (
          <svg viewBox="0 0 100 100" width="80" height="80" aria-hidden="true">
            <polygon points="50,8 88,27 88,73 50,92 12,73 12,27" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" />
            <polygon points="50,22 76,35 76,65 50,78 24,65 24,35" stroke="rgba(255,255,255,0.4)" strokeWidth="1" fill="none" />
            <polygon className="glyph-inner-shape" points="50,35 65,43 65,57 50,65 35,57 35,43" stroke="rgba(255,255,255,0.6)" strokeWidth="1" fill={visual.fill} />
            <line className="glyph-connection-line" style={{ "--line-delay": "0s" } as CSSProperties} x1="50" y1="8" x2="50" y2="35" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "0.3s" } as CSSProperties} x1="88" y1="27" x2="65" y2="43" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "0.6s" } as CSSProperties} x1="88" y1="73" x2="65" y2="57" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "0.9s" } as CSSProperties} x1="50" y1="92" x2="50" y2="65" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "1.2s" } as CSSProperties} x1="12" y1="73" x2="35" y2="57" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "1.5s" } as CSSProperties} x1="12" y1="27" x2="35" y2="43" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <polygon className="glyph-edge-flow" points="50,8 88,27 88,73 50,92 12,73 12,27" stroke={visual.glow} strokeWidth="2" fill="none" />
          </svg>
        ) : null}
        {agent.id === "owl" ? (
          <svg viewBox="0 0 100 100" width="80" height="80" aria-hidden="true">
            <polygon points="50,5 95,50 50,95 5,50" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" />
            <polygon points="50,20 80,50 50,80 20,50" stroke="rgba(255,255,255,0.4)" strokeWidth="1" fill="none" />
            <polygon className="glyph-inner-shape" points="50,33 67,50 50,67 33,50" stroke="rgba(255,255,255,0.6)" strokeWidth="1" fill={visual.fill} />
            <line className="glyph-connection-line" style={{ "--line-delay": "0s" } as CSSProperties} x1="50" y1="5" x2="50" y2="33" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "0.5s" } as CSSProperties} x1="95" y1="50" x2="67" y2="50" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "1s" } as CSSProperties} x1="50" y1="95" x2="50" y2="67" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "1.5s" } as CSSProperties} x1="5" y1="50" x2="33" y2="50" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <polygon className="glyph-edge-flow" points="50,5 95,50 50,95 5,50" stroke={visual.glow} strokeWidth="2" fill="none" />
          </svg>
        ) : null}
        {agent.id === "dolphin" ? (
          <svg viewBox="0 0 100 100" width="80" height="80" aria-hidden="true">
            <polygon points="50,10 88,70 12,70" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" />
            <polygon points="50,24 76,63 24,63" stroke="rgba(255,255,255,0.4)" strokeWidth="1" fill="none" />
            <polygon className="glyph-inner-shape" points="50,36 66,57 34,57" stroke="rgba(255,255,255,0.6)" strokeWidth="1" fill={visual.fill} />
            <line className="glyph-connection-line" style={{ "--line-delay": "0s" } as CSSProperties} x1="50" y1="10" x2="50" y2="36" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "0.4s" } as CSSProperties} x1="88" y1="70" x2="66" y2="57" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "0.8s" } as CSSProperties} x1="12" y1="70" x2="34" y2="57" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "1.2s" } as CSSProperties} x1="50" y1="50" x2="50" y2="36" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "1.6s" } as CSSProperties} x1="50" y1="50" x2="66" y2="57" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
            <line className="glyph-connection-line" style={{ "--line-delay": "2s" } as CSSProperties} x1="50" y1="50" x2="34" y2="57" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
            <polygon className="glyph-edge-flow" points="50,10 88,70 12,70" stroke={visual.glow} strokeWidth="2" fill="none" />
          </svg>
        ) : null}
      </span>
      <span className="agent-glyph-core-glow" />
      <span className="agent-glyph-core-dot" />
    </div>
  );
}

function getCenterStatus(reaction: ReactionState): string {
  if (reaction === "thinking") {
    return "THINKING";
  }
  if (reaction === "warning") {
    return "WARNING";
  }
  return "ONLINE";
}

function CenterAgentSignal({
  agent,
  reaction,
  theme,
}: {
  agent: Agent;
  reaction: ReactionState;
  theme: DashboardAgentTheme;
}) {
  const accent = theme.glow;
  const status = getCenterStatus(reaction);

  return (
    <div className="mx-auto flex w-full max-w-[760px] items-center justify-center">
      <div className="flex min-w-[320px] flex-col items-center gap-4 text-center">
        <div
          className="rounded-full bg-white/[0.06] p-6 transition duration-200"
          style={{
            boxShadow: `0 0 42px -14px ${accent}`
          }}
        >
          <AgentGlyph agent={agent} reaction={reaction} size={260} />
        </div>
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-100">
          {agent.name.toUpperCase()} - {status}
        </p>
      </div>
    </div>
  );
}

export function ChatDashboard() {
  const defaultAgent = process.env.NEXT_PUBLIC_DEFAULT_AGENT_ID ?? "ace";

  const [viewportWidth, setViewportWidth] = useState<number>(1440);
  const [chatPanelState, dispatchChatPanel] = useReducer(
    reduceChatPanelState,
    INITIAL_CHAT_PANEL_STATE
  );
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId>(
    isAgentId(defaultAgent) ? defaultAgent : "ace"
  );
  const [histories, setHistories] = useState<Record<AgentId, ChatMessage[]>>(INITIAL_HISTORIES);
  const [unreadByAgent, setUnreadByAgent] = useState<Record<AgentId, number>>(INITIAL_UNREAD);
  const [draftByAgent, setDraftByAgent] = useState<Record<AgentId, string>>(INITIAL_DRAFTS);
  const [retryByAgent, setRetryByAgent] = useState<Record<AgentId, string | null>>(INITIAL_RETRY_BY_AGENT);
  const [isSending, setIsSending] = useState(false);
  const [pendingAgents, setPendingAgents] = useState<AgentId[]>([]);
  const [isHydrated, setIsHydrated] = useState(false);
  const [chatPanelHeight, setChatPanelHeight] = useState<number>(CHAT_PANEL_LAYOUT.defaultHeight);
  const [isHandleHovered, setIsHandleHovered] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [isSendPressing, setIsSendPressing] = useState(false);
  const telegramHealth = useTelegramHealth();
  const usageSummary = useUsageSummary();

  const endRef = useRef<HTMLDivElement | null>(null);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const seenUpdateIdsRef = useRef<Set<string>>(new Set());
  const seenUpdateOrderRef = useRef<string[]>([]);
  const historiesRef = useRef<Record<AgentId, ChatMessage[]>>(INITIAL_HISTORIES);
  const selectedAgentIdRef = useRef<AgentId>(selectedAgentId);
  const resizeStartYRef = useRef(0);
  const resizeStartHeightRef = useRef<number>(CHAT_PANEL_LAYOUT.defaultHeight);
  const autoExpandBlockedUntilRef = useRef(0);
  const scrollTopByAgentRef = useRef<Record<AgentId, number>>({ ace: 0, owl: 0, dolphin: 0 });
  const stickToBottomByAgentRef = useRef<Record<AgentId, boolean>>({
    ace: true,
    owl: true,
    dolphin: true,
  });
  const lastPanelActionPriorityRef = useRef(0);
  const lastSwitchMetaRef = useRef<{
    from: AgentId;
    to: AgentId;
    at: number;
    measured: boolean;
  } | null>(null);
  const sendStartByAgentRef = useRef<Partial<Record<AgentId, number>>>({});

  const activeAgent = useMemo(
    () => AGENTS.find((agent) => agent.id === selectedAgentId) ?? AGENTS[0],
    [selectedAgentId]
  );
  const reactionByAgent = useMemo(() => {
    return AGENTS.reduce<Record<AgentId, ReactionState>>((acc, agent) => {
      acc[agent.id] = getReactionState(histories[agent.id] ?? [], pendingAgents.includes(agent.id));
      return acc;
    }, {} as Record<AgentId, ReactionState>);
  }, [histories, pendingAgents]);
  const layout = useMemo(() => resolveDashboardLayout(viewportWidth), [viewportWidth]);
  const activeTheme = AGENT_THEME[selectedAgentId];
  const activeThemeCssVars = useMemo(
    () =>
      ({
        "--dashboard-agent-main": activeTheme.main,
        "--dashboard-agent-glow": activeTheme.glow,
        "--dashboard-agent-rgb": activeTheme.rgb,
      } as CSSProperties),
    [activeTheme]
  );
  const chatPanelOpen = isChatPanelOpen(chatPanelState);
  const isResizingChat = isChatPanelResizing(chatPanelState);
  const activeHistory = histories[selectedAgentId] ?? [];
  const inputText = draftByAgent[selectedAgentId] ?? "";
  const telegramBridge = telegramHealth?.telegram;
  const telegramCode = telegramHealth?.code ?? TELEGRAM_CODES.HEALTH_UNKNOWN;
  const telegramBridgeAgentMap = useMemo(
    () => buildBridgeAgentMap(telegramHealth),
    [telegramHealth]
  );
  const telegramBadgeByAgent = useMemo(
    () =>
      AGENTS.reduce<Record<AgentId, TelegramBadge>>((acc, agent) => {
        acc[agent.id] = resolveTelegramBadge(agent.id, telegramHealth, telegramBridgeAgentMap);
        return acc;
      }, {} as Record<AgentId, TelegramBadge>),
    [telegramBridgeAgentMap, telegramHealth]
  );
  const providerUsage = useMemo(() => {
    const summaryByProvider = new Map(
      (usageSummary?.providers ?? []).map((item) => [item.provider, item] as const)
    );
    return PROVIDER_PANEL_META.map((meta) => {
      const row = summaryByProvider.get(meta.id);
      const source: "live" | "fallback" = row ? "live" : "fallback";
      return {
        provider: meta.label,
        dailyBudgetUsd: meta.dailyBudgetUsd,
        estimatedCostUsd: row?.estimated_cost_usd ?? 0,
        settledCostUsd: row?.settled_cost_usd ?? null,
        inputTokens: row?.input_tokens ?? 0,
        outputTokens: row?.output_tokens ?? 0,
        requestCount: row?.request_count ?? 0,
        errorCount: row?.error_count ?? 0,
        errorRate: row?.error_rate ?? 0,
        source,
      };
    });
  }, [usageSummary]);
  const composerMaxHeight = CHAT_PANEL_LAYOUT.composerMaxHeight;
  const enqueueChatPanelAction = useCallback((action: ChatPanelAction) => {
    const priority = CHAT_PANEL_ACTION_PRIORITY[action.type] ?? 0;
    if (priority < lastPanelActionPriorityRef.current) {
      return;
    }
    lastPanelActionPriorityRef.current = priority;
    dispatchChatPanel(action);
    window.requestAnimationFrame(() => {
      lastPanelActionPriorityRef.current = 0;
    });
  }, []);
  const setDraftForAgent = useCallback((agentId: AgentId, text: string) => {
    setDraftByAgent((prev) => ({
      ...prev,
      [agentId]: text,
    }));
  }, []);
  const setSelectedAgentDraft = useCallback((text: string) => {
    setDraftForAgent(selectedAgentId, text);
  }, [selectedAgentId, setDraftForAgent]);
  const markRetryDraft = useCallback((agentId: AgentId, draft: string | null) => {
    setRetryByAgent((prev) => ({
      ...prev,
      [agentId]: draft,
    }));
  }, []);
  const rememberActiveScrollContext = useCallback(() => {
    const scrollEl = chatScrollRef.current;
    if (!scrollEl) {
      return;
    }
    const nearBottom = scrollEl.scrollHeight - (scrollEl.scrollTop + scrollEl.clientHeight) <= 28;
    scrollTopByAgentRef.current[selectedAgentIdRef.current] = scrollEl.scrollTop;
    stickToBottomByAgentRef.current[selectedAgentIdRef.current] = nearBottom;
  }, []);
  const rememberSeenUpdateKey = useCallback((key: string) => {
    if (seenUpdateIdsRef.current.has(key)) {
      return;
    }
    seenUpdateIdsRef.current.add(key);
    seenUpdateOrderRef.current.push(key);

    const overflow = seenUpdateOrderRef.current.length - SEEN_UPDATE_CACHE_LIMIT;
    if (overflow > 0) {
      const staleKeys = seenUpdateOrderRef.current.splice(0, overflow);
      for (const staleKey of staleKeys) {
        seenUpdateIdsRef.current.delete(staleKey);
      }
    }
  }, []);

  useEffect(() => {
    if (!chatPanelOpen) {
      return;
    }
    if (!stickToBottomByAgentRef.current[selectedAgentId]) {
      return;
    }
    endRef.current?.scrollIntoView({ behavior: isSending ? "auto" : "smooth" });
  }, [activeHistory.length, chatPanelOpen, isSending, selectedAgentId]);

  useEffect(() => {
    if (!chatPanelOpen) {
      return;
    }

    const handleOutsidePointerDown = (event: PointerEvent) => {
      if (isResizingChat) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      if (target.closest("[data-chat-panel='conversation']")) {
        return;
      }
      if (target.closest("[data-dashboard-side-panel='left']")) {
        return;
      }
      if (target.closest("[data-dashboard-side-panel='right']")) {
        return;
      }

      emitUxMetric({
        metric: "chat_panel_outside_close",
        agentId: selectedAgentIdRef.current,
        value: 1,
      });
      rememberActiveScrollContext();
      enqueueChatPanelAction({ type: "CLOSE", source: "outside" });
    };

    document.addEventListener("pointerdown", handleOutsidePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handleOutsidePointerDown);
    };
  }, [chatPanelOpen, enqueueChatPanelAction, isResizingChat, rememberActiveScrollContext]);

  useEffect(() => {
    setUnreadByAgent((prev) => ({ ...prev, [selectedAgentId]: 0 }));
  }, [selectedAgentId]);

  useEffect(() => {
    historiesRef.current = histories;
  }, [histories]);

  useEffect(() => {
    const previousAgentId = selectedAgentIdRef.current;
    if (previousAgentId !== selectedAgentId) {
      rememberActiveScrollContext();
      lastSwitchMetaRef.current = {
        from: previousAgentId,
        to: selectedAgentId,
        at: Date.now(),
        measured: false,
      };
    }
    selectedAgentIdRef.current = selectedAgentId;
  }, [rememberActiveScrollContext, selectedAgentId]);

  useEffect(() => {
    if (!chatPanelOpen) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      const scrollEl = chatScrollRef.current;
      if (!scrollEl) {
        return;
      }

      const savedTop = scrollTopByAgentRef.current[selectedAgentId];
      if (savedTop > 0) {
        scrollEl.scrollTop = savedTop;
        return;
      }
      scrollEl.scrollTop = scrollEl.scrollHeight;
    });

    return () => window.cancelAnimationFrame(frame);
  }, [chatPanelOpen, selectedAgentId]);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    const handleWindowResize = () => {
      setViewportWidth(window.innerWidth);
    };
    handleWindowResize();
    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (chatPanelOpen && !isResizingChat) {
          enqueueChatPanelAction({ type: "CLOSE", source: "escape" });
        }
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key === "/") {
        event.preventDefault();
        enqueueChatPanelAction({ type: "TOGGLE" });
        return;
      }

      if (!(event.metaKey || event.ctrlKey)) {
        return;
      }

      const hotkeyMap: Record<string, AgentId> = {
        "1": "ace",
        "2": "owl",
        "3": "dolphin"
      };
      const targetAgent = hotkeyMap[event.key];
      if (!targetAgent) {
        return;
      }

      event.preventDefault();
      setSelectedAgentId(targetAgent);
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [chatPanelOpen, enqueueChatPanelAction, isResizingChat]);

  useEffect(() => {
    let cancelled = false;

    const pollAgentUpdates = async () => {
      try {
        const response = await fetch("/api/agent-updates", { cache: "no-store" });
        if (!response.ok) {
          return;
        }

        const data = (await response.json()) as { notifications?: AgentUpdate[] };
        const incoming = Array.isArray(data.notifications) ? data.notifications : [];
        if (incoming.length === 0 || cancelled) {
          return;
        }

        const validUpdates = incoming.filter((item) => {
          if (!isAgentId(item.agentId)) {
            return false;
          }
          if (!item.content?.trim()) {
            return false;
          }
          if (!item.ackKey?.trim()) {
            return false;
          }
          return true;
        });

        const fresh = validUpdates.filter((item) => {
          const dedupeKey = `${item.ackKey}:${item.id}:${item.createdAt}`;
          if (seenUpdateIdsRef.current.has(item.id)) {
            return false;
          }
          if (seenUpdateIdsRef.current.has(dedupeKey)) {
            return false;
          }
          rememberSeenUpdateKey(item.id);
          rememberSeenUpdateKey(dedupeKey);
          return true;
        });

        if (fresh.length > 0) {
          setHistories((prev) => {
            const next = { ...prev };
            for (const update of fresh) {
              const content = `${update.title}\n\n${update.content}`.trim();
              const message: ChatMessage = {
                id: update.id,
                role: "assistant",
                content: normalizeAssistantContent(content),
                createdAt: update.createdAt || new Date().toISOString(),
                origin: "proactive",
              };
              next[update.agentId] = [...(next[update.agentId] ?? []), message];
            }
            return next;
          });

          setUnreadByAgent((prev) => {
            const next = { ...prev };
            for (const update of fresh) {
              if (update.agentId !== selectedAgentIdRef.current) {
                next[update.agentId] += 1;
              }
            }
            return next;
          });

          enqueueChatPanelAction({ type: "OPEN" });
        }

        const ackKeys = [...new Set(validUpdates.map((item) => item.ackKey))];
        if (ackKeys.length > 0) {
          await fetch("/api/agent-updates", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ackKeys }),
          });
        }
      } catch {
        // Ignore polling failures and retry on next interval.
      }
    };

    void pollAgentUpdates();
    const timer = window.setInterval(() => {
      void pollAgentUpdates();
    }, 15_000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [enqueueChatPanelAction, rememberSeenUpdateKey]);

  const clampChatHeight = useCallback((height: number) => {
    const maxHeight =
      typeof window === "undefined"
        ? 760
        : Math.max(CHAT_PANEL_LAYOUT.minHeight, window.innerHeight - layout.islandGap * 2);
    return Math.min(Math.max(height, CHAT_PANEL_LAYOUT.minHeight), maxHeight);
  }, [layout.islandGap]);

  useEffect(() => {
    setChatPanelHeight((prev) => clampChatHeight(prev));
  }, [clampChatHeight]);

  useEffect(() => {
    if (!isResizingChat) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      const delta = resizeStartYRef.current - event.clientY;
      setChatPanelHeight(clampChatHeight(resizeStartHeightRef.current + delta));
    };

    const handleMouseUp = () => {
      autoExpandBlockedUntilRef.current =
        Date.now() + CHAT_PANEL_LAYOUT.autoExpandBlockedMsAfterResize;
      enqueueChatPanelAction({ type: "END_RESIZE" });
    };

    document.body.style.userSelect = "none";
    document.body.style.cursor = "row-resize";
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.body.style.removeProperty("user-select");
      document.body.style.removeProperty("cursor");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [clampChatHeight, enqueueChatPanelAction, isResizingChat]);

  const ensureChatPanelFitsContent = useCallback(() => {
    if (!chatPanelOpen || isResizingChat) {
      return;
    }
    if (Date.now() < autoExpandBlockedUntilRef.current) {
      return;
    }

    const scrollEl = chatScrollRef.current;
    if (!scrollEl) {
      return;
    }

    const overflow = scrollEl.scrollHeight - scrollEl.clientHeight;
    if (overflow <= 16) {
      return;
    }

    setChatPanelHeight((prev) => {
      const next = clampChatHeight(prev + overflow + CHAT_PANEL_LAYOUT.autoExpandPadding);
      return next > prev ? next : prev;
    });
  }, [chatPanelOpen, clampChatHeight, isResizingChat]);

  useEffect(() => {
    if (!chatPanelOpen) {
      return;
    }

    const frame = window.requestAnimationFrame(ensureChatPanelFitsContent);

    return () => window.cancelAnimationFrame(frame);
  }, [
    activeHistory.length,
    chatPanelOpen,
    ensureChatPanelFitsContent,
    inputText,
    isSending,
    selectedAgentId,
  ]);

  useEffect(() => {
    const composerEl = composerRef.current;
    if (!composerEl) {
      return;
    }

    composerEl.style.height = "auto";
    const nextHeight = Math.min(
      Math.max(composerEl.scrollHeight, CHAT_PANEL_LAYOUT.composerMinHeight),
      composerMaxHeight
    );
    composerEl.style.height = `${nextHeight}px`;
    composerEl.style.overflowY =
      composerEl.scrollHeight > composerMaxHeight ? "auto" : "hidden";
  }, [inputText, selectedAgentId, chatPanelOpen, composerMaxHeight]);

  const startResizeChat = (clientY: number) => {
    resizeStartYRef.current = clientY;
    resizeStartHeightRef.current = chatPanelHeight;
    autoExpandBlockedUntilRef.current =
      Date.now() + CHAT_PANEL_LAYOUT.autoExpandBlockedMsAfterResize;
    enqueueChatPanelAction({ type: "START_RESIZE" });
  };

  const appendAgentMessage = (agentId: AgentId, message: ChatMessage) => {
    setHistories((prev) => ({
      ...prev,
      [agentId]: [...(prev[agentId] ?? []), message]
    }));

    if (agentId !== selectedAgentIdRef.current && message.role !== "user") {
      setUnreadByAgent((prev) => ({
        ...prev,
        [agentId]: prev[agentId] + 1
      }));
    }
  };

  const requestAgentReply = async (agentId: AgentId, message: string, history: ChatMessage[]) => {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agentId,
        message,
        history: buildApiHistory(history)
      })
    });

    const data = (await response.json()) as { content?: string; error?: string };
    if (!response.ok) {
      throw new Error(data.error ?? "Agent call failed");
    }

    return data.content ?? "응답이 비어 있습니다.";
  };

  const sendToSingleAgent = async (message: string) => {
    const agentId = selectedAgentId;
    sendStartByAgentRef.current[agentId] = performance.now();
    const baseHistory = historiesRef.current[agentId] ?? [];
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      createdAt: new Date().toISOString()
    };

    const nextHistory = [...baseHistory, userMessage];
    setHistories((prev) => ({
      ...prev,
      [agentId]: [...(prev[agentId] ?? []), userMessage]
    }));

    setPendingAgents([agentId]);

    try {
      const content = await requestAgentReply(agentId, message, nextHistory);
      appendAgentMessage(agentId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: normalizeAssistantContent(content),
        createdAt: new Date().toISOString(),
        origin: "manual"
      });
      markRetryDraft(agentId, null);
      const startedAt = sendStartByAgentRef.current[agentId];
      if (typeof startedAt === "number") {
        emitUxMetric({
          metric: "chat_send_success_ms",
          agentId,
          value: Math.round(performance.now() - startedAt),
        });
      }
    } catch (error) {
      appendAgentMessage(agentId, {
        id: crypto.randomUUID(),
        role: "system",
        content: `오류: ${error instanceof Error ? error.message : "채팅 요청 실패"}`,
        createdAt: new Date().toISOString()
      });
      markRetryDraft(agentId, message);
    } finally {
      setPendingAgents([]);
    }
  };

  const sendAllQuickPrompts = async () => {
    if (isSending) {
      return;
    }

    enqueueChatPanelAction({ type: "OPEN" });
    stickToBottomByAgentRef.current = { ace: true, owl: true, dolphin: true };
    setIsSending(true);
    try {
      const nowIso = new Date().toISOString();
      const messagesByAgent: Record<AgentId, string> = {
        ace: QUICK_PROMPT_BY_AGENT.ace.value,
        owl: QUICK_PROMPT_BY_AGENT.owl.value,
        dolphin: QUICK_PROMPT_BY_AGENT.dolphin.value,
      };

      const userMessages: Record<AgentId, ChatMessage> = {
        ace: { id: crypto.randomUUID(), role: "user", content: messagesByAgent.ace, createdAt: nowIso },
        owl: { id: crypto.randomUUID(), role: "user", content: messagesByAgent.owl, createdAt: nowIso },
        dolphin: { id: crypto.randomUUID(), role: "user", content: messagesByAgent.dolphin, createdAt: nowIso },
      };
      const requestHistories: Record<AgentId, ChatMessage[]> = {
        ace: [...(historiesRef.current.ace ?? []), userMessages.ace],
        owl: [...(historiesRef.current.owl ?? []), userMessages.owl],
        dolphin: [...(historiesRef.current.dolphin ?? []), userMessages.dolphin],
      };

      setHistories((prev) => ({
        ...prev,
        ace: [...(prev.ace ?? []), userMessages.ace],
        owl: [...(prev.owl ?? []), userMessages.owl],
        dolphin: [...(prev.dolphin ?? []), userMessages.dolphin],
      }));
      sendStartByAgentRef.current = {
        ace: performance.now(),
        owl: performance.now(),
        dolphin: performance.now(),
      };
      setPendingAgents(AGENTS.map((agent) => agent.id));

      const results = await Promise.all(
        AGENTS.map(async (agent) => {
          try {
            const content = await requestAgentReply(
              agent.id,
              messagesByAgent[agent.id],
              requestHistories[agent.id]
            );
            return {
              agentId: agent.id,
              message: {
                id: crypto.randomUUID(),
                role: "assistant" as const,
                content: normalizeAssistantContent(content),
                createdAt: new Date().toISOString(),
                origin: "manual" as const
              }
            };
          } catch (error) {
            return {
              agentId: agent.id,
              message: {
                id: crypto.randomUUID(),
                role: "system" as const,
                content: `오류: ${error instanceof Error ? error.message : "채팅 요청 실패"}`,
                createdAt: new Date().toISOString()
              }
            };
          }
        })
      );

      setHistories((prev) => {
        const next = { ...prev };
        for (const result of results) {
          next[result.agentId] = [...(next[result.agentId] ?? []), result.message];
        }
        return next;
      });

      for (const result of results) {
        if (result.message.role === "assistant") {
          markRetryDraft(result.agentId, null);
          const startedAt = sendStartByAgentRef.current[result.agentId];
          if (typeof startedAt === "number") {
            emitUxMetric({
              metric: "chat_send_success_ms",
              agentId: result.agentId,
              value: Math.round(performance.now() - startedAt),
              meta: { source: "bulk" },
            });
          }
        } else {
          markRetryDraft(result.agentId, messagesByAgent[result.agentId]);
        }
      }

      setUnreadByAgent((prev) => {
        const next = { ...prev };
        for (const result of results) {
          if (result.agentId !== selectedAgentIdRef.current) {
            next[result.agentId] += 1;
          }
        }
        return next;
      });
    } finally {
      setPendingAgents([]);
      setIsSending(false);
    }
  };

  const triggerSendFeedback = () => {
    setIsSendPressing(true);
    window.setTimeout(() => {
      setIsSendPressing(false);
    }, 150);
  };

  async function sendMessage() {
    const message = inputText.trim();
    if (!message || isSending) {
      return;
    }

    stickToBottomByAgentRef.current[selectedAgentId] = true;
    triggerSendFeedback();
    enqueueChatPanelAction({ type: "OPEN" });
    setSelectedAgentDraft("");
    setIsSending(true);

    try {
      await sendToSingleAgent(message);
    } finally {
      setIsSending(false);
    }
  }

  async function retryLastFailedMessage() {
    const retryDraft = retryByAgent[selectedAgentId];
    if (!retryDraft || isSending) {
      return;
    }

    stickToBottomByAgentRef.current[selectedAgentId] = true;
    triggerSendFeedback();
    enqueueChatPanelAction({ type: "OPEN" });
    setIsSending(true);
    try {
      await sendToSingleAgent(retryDraft);
    } finally {
      setIsSending(false);
    }
  }

  async function copyRetryDraft() {
    const retryDraft = retryByAgent[selectedAgentId];
    if (!retryDraft) {
      return;
    }
    try {
      await navigator.clipboard.writeText(retryDraft);
    } catch {
      // Ignore clipboard failure in locked browser contexts.
    }
  }

  return (
    <div
      className="dashboard-theme-shell min-h-screen bg-[#020307] text-stone-100"
      style={activeThemeCssVars}
    >
      <DashboardSlot id="left" label="Left Control Panel">
        {layout.showLeftPanel ? (
          <LeftPanel
            width={layout.leftPanelWidth}
            topBottomGap={DASHBOARD_LAYOUT.sideTopBottomGap}
            islandGap={layout.islandGap}
            activeTheme={activeTheme}
            agentThemeById={AGENT_THEME}
            agents={AGENTS.map((agent) => ({
              id: agent.id,
              name: agent.name,
              legacyName: agent.legacyName,
              role: agent.role,
              status: agent.status,
            }))}
            selectedAgentId={selectedAgentId}
            unreadByAgent={unreadByAgent}
            onSelectAgent={setSelectedAgentId}
          />
        ) : null}
      </DashboardSlot>

      <DashboardSlot id="right" label="Right Insights Panel">
        {layout.showRightPanel ? (
          <RightPanel
            width={layout.rightPanelWidth}
            topBottomGap={DASHBOARD_LAYOUT.sideTopBottomGap}
            islandGap={layout.islandGap}
            activeTheme={activeTheme}
            providerUsage={providerUsage}
            agents={AGENTS.map((agent) => ({ id: agent.id, name: agent.name }))}
            telegramStatus={telegramHealth?.status ?? null}
            telegramCode={telegramCode}
            telegramPollInterval={telegramBridge?.poll_interval_sec ?? null}
            telegramBackgroundRunning={Boolean(telegramBridge?.background_running)}
            telegramBadgeByAgent={telegramBadgeByAgent}
            telegramBridgeAgentMap={telegramBridgeAgentMap}
          />
        ) : null}
      </DashboardSlot>

      <DashboardSlot id="center" className="contents" label="Center Agent Signal">
        <main
        className="relative min-h-screen transition-[padding] duration-500 ease-out"
        style={{ paddingLeft: layout.centerLeftInset, paddingRight: layout.centerRightInset }}
      >
        <div className="flex min-h-screen flex-col">
          <section className="flex flex-1 items-center justify-center px-8 pb-40 pt-10">
            <CenterAgentSignal
              agent={activeAgent}
              reaction={reactionByAgent[activeAgent.id]}
              theme={activeTheme}
            />
          </section>
        </div>

        <DashboardSlot id="chat" className="contents" label="Conversation Panel">
        <div
          data-chat-panel="conversation"
          data-dashboard-slot="chat"
          role="region"
          aria-label="Conversation panel"
          className="fixed z-40 overflow-hidden rounded-[16px] backdrop-blur-[10px] transition-[height,background,border-color,box-shadow] duration-500 ease-out"
          onClick={() => {
            if (!chatPanelOpen) {
              enqueueChatPanelAction({ type: "OPEN" });
            }
          }}
          style={{
            left: layout.centerLeftInset,
            right: layout.centerRightInset,
            bottom: layout.islandGap,
            height: chatPanelOpen ? chatPanelHeight : CHAT_PANEL_LAYOUT.collapsedHeight,
            maxHeight: `calc(100vh - ${layout.islandGap * 2}px)`,
            background:
              "linear-gradient(180deg, rgba(var(--dashboard-agent-rgb), 0.04) 0%, rgba(10, 10, 15, 0.98) 100%)",
            border: "1px solid rgba(var(--dashboard-agent-rgb), 0.12)",
            boxShadow: "0 -4px 30px rgba(var(--dashboard-agent-rgb), 0.05)",
          }}
        >
          <div
            className={cn(
              "absolute inset-x-0 top-0 z-10 h-3",
              chatPanelOpen ? "cursor-row-resize" : "cursor-default"
            )}
            onMouseDown={(event) => {
              if (chatPanelOpen) {
                event.preventDefault();
                startResizeChat(event.clientY);
              }
            }}
            aria-hidden="true"
          />
          <div className="mx-auto flex h-full w-full max-w-[980px] flex-col px-6 py-2">
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                enqueueChatPanelAction({ type: "TOGGLE" });
              }}
              onMouseEnter={() => setIsHandleHovered(true)}
              onMouseLeave={() => setIsHandleHovered(false)}
              className="flex w-full items-center justify-center bg-transparent py-3"
              style={{ border: "none", cursor: "pointer" }}
              aria-label={chatPanelOpen ? "Collapse conversation panel" : "Expand conversation panel"}
              aria-expanded={chatPanelOpen}
              title="Ctrl+/ to toggle, Esc to close"
            >
              <span
                style={{
                  width: isHandleHovered ? "50px" : "40px",
                  height: "4px",
                  borderRadius: "2px",
                  background: isHandleHovered
                    ? "var(--dashboard-agent-glow)"
                    : chatPanelOpen
                      ? "rgba(var(--dashboard-agent-rgb), 0.3)"
                      : "rgba(var(--dashboard-agent-rgb), 0.4)",
                  boxShadow: isHandleHovered
                    ? "0 0 12px rgba(var(--dashboard-agent-rgb), 0.4)"
                    : "none",
                  transform: isHandleHovered
                    ? `translateY(${chatPanelOpen ? 2 : -2}px)`
                    : "translateY(0)",
                  transition:
                    "all var(--dashboard-motion-base, 320ms) var(--dashboard-ease-standard, ease)",
                }}
              />
            </button>

            <div className="flex items-center justify-between gap-2 text-xs">
              <p
                className="text-[11px] uppercase tracking-[0.15em] transition-colors duration-500 ease-out"
                style={{ color: activeTheme.glow, opacity: 0.8 }}
              >
                Conversation
              </p>
            </div>

            <div className={cn("mt-2 min-h-0 flex-1", chatPanelOpen ? "block" : "hidden")}>
              <div className="flex h-full flex-col gap-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      const prompt = QUICK_PROMPT_BY_AGENT[selectedAgentId];
                      setSelectedAgentDraft(prompt.value);
                      enqueueChatPanelAction({ type: "OPEN" });
                    }}
                    className="rounded-xl border px-3 py-1 text-xs transition-all duration-500 ease-out"
                    style={{
                      background: `rgba(${activeTheme.rgb}, 0.15)`,
                      borderColor: `rgba(${activeTheme.rgb}, 0.3)`,
                      color: activeTheme.glow,
                    }}
                  >
                    {QUICK_PROMPT_BY_AGENT[selectedAgentId].label}
                  </button>
                  <button
                    type="button"
                    onClick={() => void sendAllQuickPrompts()}
                    className="rounded-xl border px-3 py-1 text-xs font-semibold transition-all duration-500 ease-out hover:bg-white/[0.08]"
                    style={{
                      background: "rgba(255,255,255,0.04)",
                      borderColor: "rgba(255,255,255,0.08)",
                      color: "#94A3B8",
                    }}
                    disabled={isSending}
                  >
                    모두 요청
                  </button>
                </div>

                <div
                  ref={chatScrollRef}
                  onScroll={rememberActiveScrollContext}
                  className="agent-chat-scroll min-h-0 flex-1 overflow-y-auto pr-1"
                  style={{ "--panel-rgb": activeTheme.rgb } as CSSProperties}
                  role="log"
                  aria-live="polite"
                  aria-relevant="additions text"
                >
                  <div className="space-y-3 pb-2">
                    {activeHistory.map((message) => {
                      if (message.role === "assistant") {
                        return (
                          <div key={message.id} className="space-y-1.5">
                            <div className="min-w-0 max-w-[92%]">
                              <div className="mb-1 flex items-center gap-2">
                                <p className="text-xs font-semibold transition-colors duration-500 ease-out" style={{ color: activeTheme.glow }}>
                                  {activeAgent.name}
                                </p>
                                {message.origin === "proactive" ? (
                                  <span className="rounded-full border border-cyan-300/45 bg-cyan-400/15 px-2 py-0.5 text-[10px] text-cyan-100">
                                    자동 브리핑
                                  </span>
                                ) : null}
                              </div>
                              <div
                                className="rounded-r-[12px] rounded-bl-[12px] px-4 py-3 text-sm leading-relaxed text-stone-100 whitespace-pre-wrap transition-all duration-500 ease-out"
                                style={{
                                  background: "rgba(17, 17, 24, 0.8)",
                                  borderLeft: `2px solid ${activeTheme.glow}`,
                                  boxShadow: `-2px 0 10px rgba(${activeTheme.rgb}, 0.1)`,
                                }}
                              >
                                {message.content}
                              </div>
                            </div>
                            <p className="text-[11px]" style={{ color: "#4B5563" }} suppressHydrationWarning>
                              {isHydrated ? formatTime(message.createdAt) : "--:--"}
                            </p>
                          </div>
                        );
                      }

                      return (
                        <div key={message.id} className={cn("space-y-1.5", message.role === "user" && "text-right")}>
                          <div
                            className={cn(
                              "inline-block max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap",
                              message.role === "user" && "rounded-r-[0] rounded-l-[12px] text-stone-100",
                              message.role === "system" && "bg-rose-500/25 text-rose-100"
                            )}
                            style={
                              message.role === "user"
                                ? {
                                    background: "rgba(30, 30, 46, 0.8)",
                                    borderRight: "2px solid rgba(255,255,255,0.15)",
                                  }
                                : undefined
                            }
                          >
                            {message.content}
                          </div>
                          {message.role === "system" &&
                          retryByAgent[selectedAgentId] &&
                          message.id === activeHistory[activeHistory.length - 1]?.id ? (
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => void retryLastFailedMessage()}
                                className="rounded-md border border-rose-200/30 bg-rose-400/10 px-2 py-1 text-[10px] font-medium text-rose-100 transition hover:bg-rose-400/20"
                                disabled={isSending}
                              >
                                재시도
                              </button>
                              <button
                                type="button"
                                onClick={() => void copyRetryDraft()}
                                className="rounded-md border border-white/20 bg-white/5 px-2 py-1 text-[10px] font-medium text-stone-200 transition hover:bg-white/10"
                              >
                                요청 복사
                              </button>
                            </div>
                          ) : null}
                          <p className="text-[11px]" style={{ color: "#4B5563" }} suppressHydrationWarning>
                            {isHydrated ? formatTime(message.createdAt) : "--:--"}
                          </p>
                        </div>
                      );
                    })}

                    {isSending ? (
                      <div className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-stone-300">
                        {pendingAgents.length > 1
                          ? `에이전트 ${pendingAgents.length}명 응답 대기 중...`
                          : `${activeAgent.name} 생각 중...`}
                      </div>
                    ) : null}

                    <div ref={endRef} />
                  </div>
                </div>

                <div
                  className="flex w-full items-end gap-2 rounded-[14px] p-1 transition-all duration-500 ease-out"
                  style={{
                    background: "rgba(17, 17, 24, 0.6)",
                    border: `1px solid ${isInputFocused ? activeTheme.glow : "rgba(255,255,255,0.08)"}`,
                    boxShadow: isInputFocused ? `0 0 15px rgba(${activeTheme.rgb}, 0.15)` : "none",
                  }}
                >
                  <textarea
                    ref={composerRef}
                    value={inputText}
                    onChange={(event) => {
                      const nextDraft = event.target.value;
                      setSelectedAgentDraft(nextDraft);
                      const switchMeta = lastSwitchMetaRef.current;
                      if (
                        switchMeta &&
                        !switchMeta.measured &&
                        switchMeta.to === selectedAgentId &&
                        nextDraft.trim().length > 0 &&
                        Date.now() - switchMeta.at <= 15_000
                      ) {
                        emitUxMetric({
                          metric: "agent_switch_reinput",
                          agentId: selectedAgentId,
                          value: Date.now() - switchMeta.at,
                          meta: { from: switchMeta.from, to: switchMeta.to },
                        });
                        switchMeta.measured = true;
                      }
                    }}
                    onFocus={() => {
                      enqueueChatPanelAction({ type: "OPEN" });
                      setIsInputFocused(true);
                    }}
                    onBlur={() => setIsInputFocused(false)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        void sendMessage();
                      }
                    }}
                    placeholder={`${activeAgent.name}에게 메시지를 입력하세요...`}
                    disabled={isSending}
                    rows={1}
                    className="w-full bg-transparent px-3 py-2 text-sm leading-relaxed text-stone-100 placeholder:text-[#4B5563] focus-visible:outline-none"
                    style={{
                      minHeight: `${CHAT_PANEL_LAYOUT.composerMinHeight}px`,
                      maxHeight: `${composerMaxHeight}px`,
                      resize: "none",
                      border: "none",
                      outline: "none",
                      color: "#E2E8F0",
                      transition: "color 0.5s ease",
                    }}
                  />
                  <Button
                    type="button"
                    onClick={() => void sendMessage()}
                    disabled={isSending || inputText.trim().length === 0}
                    className="mb-[2px] h-9 w-9 shrink-0 rounded-[10px] p-0 text-white transition-all duration-150 ease-out hover:scale-105 hover:brightness-110"
                    style={{
                      background:
                        isSendPressing
                          ? activeTheme.main
                          : isSending || inputText.trim().length === 0
                          ? `rgba(${activeTheme.rgb}, 0.2)`
                          : `rgba(${activeTheme.rgb}, 0.8)`,
                      border: "none",
                      transform: isSendPressing ? "scale(0.85)" : "scale(1)",
                      boxShadow:
                        isSending || inputText.trim().length === 0 || isSendPressing
                          ? "none"
                          : `0 0 15px rgba(${activeTheme.rgb}, 0.4)`,
                      opacity: isSending || inputText.trim().length === 0 ? 0.5 : 1,
                    }}
                    aria-label="Send message"
                  >
                    {isSending ? (
                      <span className="h-4 w-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                    ) : (
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <path
                          d="M8 13V3M8 3L3 8M8 3L13 8"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </Button>
                </div>

                <p className="mt-[6px] pl-2 text-[11px]" style={{ color: "rgba(255,255,255,0.12)" }}>
                  Enter 전송 · Shift+Enter 줄바꿈 · Ctrl+/ 토글 · Esc 닫기
                </p>
              </div>
            </div>
          </div>
        </div>
        </DashboardSlot>
      </main>
      </DashboardSlot>
    </div>
  );
}
