"use client";

import { useEffect, useState } from "react";
import { TELEGRAM_CODES } from "@/lib/telegram-codes";
import type { TelegramHealthPayload } from "./telegram-health";

export function useTelegramHealth(pollIntervalMs = 20000) {
  const [telegramHealth, setTelegramHealth] = useState<TelegramHealthPayload | null>(null);

  useEffect(() => {
    let cancelled = false;

    const pollTelegramHealth = async () => {
      try {
        const response = await fetch("/api/telegram/health", { cache: "no-store" });
        const payload = (await response.json().catch(() => null)) as TelegramHealthPayload | null;

        if (!cancelled && payload && typeof payload.code === "string") {
          setTelegramHealth(payload);
        } else if (!cancelled && !response.ok) {
          setTelegramHealth({
            status: "error",
            code: TELEGRAM_CODES.HEALTH_UNAVAILABLE,
            message: "health_unavailable",
            retryable: true,
          });
        }
      } catch {
        if (!cancelled) {
          setTelegramHealth({
            status: "error",
            code: TELEGRAM_CODES.HEALTH_UNREACHABLE,
            message: "health_unreachable",
            retryable: true,
          });
        }
      }
    };

    void pollTelegramHealth();
    const timer = window.setInterval(() => {
      void pollTelegramHealth();
    }, pollIntervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pollIntervalMs]);

  return telegramHealth;
}
