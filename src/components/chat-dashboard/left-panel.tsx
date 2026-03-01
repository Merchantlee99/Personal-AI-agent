import type { CSSProperties } from "react";
import type { DashboardAgentId } from "@/components/chat-dashboard/telegram-health";
import { STATUS_THEME, type DashboardAgentTheme } from "@/components/chat-dashboard/design-tokens";

type AgentStatus = "online" | "busy" | "idle";

type LeftPanelAgent = {
  id: DashboardAgentId;
  name: string;
  legacyName: string;
  role: string;
  status: AgentStatus;
};

type LeftPanelProps = {
  width: number;
  topBottomGap: number;
  islandGap: number;
  activeTheme: DashboardAgentTheme;
  agentThemeById: Record<DashboardAgentId, DashboardAgentTheme>;
  agents: LeftPanelAgent[];
  selectedAgentId: DashboardAgentId;
  unreadByAgent: Record<DashboardAgentId, number>;
  onSelectAgent: (agentId: DashboardAgentId) => void;
};

const STATUS_LABEL: Record<AgentStatus, string> = {
  online: "업무 중",
  busy: "집중",
  idle: "대기",
};

export function LeftPanel({
  width,
  topBottomGap,
  islandGap,
  activeTheme,
  agentThemeById,
  agents,
  selectedAgentId,
  unreadByAgent,
  onSelectAgent,
}: LeftPanelProps) {
  return (
    <aside
      data-dashboard-side-panel="left"
      data-dashboard-slot="left"
      role="complementary"
      aria-label="Agent controls"
      className="fixed z-30 overflow-hidden rounded-[24px] backdrop-blur-xl transition-all duration-500 ease-out"
      style={{
        left: islandGap,
        top: "50%",
        transform: "translateY(-50%)",
        maxHeight: `calc(100vh - ${topBottomGap * 2}px)`,
        width,
        background: `linear-gradient(135deg, rgba(${activeTheme.rgb}, 0.06) 0%, rgba(10, 10, 15, 0.95) 100%)`,
        border: `1px solid rgba(${activeTheme.rgb}, 0.15)`,
        boxShadow: `0 0 20px rgba(${activeTheme.rgb}, 0.05), inset 0 0 20px rgba(${activeTheme.rgb}, 0.03)`,
      }}
    >
      <div className="flex flex-col p-4">
        <div className="pb-4">
          <p
            className="text-xs uppercase tracking-[0.15em] transition-colors duration-500 ease-out"
            style={{ color: activeTheme.glow, opacity: 0.8 }}
          >
            System Status
          </p>
          <h2 className="mt-1 text-lg font-semibold text-white">AI Agents</h2>
        </div>

        <div className="space-y-2 pr-1">
          {agents.map((agent) => {
            const active = selectedAgentId === agent.id;
            const agentTheme = agentThemeById[agent.id];
            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => onSelectAgent(agent.id)}
                className="w-full rounded-xl border px-3 py-3 text-left transition-all duration-500 ease-out hover:bg-white/[0.04] hover:border-white/10"
                style={
                  active
                    ? {
                        background: `rgba(${activeTheme.rgb}, 0.1)`,
                        border: `1px solid rgba(${activeTheme.rgb}, 0.3)`,
                        borderLeft: `3px solid ${activeTheme.glow}`,
                        boxShadow: `0 0 15px rgba(${activeTheme.rgb}, 0.1)`,
                      }
                    : {
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid rgba(255,255,255,0.06)",
                        borderLeft: "3px solid transparent",
                      }
                }
              >
                <div className="min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className="truncate text-sm transition-colors duration-500 ease-out"
                      style={{
                        color: active ? "#F1F5F9" : "#94A3B8",
                        fontWeight: active ? 600 : 400,
                      }}
                    >
                      {agent.name}
                    </p>
                    {unreadByAgent[agent.id] > 0 ? (
                      <span
                        className="h-2.5 w-2.5 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.8)] animate-pulse"
                        aria-label={`${agent.name} unread notifications`}
                        title={`${agent.name} unread notifications`}
                      />
                    ) : null}
                  </div>
                  <p className="truncate text-[12px]" style={{ color: "#64748B" }}>
                    {agent.legacyName} · {agent.role}
                  </p>
                  <div className="mt-1.5 flex items-center gap-1.5 text-[11px]">
                    <span
                      className="h-2 w-2 rounded-full transition-all duration-500 ease-out"
                      style={
                        {
                          background:
                            agent.status === "online"
                              ? agentTheme.glow
                              : agent.status === "busy"
                                ? STATUS_THEME.busy
                                : STATUS_THEME.idle,
                          animation: agent.status === "online" ? "statusPulse 2s ease-in-out infinite" : undefined,
                          boxShadow:
                            agent.status === "online"
                              ? `0 0 6px ${agentTheme.glow}`
                              : undefined,
                          "--status-pulse-color": agentTheme.glow,
                        } as CSSProperties
                      }
                    />
                    <span className="text-stone-300">{STATUS_LABEL[agent.status]}</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
