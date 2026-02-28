export type UxMetricName =
  | "chat_send_success_ms"
  | "chat_panel_outside_close"
  | "agent_switch_reinput";

export type UxMetricPayload = {
  metric: UxMetricName;
  agentId?: string;
  value?: number;
  meta?: Record<string, string | number | boolean | null>;
  ts: string;
};

export function emitUxMetric(payload: Omit<UxMetricPayload, "ts">): void {
  if (typeof window === "undefined") {
    return;
  }

  const eventPayload: UxMetricPayload = {
    ...payload,
    ts: new Date().toISOString(),
  };

  window.dispatchEvent(
    new CustomEvent<UxMetricPayload>("dashboard:ux-metric", {
      detail: eventPayload,
    })
  );

  if (process.env.NODE_ENV !== "production") {
    // Keeping lightweight telemetry visible in development speeds UX iteration.
    // eslint-disable-next-line no-console
    console.debug("[ux-metric]", eventPayload);
  }
}
