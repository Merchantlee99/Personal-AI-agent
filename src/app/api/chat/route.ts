import { NextRequest, NextResponse } from "next/server";

const LLM_PROXY_URL = process.env.LLM_PROXY_URL || "http://localhost:8000";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatRequestBody {
  agentId: string;
  message: string;
  history?: ChatMessage[];
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequestBody = await request.json();
    const { agentId, message, history } = body;

    if (!agentId || !message) {
      return NextResponse.json(
        { error: "agentId and message are required" },
        { status: 400 }
      );
    }

    // llm-proxy의 /api/agent 엔드포인트로 전달
    const proxyResponse = await fetch(`${LLM_PROXY_URL}/api/agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: agentId,
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
    const res = await fetch(`${LLM_PROXY_URL}/api/agents`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch agents" },
      { status: 502 }
    );
  }
}
