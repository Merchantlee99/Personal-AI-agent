export type CanonicalAgentId = "ace" | "owl" | "dolphin";

export const AGENT_ALIASES: Record<string, CanonicalAgentId> = {
  ace: "ace",
  "에이스": "ace",
  morpheus: "ace",
  "모르피어스": "ace",
  owl: "owl",
  clio: "owl",
  "클리오": "owl",
  dolphin: "dolphin",
  hermes: "dolphin",
  "헤르메스": "dolphin",
};

export function normalizeAgentIdInput(value: string): CanonicalAgentId | null {
  const raw = value.trim();
  if (!raw) {
    return null;
  }

  const lowered = raw.toLowerCase();
  return AGENT_ALIASES[lowered] ?? AGENT_ALIASES[raw] ?? null;
}
