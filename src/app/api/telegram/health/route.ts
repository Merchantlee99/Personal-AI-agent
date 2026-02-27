import { NextResponse } from "next/server";
import { buildProxyHeaders, fetchWithTimeout, getProxyBaseUrl } from "@/lib/server/proxy-client";
import { TELEGRAM_CODES } from "@/lib/telegram-codes";

const LLM_PROXY_URL = getProxyBaseUrl();

export async function GET() {
  try {
    const upstream = await fetchWithTimeout(`${LLM_PROXY_URL}/api/telegram/health`, {
      method: "GET",
      headers: buildProxyHeaders(),
      cache: "no-store",
    }, 15000);

    const payload = await upstream.json().catch(() => ({
      status: "error",
      code: "TELEGRAM_HEALTH_PARSE_ERROR",
      message: "invalid_json_response",
      retryable: true,
    }));

    if (!upstream.ok) {
      return NextResponse.json(payload, { status: upstream.status });
    }

    return NextResponse.json(payload);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        {
          status: "error",
          code: TELEGRAM_CODES.HEALTH_TIMEOUT,
          message: "upstream_timeout",
          retryable: true,
        },
        { status: 504 }
      );
    }
    return NextResponse.json(
      {
        status: "error",
        code: TELEGRAM_CODES.HEALTH_UNREACHABLE,
        message: "upstream_unreachable",
        retryable: true,
      },
      { status: 502 }
    );
  }
}
