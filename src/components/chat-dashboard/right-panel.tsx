import { cn } from "@/lib/utils";
import {
  TELEGRAM_BADGE_STYLE,
  type DashboardAgentId,
  type TelegramBadge,
  type TelegramHealthAgent,
} from "@/components/chat-dashboard/telegram-health";

type AgentTheme = {
  glow: string;
  rgb: string;
};

type ProviderUsage = {
  provider: "Anthropic" | "OpenAI" | "Gemini";
  dailyBudgetUsd: number;
  usedUsd: number;
  inputTokens: number;
  outputTokens: number;
  errorRate: number;
};

type PanelAgent = {
  id: DashboardAgentId;
  name: string;
};

type RightPanelProps = {
  width: number;
  topBottomGap: number;
  islandGap: number;
  activeTheme: AgentTheme;
  providerUsage: ProviderUsage[];
  agents: PanelAgent[];
  telegramStatus: "ok" | "error" | null;
  telegramCode: string;
  telegramPollInterval: number | null;
  telegramBackgroundRunning: boolean;
  telegramBadgeByAgent: Record<DashboardAgentId, TelegramBadge>;
  telegramBridgeAgentMap: Partial<Record<DashboardAgentId, TelegramHealthAgent>>;
};

function getUsageColor(percentage: number): string {
  if (percentage >= 95) {
    return "bg-rose-400";
  }
  if (percentage >= 80) {
    return "bg-amber-300";
  }
  return "bg-emerald-300";
}

export function RightPanel({
  width,
  topBottomGap,
  islandGap,
  activeTheme,
  providerUsage,
  agents,
  telegramStatus,
  telegramCode,
  telegramPollInterval,
  telegramBackgroundRunning,
  telegramBadgeByAgent,
  telegramBridgeAgentMap,
}: RightPanelProps) {
  return (
    <aside
      className="fixed z-30 overflow-hidden rounded-[24px] backdrop-blur-xl transition-all duration-500 ease-out"
      style={{
        right: islandGap,
        top: "50%",
        transform: "translateY(-50%)",
        maxHeight: `calc(100vh - ${topBottomGap * 2}px)`,
        width,
        background: `linear-gradient(225deg, rgba(${activeTheme.rgb}, 0.06) 0%, rgba(10, 10, 15, 0.95) 100%)`,
        border: `1px solid rgba(${activeTheme.rgb}, 0.15)`,
        boxShadow: `0 0 20px rgba(${activeTheme.rgb}, 0.05), inset 0 0 20px rgba(${activeTheme.rgb}, 0.03)`,
      }}
    >
      <div className="flex flex-col gap-3 overflow-y-auto p-4">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <p
            className="text-xs uppercase tracking-[0.15em] transition-colors duration-500 ease-out"
            style={{ color: activeTheme.glow, opacity: 0.8 }}
          >
            API Budget
          </p>
          <div className="mt-2 space-y-2">
            {providerUsage.map((usage) => {
              const usagePercent = Math.min(Math.round((usage.usedUsd / usage.dailyBudgetUsd) * 100), 100);
              const remaining = Math.max(usage.dailyBudgetUsd - usage.usedUsd, 0);
              return (
                <div key={usage.provider} className="rounded-lg border border-white/10 bg-black/20 p-2">
                  <div className="flex items-center justify-between text-xs">
                    <span>{usage.provider}</span>
                    <span className="font-semibold" style={{ color: "#E2E8F0" }}>{usagePercent}%</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                    <div className={cn("h-full rounded-full", getUsageColor(usagePercent))} style={{ width: `${usagePercent}%` }} />
                  </div>
                  <div className="mt-1.5 grid grid-cols-2 gap-y-1 text-[11px]" style={{ color: "#64748B" }}>
                    <span>남은: ${remaining.toFixed(1)}</span>
                    <span className="text-right">오류: {usage.errorRate.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <div className="flex items-center justify-between gap-2">
            <p
              className="text-xs uppercase tracking-[0.15em] transition-colors duration-500 ease-out"
              style={{ color: activeTheme.glow, opacity: 0.8 }}
            >
              Telegram Health
            </p>
            <span
              className="shrink-0 rounded-full px-2 py-[1px] text-[10px] font-medium"
              style={TELEGRAM_BADGE_STYLE[telegramStatus === "error" ? "error" : "ok"]}
              title={telegramCode}
            >
              {telegramStatus === "error" ? "ERROR" : "OK"}
            </span>
          </div>

          <div className="mt-2 rounded-lg border border-white/10 bg-black/20 px-2 py-1.5 text-[11px] text-stone-300">
            <div className="flex items-center justify-between gap-2">
              <span className="text-stone-400">code</span>
              <span className="font-mono text-[10px] text-stone-200">{telegramCode}</span>
            </div>
            <div className="mt-1 flex items-center justify-between gap-2">
              <span className="text-stone-400">poll</span>
              <span className="text-stone-200">
                {telegramPollInterval ?? "-"}s · {telegramBackgroundRunning ? "running" : "stopped"}
              </span>
            </div>
          </div>

          <div className="mt-2 space-y-1.5">
            {agents.map((agent) => {
              const badge = telegramBadgeByAgent[agent.id];
              const bridgeAgent = telegramBridgeAgentMap[agent.id];

              return (
                <div
                  key={`tg-health-${agent.id}`}
                  className="flex items-center justify-between gap-2 rounded-md border border-white/10 bg-black/20 px-2 py-1.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-[11px] text-stone-200">{agent.name}</p>
                    <p className="truncate text-[10px] text-stone-500">
                      allowlist {bridgeAgent?.allow_chat_ids_count ?? 0}
                    </p>
                  </div>
                  <span
                    className="shrink-0 rounded-full px-2 py-[1px] text-[10px] font-medium"
                    style={TELEGRAM_BADGE_STYLE[badge.tone]}
                    title={`Telegram: ${badge.code}`}
                  >
                    {badge.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
