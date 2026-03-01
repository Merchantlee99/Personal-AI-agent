import { NextRequest, NextResponse } from "next/server";
import { buildProxyHeaders, fetchWithTimeout, getProxyBaseUrl } from "@/lib/server/proxy-client";

const LLM_PROXY_URL = getProxyBaseUrl();

function fallbackPayload() {
  return {
    day_kst: new Date().toISOString().slice(0, 10),
    generated_at: new Date().toISOString(),
    settled_cost_note: "usage_summary_unavailable",
    providers: [],
  };
}

export async function GET(request: NextRequest) {
  try {
    const dayKst = request.nextUrl.searchParams.get("day_kst");
    const query = dayKst ? `?day_kst=${encodeURIComponent(dayKst)}` : "";
    const upstream = await fetchWithTimeout(`${LLM_PROXY_URL}/api/usage/summary${query}`, {
      method: "GET",
      headers: buildProxyHeaders(),
      cache: "no-store",
    }, 10000);

    const payload = await upstream.json().catch(() => fallbackPayload());
    if (!upstream.ok) {
      return NextResponse.json(payload, { status: upstream.status });
    }
    return NextResponse.json(payload);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        {
          ...fallbackPayload(),
          settled_cost_note: "usage_summary_timeout",
        },
        { status: 504 }
      );
    }
    return NextResponse.json(
      {
        ...fallbackPayload(),
        settled_cost_note: "usage_summary_unreachable",
      },
      { status: 502 }
    );
  }
}

