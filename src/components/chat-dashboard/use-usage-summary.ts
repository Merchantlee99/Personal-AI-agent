"use client";

import { useEffect, useState } from "react";

export type UsageProviderId = "anthropic" | "openai" | "gemini";

export type UsageSummaryProvider = {
  provider: UsageProviderId;
  request_count: number;
  error_count: number;
  error_rate: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  settled_cost_usd: number | null;
};

export type UsageSummaryPayload = {
  day_kst: string;
  generated_at: string;
  settled_cost_note: string;
  providers: UsageSummaryProvider[];
};

function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeProvider(candidate: unknown): UsageProviderId | null {
  if (candidate === "anthropic" || candidate === "openai" || candidate === "gemini") {
    return candidate;
  }
  return null;
}

function normalizePayload(candidate: unknown): UsageSummaryPayload | null {
  if (!candidate || typeof candidate !== "object") {
    return null;
  }

  const source = candidate as Record<string, unknown>;
  if (typeof source.day_kst !== "string" || typeof source.generated_at !== "string") {
    return null;
  }

  const rawProviders = Array.isArray(source.providers) ? source.providers : [];
  const providers: UsageSummaryProvider[] = [];

  for (const item of rawProviders) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const row = item as Record<string, unknown>;
    const provider = normalizeProvider(row.provider);
    if (!provider) {
      continue;
    }
    providers.push({
      provider,
      request_count: toNumber(row.request_count, 0),
      error_count: toNumber(row.error_count, 0),
      error_rate: toNumber(row.error_rate, 0),
      input_tokens: toNumber(row.input_tokens, 0),
      output_tokens: toNumber(row.output_tokens, 0),
      total_tokens: toNumber(row.total_tokens, 0),
      estimated_cost_usd: toNumber(row.estimated_cost_usd, 0),
      settled_cost_usd:
        row.settled_cost_usd === null || row.settled_cost_usd === undefined
          ? null
          : toNumber(row.settled_cost_usd, 0),
    });
  }

  return {
    day_kst: source.day_kst,
    generated_at: source.generated_at,
    settled_cost_note: typeof source.settled_cost_note === "string" ? source.settled_cost_note : "",
    providers,
  };
}

export function useUsageSummary(pollIntervalMs = 8000) {
  const [usageSummary, setUsageSummary] = useState<UsageSummaryPayload | null>(null);

  useEffect(() => {
    let cancelled = false;

    const pollUsageSummary = async () => {
      try {
        const response = await fetch("/api/usage/summary", { cache: "no-store" });
        const payload = normalizePayload(await response.json().catch(() => null));
        if (!cancelled && payload) {
          setUsageSummary(payload);
        } else if (!cancelled && !response.ok) {
          setUsageSummary(null);
        }
      } catch {
        if (!cancelled) {
          setUsageSummary(null);
        }
      }
    };

    void pollUsageSummary();
    const timer = window.setInterval(() => {
      void pollUsageSummary();
    }, pollIntervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pollIntervalMs]);

  return usageSummary;
}
