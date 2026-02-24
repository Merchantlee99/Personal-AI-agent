"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type AgentId = "ace" | "owl" | "dolphin";
type AgentStatus = "online" | "busy" | "idle";

type Agent = {
  id: AgentId;
  name: string;
  legacyName: string;
  icon: string;
  color: string;
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
};

type ProviderUsage = {
  provider: "Anthropic" | "OpenAI" | "Gemini";
  dailyBudgetUsd: number;
  usedUsd: number;
  inputTokens: number;
  outputTokens: number;
  errorRate: number;
};

const AGENTS: Agent[] = [
  {
    id: "ace",
    name: "Morpheus",
    legacyName: "에이스",
    icon: "🐙",
    color: "#8B5CF6",
    role: "총괄 조언자",
    model: "claude-opus-4-6",
    status: "online",
    tabooWord: "\"아마\"(근거 없는 추측)",
    reportStyle: "결론 1줄 → 근거 2줄 → 다음 액션 1줄"
  },
  {
    id: "owl",
    name: "Clio",
    legacyName: "지식관리자",
    icon: "🦉",
    color: "#F59E0B",
    role: "지식 체계화",
    model: "claude-sonnet-4-5-20250929",
    status: "online",
    tabooWord: "\"대충\"(비구조화 요약)",
    reportStyle: "요약 3줄 → 구조화 목록 → 연결 노트 1줄"
  },
  {
    id: "dolphin",
    name: "Hermes",
    legacyName: "트렌드트래커",
    icon: "🐬",
    color: "#3B82F6",
    role: "트렌드 조사",
    model: "claude-sonnet-4-5-20250929",
    status: "busy",
    tabooWord: "\"출처 없음\"(검증 없는 인용)",
    reportStyle: "HOT/INSIGHT/MONITOR + 출처 2개 + 추천 액션"
  }
];

const QUICK_PROMPTS: Array<{ label: string; value: string }> = [
  { label: "@morpheus 전략 요약", value: "@ace 현재 상황 기준으로 우선순위 3가지를 요약해줘." },
  { label: "@clio 문서화", value: "@owl 이 대화 내용을 옵시디언 문서 포맷으로 정리해줘." },
  { label: "@hermes 트렌드", value: "@dolphin 2025 한국 관광 트렌드 핵심 이슈 5개만 정리해줘." }
];

const PROVIDER_USAGE: ProviderUsage[] = [
  {
    provider: "Anthropic",
    dailyBudgetUsd: 80,
    usedUsd: 31.4,
    inputTokens: 572340,
    outputTokens: 214987,
    errorRate: 0.8
  },
  {
    provider: "OpenAI",
    dailyBudgetUsd: 60,
    usedUsd: 52.7,
    inputTokens: 420120,
    outputTokens: 191234,
    errorRate: 2.1
  },
  {
    provider: "Gemini",
    dailyBudgetUsd: 50,
    usedUsd: 12.8,
    inputTokens: 132903,
    outputTokens: 50888,
    errorRate: 0.4
  }
];

const STATUS_LABEL: Record<AgentStatus, string> = {
  online: "업무 중",
  busy: "집중",
  idle: "대기"
};

const STATUS_CLASS: Record<AgentStatus, string> = {
  online: "bg-emerald-500",
  busy: "bg-amber-500",
  idle: "bg-stone-400"
};

const INITIAL_HISTORIES: Record<AgentId, ChatMessage[]> = {
  ace: [
    {
      id: "ace-initial",
      role: "assistant",
      content: "Morpheus 연결 완료. 전략/우선순위/실행 플랜을 함께 정리하겠습니다.",
      createdAt: new Date().toISOString()
    }
  ],
  owl: [
    {
      id: "owl-initial",
      role: "assistant",
      content: "Clio 연결 완료. 노트 구조화와 지식 연결을 도와드릴게요.",
      createdAt: new Date().toISOString()
    }
  ],
  dolphin: [
    {
      id: "dolphin-initial",
      role: "assistant",
      content: "Hermes 연결 완료. 최신 트렌드 조사와 정리를 수행합니다.",
      createdAt: new Date().toISOString()
    }
  ]
};

const INITIAL_UNREAD: Record<AgentId, number> = {
  ace: 0,
  owl: 0,
  dolphin: 0
};

function isAgentId(value: string): value is AgentId {
  return AGENTS.some((agent) => agent.id === value);
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
}

function buildApiHistory(history: ChatMessage[]) {
  return history
    .filter((item) => item.role === "user" || item.role === "assistant")
    .map((item) => ({ role: item.role, content: item.content }));
}

function getUsageColor(percentage: number): string {
  if (percentage >= 95) {
    return "bg-red-500";
  }
  if (percentage >= 80) {
    return "bg-amber-500";
  }
  return "bg-emerald-500";
}

function normalizeAssistantContent(content: string): string {
  return content
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function ChatDashboard() {
  const dashboardTitle = process.env.NEXT_PUBLIC_DASHBOARD_TITLE ?? "Nanoclaw Collaborative Agent Console";
  const defaultAgent = process.env.NEXT_PUBLIC_DEFAULT_AGENT_ID ?? "ace";

  const [selectedAgentId, setSelectedAgentId] = useState<AgentId>(
    isAgentId(defaultAgent) ? defaultAgent : "ace"
  );
  const [histories, setHistories] = useState<Record<AgentId, ChatMessage[]>>(INITIAL_HISTORIES);
  const [unreadByAgent, setUnreadByAgent] = useState<Record<AgentId, number>>(INITIAL_UNREAD);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [broadcastMode, setBroadcastMode] = useState(false);
  const [pendingAgents, setPendingAgents] = useState<AgentId[]>([]);

  const endRef = useRef<HTMLDivElement | null>(null);

  const activeAgent = useMemo(
    () => AGENTS.find((agent) => agent.id === selectedAgentId) ?? AGENTS[0],
    [selectedAgentId]
  );
  const activeHistory = histories[selectedAgentId];
  const recentUserPrompts = useMemo(() => {
    return activeHistory
      .filter((message) => message.role === "user")
      .slice(-3)
      .reverse();
  }, [activeHistory]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeHistory.length, isSending]);

  useEffect(() => {
    setUnreadByAgent((prev) => ({ ...prev, [selectedAgentId]: 0 }));
  }, [selectedAgentId]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
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
  }, []);

  const appendAgentMessage = (agentId: AgentId, message: ChatMessage) => {
    setHistories((prev) => ({
      ...prev,
      [agentId]: [...(prev[agentId] ?? []), message]
    }));

    if (agentId !== selectedAgentId && message.role !== "user") {
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
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      createdAt: new Date().toISOString()
    };

    const nextHistory = [...(histories[agentId] ?? []), userMessage];
    setHistories((prev) => ({
      ...prev,
      [agentId]: nextHistory
    }));

    setPendingAgents([agentId]);

    try {
      const content = await requestAgentReply(agentId, message, nextHistory);
      appendAgentMessage(agentId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: normalizeAssistantContent(content),
        createdAt: new Date().toISOString()
      });
    } catch (error) {
      appendAgentMessage(agentId, {
        id: crypto.randomUUID(),
        role: "system",
        content: `오류: ${error instanceof Error ? error.message : "채팅 요청 실패"}`,
        createdAt: new Date().toISOString()
      });
    } finally {
      setPendingAgents([]);
    }
  };

  const sendBroadcast = async (message: string) => {
    const nowIso = new Date().toISOString();

    const userMessagesByAgent: Record<AgentId, ChatMessage> = {
      ace: {
        id: crypto.randomUUID(),
        role: "user",
        content: `[브로드캐스트] ${message}`,
        createdAt: nowIso
      },
      owl: {
        id: crypto.randomUUID(),
        role: "user",
        content: `[브로드캐스트] ${message}`,
        createdAt: nowIso
      },
      dolphin: {
        id: crypto.randomUUID(),
        role: "user",
        content: `[브로드캐스트] ${message}`,
        createdAt: nowIso
      }
    };

    const nextHistories: Record<AgentId, ChatMessage[]> = {
      ace: [...(histories.ace ?? []), userMessagesByAgent.ace],
      owl: [...(histories.owl ?? []), userMessagesByAgent.owl],
      dolphin: [...(histories.dolphin ?? []), userMessagesByAgent.dolphin]
    };

    setHistories(nextHistories);
    setPendingAgents(AGENTS.map((agent) => agent.id));

    const results = await Promise.all(
      AGENTS.map(async (agent) => {
        try {
          const content = await requestAgentReply(agent.id, message, nextHistories[agent.id]);
          return {
            agentId: agent.id,
            message: {
              id: crypto.randomUUID(),
              role: "assistant" as const,
              content: normalizeAssistantContent(content),
              createdAt: new Date().toISOString()
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

    setUnreadByAgent((prev) => {
      const next = { ...prev };
      for (const result of results) {
        if (result.agentId !== selectedAgentId) {
          next[result.agentId] += 1;
        }
      }
      return next;
    });

    setPendingAgents([]);
  };

  async function sendMessage() {
    const message = inputText.trim();
    if (!message || isSending) {
      return;
    }

    setInputText("");
    setIsSending(true);

    try {
      if (broadcastMode) {
        await sendBroadcast(message);
      } else {
        await sendToSingleAgent(message);
      }
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="min-h-screen px-4 pb-28 pt-6 sm:px-6 xl:px-10">
      <main className="mx-auto w-full max-w-[1600px]">
        <div className="mb-4 flex items-center justify-between rounded-xl border border-amber-100 bg-white/80 px-4 py-3">
          <div>
            <h1 className="text-lg font-semibold text-stone-900 sm:text-xl">{dashboardTitle}</h1>
            <p className="text-xs text-stone-500 sm:text-sm">Snapplug 스타일 협업 콘솔 | 단축키: Cmd/Ctrl + 1/2/3</p>
          </div>
          <div className="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700">
            활성 에이전트: {activeAgent.name}
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
          <Card className="h-fit border-stone-200/80 bg-white/90 xl:sticky xl:top-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">AI 팀원</CardTitle>
              <CardDescription>상태/역할 기반으로 빠르게 전환</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {AGENTS.map((agent) => {
                const active = selectedAgentId === agent.id;
                return (
                  <button
                    key={agent.id}
                    type="button"
                    onClick={() => setSelectedAgentId(agent.id)}
                    className={cn(
                      "w-full rounded-xl border px-3 py-3 text-left transition",
                      active ? "bg-white" : "border-stone-200 bg-stone-50 hover:bg-white"
                    )}
                    style={active ? { borderColor: agent.color, boxShadow: `inset 0 0 0 1px ${agent.color}33` } : undefined}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl" aria-hidden="true">
                          {agent.icon}
                        </span>
                        <div>
                          <p className="text-sm font-semibold text-stone-900">{agent.name}</p>
                          <p className="text-xs text-stone-500">{agent.legacyName} · {agent.role}</p>
                        </div>
                      </div>

                      {unreadByAgent[agent.id] > 0 ? (
                        <span className="min-w-5 rounded-full bg-primary px-1.5 py-0.5 text-center text-[11px] font-semibold text-white">
                          {unreadByAgent[agent.id]}
                        </span>
                      ) : null}
                    </div>

                    <div className="mt-2 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <span className={cn("h-2.5 w-2.5 rounded-full", STATUS_CLASS[agent.status])} />
                        <span className="text-stone-600">{STATUS_LABEL[agent.status]}</span>
                      </div>
                      <span className="text-stone-500">{agent.model}</span>
                    </div>
                    <p className="mt-1 truncate text-[11px] text-stone-500">금기어: {agent.tabooWord}</p>
                    <p className="truncate text-[11px] text-stone-500">보고: {agent.reportStyle}</p>
                  </button>
                );
              })}
            </CardContent>
          </Card>

          <Card className="overflow-hidden border-stone-200/80 bg-white/90">
            <CardHeader className="border-b border-stone-100 pb-3">
              <CardTitle className="text-base">협업 채팅</CardTitle>
              <CardDescription>
                {broadcastMode ? "브로드캐스트 모드: 3개 에이전트 동시 질의" : `${activeAgent.name}와 1:1 대화`}
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 p-4">
              <div className="flex flex-wrap gap-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt.label}
                    type="button"
                    onClick={() => setInputText(prompt.value)}
                    className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs text-stone-700 transition hover:bg-stone-100"
                  >
                    {prompt.label}
                  </button>
                ))}

                <button
                  type="button"
                  onClick={() => setBroadcastMode((prev) => !prev)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-semibold transition",
                    broadcastMode
                      ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                      : "border-stone-200 bg-stone-50 text-stone-600 hover:bg-stone-100"
                  )}
                >
                  모두에게 전송 {broadcastMode ? "ON" : "OFF"}
                </button>
              </div>

              <div className="h-[56vh] overflow-y-auto rounded-2xl border border-stone-200 bg-stone-50/80 p-4">
                <div className="space-y-3">
                  {activeHistory.map((message) => (
                    <div key={message.id} className={cn("space-y-1", message.role === "user" && "text-right")}>
                      <div
                        className={cn(
                          "inline-block max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                          "whitespace-pre-wrap",
                          message.role === "user" && "bg-primary text-primary-foreground",
                          message.role === "assistant" && "border border-emerald-100 bg-white text-stone-900",
                          message.role === "system" && "border border-red-200 bg-red-50 text-red-900"
                        )}
                      >
                        {message.content}
                      </div>
                      <p className="text-[11px] text-stone-400">{formatTime(message.createdAt)}</p>
                    </div>
                  ))}

                  {isSending ? (
                    <div className="inline-block max-w-[88%] rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-600">
                      {pendingAgents.length > 1
                        ? `에이전트 ${pendingAgents.length}명 응답 대기 중...`
                        : `${activeAgent.name} 생각 중...`}
                    </div>
                  ) : null}

                  <div ref={endRef} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex gap-2">
                  <Input
                    value={inputText}
                    onChange={(event) => setInputText(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        void sendMessage();
                      }
                    }}
                    placeholder={
                      broadcastMode
                        ? "3개 에이전트에게 동시에 보낼 메시지를 입력하세요..."
                        : `${activeAgent.name}에게 메시지를 입력하세요...`
                    }
                    disabled={isSending}
                  />
                  <Button
                    type="button"
                    onClick={() => void sendMessage()}
                    disabled={isSending || inputText.trim().length === 0}
                    className="min-w-24"
                  >
                    {isSending ? "전송 중" : "전송"}
                  </Button>
                </div>
                <p className="text-xs text-stone-500">Enter 전송 · Shift+Enter 줄바꿈(멀티라인 입력 전환 시) · Cmd/Ctrl+1~3 에이전트 전환</p>
              </div>
            </CardContent>
          </Card>

          <Card className="h-fit border-stone-200/80 bg-white/90 xl:sticky xl:top-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">운영 패널</CardTitle>
              <CardDescription>API 사용량과 보고 규칙</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{activeAgent.icon}</span>
                  <div>
                    <p className="text-sm font-semibold text-stone-900">{activeAgent.name}</p>
                    <p className="text-xs text-stone-500">{activeAgent.role}</p>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-stone-600">
                  <div className="rounded-lg border border-stone-200 bg-white px-2 py-1.5">모델: {activeAgent.model}</div>
                  <div className="rounded-lg border border-stone-200 bg-white px-2 py-1.5">상태: {STATUS_LABEL[activeAgent.status]}</div>
                </div>
                <div className="mt-2 space-y-1 text-[11px] text-stone-600">
                  <p>금기어: {activeAgent.tabooWord}</p>
                  <p>보고 스타일: {activeAgent.reportStyle}</p>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-stone-900">API 할당량</p>
                {PROVIDER_USAGE.map((usage) => {
                  const usagePercent = Math.min(Math.round((usage.usedUsd / usage.dailyBudgetUsd) * 100), 100);
                  const remaining = Math.max(usage.dailyBudgetUsd - usage.usedUsd, 0);
                  const tone = getUsageColor(usagePercent);

                  return (
                    <div key={usage.provider} className="rounded-xl border border-stone-200 bg-white p-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-stone-900">{usage.provider}</span>
                        <span className="text-stone-600">{usagePercent}%</span>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-200">
                        <div className={cn("h-full rounded-full", tone)} style={{ width: `${usagePercent}%` }} />
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-y-1 text-[11px] text-stone-500">
                        <span>남은 예산: ${remaining.toFixed(1)}</span>
                        <span className="text-right">오류율: {usage.errorRate.toFixed(1)}%</span>
                        <span>입력: {usage.inputTokens.toLocaleString()}</span>
                        <span className="text-right">출력: {usage.outputTokens.toLocaleString()}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-stone-900">최근 프롬프트</p>
                {recentUserPrompts.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-stone-300 bg-stone-50 px-3 py-2 text-xs text-stone-500">
                    최근 프롬프트가 없습니다.
                  </div>
                ) : (
                  recentUserPrompts.map((message) => (
                    <button
                      type="button"
                      key={message.id}
                      onClick={() => setInputText(message.content.replace(/^\[브로드캐스트\]\s*/, ""))}
                      className="w-full rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-left text-xs text-stone-600 transition hover:bg-stone-100"
                    >
                      {message.content}
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 px-4 pb-5 sm:px-6 xl:px-10">
        <div className="mx-auto grid w-full max-w-xl grid-cols-3 gap-2 rounded-2xl border border-stone-200 bg-white/95 p-2 shadow-soft backdrop-blur">
          {AGENTS.map((agent) => {
            const isActive = selectedAgentId === agent.id;

            return (
              <button
                key={agent.id}
                type="button"
                className={cn(
                  "rounded-xl border px-3 py-2 text-center transition",
                  isActive
                    ? "bg-white"
                    : "border-transparent bg-stone-100/90 hover:border-stone-300 hover:bg-white"
                )}
                style={isActive ? { borderColor: agent.color, boxShadow: `inset 0 0 0 1px ${agent.color}20` } : undefined}
                onClick={() => setSelectedAgentId(agent.id)}
                aria-label={`${agent.name} 에이전트 선택`}
              >
                <div className="text-2xl">{agent.icon}</div>
                <p className="mt-1 text-xs font-semibold text-stone-800">{agent.name}</p>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
