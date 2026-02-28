export type DashboardAgentId = "ace" | "owl" | "dolphin";

export type DashboardAgentTheme = {
  main: string;
  glow: string;
  rgb: string;
};

export type DashboardLayout = {
  islandGap: number;
  sideTopBottomGap: number;
  leftPanelWidth: number;
  rightPanelWidth: number;
  centerMinWidth: number;
  compactCenterMinWidth: number;
};

export type DashboardLayoutState = {
  islandGap: number;
  showLeftPanel: boolean;
  showRightPanel: boolean;
  leftPanelWidth: number;
  rightPanelWidth: number;
  centerLeftInset: number;
  centerRightInset: number;
};

export const AGENT_THEME: Record<DashboardAgentId, DashboardAgentTheme> = {
  ace: { main: "#4338CA", glow: "#6366F1", rgb: "99,102,241" },
  owl: { main: "#EA580C", glow: "#F97316", rgb: "249,115,22" },
  dolphin: { main: "#059669", glow: "#10B981", rgb: "16,185,129" },
};

export const STATUS_THEME = {
  busy: "#EAB308",
  idle: "#6B7280",
} as const;

export const DASHBOARD_LAYOUT: DashboardLayout = {
  islandGap: 16,
  sideTopBottomGap: 16,
  leftPanelWidth: 280,
  rightPanelWidth: 320,
  centerMinWidth: 560,
  compactCenterMinWidth: 500,
};

export const CHAT_PANEL_LAYOUT = {
  minHeight: 260,
  defaultHeight: 420,
  collapsedHeight: 62,
  composerMinHeight: 24,
  composerMaxHeight: 200,
  autoExpandPadding: 48,
  autoExpandBlockedMsAfterResize: 700,
} as const;

export function resolveDashboardLayout(viewportWidth: number): DashboardLayoutState {
  const { islandGap, leftPanelWidth, rightPanelWidth, centerMinWidth, compactCenterMinWidth } =
    DASHBOARD_LAYOUT;
  const fullInsetExtra = islandGap * 3;
  const compactInset = islandGap;

  const leftInset = leftPanelWidth + fullInsetExtra;
  const rightInset = rightPanelWidth + fullInsetExtra;
  const canShowBoth = viewportWidth >= leftInset + rightInset + centerMinWidth;
  const canShowLeftOnly = viewportWidth >= leftInset + compactInset + compactCenterMinWidth;

  const showLeftPanel = canShowBoth || canShowLeftOnly;
  const showRightPanel = canShowBoth;

  return {
    islandGap,
    showLeftPanel,
    showRightPanel,
    leftPanelWidth,
    rightPanelWidth,
    centerLeftInset: showLeftPanel ? leftInset : compactInset,
    centerRightInset: showRightPanel ? rightInset : compactInset,
  };
}
