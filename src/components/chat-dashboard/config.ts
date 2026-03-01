import type { Agent, AgentId, ChatMessage } from "@/components/chat-dashboard/types";

export const SEEN_UPDATE_CACHE_LIMIT = 4000;

export const AGENTS: Agent[] = [
  {
    id: "ace",
    name: "Morpheus",
    legacyName: "에이스",
    role: "총괄 조언자",
    model: "gemini-2.0-flash",
    status: "online",
    tabooWord: "\"아마\"(근거 없는 추측)",
    reportStyle: "결론 1줄 → 근거 2줄 → 다음 액션 1줄",
  },
  {
    id: "owl",
    name: "Clio",
    legacyName: "지식관리자",
    role: "지식 체계화",
    model: "gemini-2.0-flash",
    status: "online",
    tabooWord: "\"대충\"(비구조화 요약)",
    reportStyle: "요약 3줄 → 구조화 목록 → 연결 노트 1줄",
  },
  {
    id: "dolphin",
    name: "Hermes",
    legacyName: "트렌드트래커",
    role: "트렌드 조사",
    model: "gemini-2.0-flash",
    status: "busy",
    tabooWord: "\"출처 없음\"(검증 없는 인용)",
    reportStyle: "HOT/INSIGHT/MONITOR + 출처 2개 + 추천 액션",
  },
];

export const QUICK_PROMPT_BY_AGENT: Record<AgentId, { label: string; value: string }> = {
  ace: {
    label: "@morpheus 전략 요약",
    value: "@ace 현재 상황 기준으로 우선순위 3가지를 요약해줘.",
  },
  owl: {
    label: "@clio 문서화",
    value: "@owl 이 대화 내용을 옵시디언 문서 포맷으로 정리해줘.",
  },
  dolphin: {
    label: "@hermes 트렌드",
    value: "@dolphin 2025 한국 관광 트렌드 핵심 이슈 5개만 정리해줘.",
  },
};

const INITIAL_CREATED_AT = "2026-02-24T00:00:00.000Z";

export const INITIAL_HISTORIES: Record<AgentId, ChatMessage[]> = {
  ace: [
    {
      id: "ace-initial",
      role: "assistant",
      content: "Morpheus 연결 완료. 전략/우선순위/실행 플랜을 함께 정리하겠습니다.",
      createdAt: INITIAL_CREATED_AT,
      origin: "manual",
    },
  ],
  owl: [
    {
      id: "owl-initial",
      role: "assistant",
      content: "Clio 연결 완료. 노트 구조화와 지식 연결을 도와드릴게요.",
      createdAt: INITIAL_CREATED_AT,
      origin: "manual",
    },
  ],
  dolphin: [
    {
      id: "dolphin-initial",
      role: "assistant",
      content: "Hermes 연결 완료. 최신 트렌드 조사와 정리를 수행합니다.",
      createdAt: INITIAL_CREATED_AT,
      origin: "manual",
    },
  ],
};

export const INITIAL_UNREAD: Record<AgentId, number> = {
  ace: 0,
  owl: 0,
  dolphin: 0,
};

export const INITIAL_DRAFTS: Record<AgentId, string> = {
  ace: "",
  owl: "",
  dolphin: "",
};

export const INITIAL_RETRY_BY_AGENT: Record<AgentId, string | null> = {
  ace: null,
  owl: null,
  dolphin: null,
};

export function isAgentId(value: string): value is AgentId {
  return AGENTS.some((agent) => agent.id === value);
}
