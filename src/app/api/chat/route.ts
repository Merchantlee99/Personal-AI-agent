import { NextRequest, NextResponse } from "next/server";
import { normalizeAgentIdInput } from "@/lib/agent-config";
import { buildProxyHeaders, fetchWithTimeout, getProxyBaseUrl } from "@/lib/server/proxy-client";

const LLM_PROXY_URL = getProxyBaseUrl();
const ACE_SHARED_USER_ID = process.env.ACE_SHARED_USER_ID?.trim() || "owner";

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
    const useSharedServerHistory = canonicalAgentId === "ace";
    const proxyResponse = await fetchWithTimeout(`${LLM_PROXY_URL}/api/agent`, {
      method: "POST",
      headers: buildProxyHeaders(),
      body: JSON.stringify({
        agent_id: canonicalAgentId,
        message,
        history: useSharedServerHistory ? [] : history || [],
        ...(useSharedServerHistory
          ? { user_id: ACE_SHARED_USER_ID, channel: "web" }
          : {}),
      }),
    }, 45000);

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
    }, 45000);
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
