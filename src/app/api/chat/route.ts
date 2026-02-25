import { NextRequest, NextResponse } from "next/server";
import { normalizeAgentIdInput } from "@/lib/agent-config";

const LLM_PROXY_URL = process.env.LLM_PROXY_URL || "http://localhost:8000";
const LLM_PROXY_INTERNAL_TOKEN = process.env.LLM_PROXY_INTERNAL_TOKEN?.trim() || "";
const LLM_PROXY_TIMEOUT_MS = Number(process.env.LLM_PROXY_TIMEOUT_MS || "45000");

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatRequestBody {
  agentId: string;
  message: string;
  history?: ChatMessage[];
}

function normalizeAgentId(agentId: string): "ace" | "owl" | "dolphin" | null {
  return normalizeAgentIdInput(agentId);
}

function buildProxyHeaders() {
  return {
    "Content-Type": "application/json",
    ...(LLM_PROXY_INTERNAL_TOKEN
      ? { "x-internal-token": LLM_PROXY_INTERNAL_TOKEN }
      : {}),
  };
}

async function fetchWithTimeout(input: string, init: RequestInit = {}) {
  const controller = new AbortController();
  const timeout = Number.isFinite(LLM_PROXY_TIMEOUT_MS) && LLM_PROXY_TIMEOUT_MS > 0
    ? LLM_PROXY_TIMEOUT_MS
    : 45000;
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequestBody = await request.json();
    const { agentId, message, history } = body;
    const canonicalAgentId = normalizeAgentId(agentId);

    if (!agentId || !message) {
      return NextResponse.json(
        { error: "agentId and message are required" },
        { status: 400 }
      );
    }
    if (!canonicalAgentId) {
      return NextResponse.json(
        { error: `Unknown agentId: ${agentId}` },
        { status: 400 }
      );
    }

    // llm-proxy의 /api/agent 엔드포인트로 전달
    const proxyResponse = await fetchWithTimeout(`${LLM_PROXY_URL}/api/agent`, {
      method: "POST",
      headers: buildProxyHeaders(),
      body: JSON.stringify({
        agent_id: canonicalAgentId,
        message,
        history: history || [],
      }),
    });

    if (!proxyResponse.ok) {
      const errorData = await proxyResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "Agent call failed" },
        { status: proxyResponse.status }
      );
    }

    const data = await proxyResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        { error: "Agent upstream timeout" },
        { status: 504 }
      );
    }
    console.error("[/api/chat] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// 에이전트 목록 조회
export async function GET() {
  try {
    const res = await fetchWithTimeout(`${LLM_PROXY_URL}/api/agents`, {
      headers: buildProxyHeaders(),
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        { error: "Agent list upstream timeout" },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: "Failed to fetch agents" },
      { status: 502 }
    );
  }
}
