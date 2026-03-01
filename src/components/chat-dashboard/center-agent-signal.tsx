"use client";

import { type CSSProperties } from "react";

import type { DashboardAgentTheme } from "@/components/chat-dashboard/design-tokens";
import type { Agent, AgentId, ChatMessage, ReactionState } from "@/components/chat-dashboard/types";
import { cn } from "@/lib/utils";

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
  { angle: 324, delay: 4.05 },
] as const;

const VISUAL_BY_AGENT: Record<
  AgentId,
  {
    rgb: string;
    fill: string;
    glow: string;
    glowSoft: string;
  }
> = {
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
  },
};

export function getReactionState(history: ChatMessage[], pending: boolean): ReactionState {
  if (pending) {
    return "thinking";
  }
  const latestMessage = [...history].reverse().find((message) => message.role !== "user");
  if (latestMessage?.role === "system") {
    return "warning";
  }
  return "neutral";
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
  const visual = VISUAL_BY_AGENT[agent.id];
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

export function CenterAgentSignal({
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
            boxShadow: `0 0 42px -14px ${accent}`,
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
