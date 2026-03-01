export type ChatPanelPhase = "closed" | "open" | "resizing";

export type ChatPanelAction =
  | { type: "OPEN" }
  | { type: "CLOSE"; source: "outside" | "escape" | "toggle" }
  | { type: "TOGGLE" }
  | { type: "START_RESIZE" }
  | { type: "END_RESIZE" };

export type ChatPanelTransitionMap = Record<ChatPanelPhase, Partial<Record<ChatPanelAction["type"], ChatPanelPhase>>>;

export const CHAT_PANEL_TRANSITION_MAP: ChatPanelTransitionMap = {
  closed: {
    OPEN: "open",
    TOGGLE: "open",
  },
  open: {
    CLOSE: "closed",
    TOGGLE: "closed",
    START_RESIZE: "resizing",
  },
  resizing: {
    END_RESIZE: "open",
    CLOSE: "open",
    TOGGLE: "open",
  },
};

// Higher value means higher precedence when multiple actions may fire in one interaction.
export const CHAT_PANEL_ACTION_PRIORITY: Record<ChatPanelAction["type"], number> = {
  START_RESIZE: 3,
  END_RESIZE: 3,
  CLOSE: 2,
  OPEN: 2,
  TOGGLE: 1,
};

export type ChatPanelState = {
  phase: ChatPanelPhase;
};

export const INITIAL_CHAT_PANEL_STATE: ChatPanelState = {
  phase: "closed",
};

export function reduceChatPanelState(
  state: ChatPanelState,
  action: ChatPanelAction
): ChatPanelState {
  const nextPhase = CHAT_PANEL_TRANSITION_MAP[state.phase][action.type];
  if (!nextPhase) {
    return state;
  }
  return { phase: nextPhase };
}

export function isChatPanelOpen(state: ChatPanelState): boolean {
  return state.phase !== "closed";
}

export function isChatPanelResizing(state: ChatPanelState): boolean {
  return state.phase === "resizing";
}
