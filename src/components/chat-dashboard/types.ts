import type { DashboardAgentId } from "@/components/chat-dashboard/design-tokens";

export type AgentId = DashboardAgentId;
export type AgentStatus = "online" | "busy" | "idle";
export type ReactionState = "neutral" | "thinking" | "warning";

export type Agent = {
  id: AgentId;
  name: string;
  legacyName: string;
  role: string;
  model: string;
  status: AgentStatus;
  tabooWord: string;
  reportStyle: string;
};

export type ChatMessage = {
  id: string;
  role: "assistant" | "user" | "system";
  content: string;
  createdAt: string;
  origin?: "manual" | "proactive";
};

export type AgentUpdate = {
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
