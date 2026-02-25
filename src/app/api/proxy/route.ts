import fs from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

import { persistRoutedMessage, updateForwardStatus } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const N8N_INBOX_DIR = path.resolve(process.cwd(), "shared_data", "n8n_inbox");
const LEGACY_ROUTE_NOTICE = "legacy-proxy-route";

type ProxyBody = {
  agentId?: unknown;
  message?: unknown;
  metadata?: unknown;
};

type N8nExtractedResult = {
  finalText: string;
  filename: string;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function extractN8nResult(payload: unknown): N8nExtractedResult | null {
  const candidate = Array.isArray(payload) ? payload[0] : payload;
  if (!candidate || typeof candidate !== "object") {
    return null;
  }

  const asRecord = candidate as Record<string, unknown>;
  if (!isNonEmptyString(asRecord.final_text) || !isNonEmptyString(asRecord.filename)) {
    return null;
  }

  return {
    finalText: asRecord.final_text.trim(),
    filename: asRecord.filename.trim()
  };
}

function sanitizeFilename(filename: string) {
  const basename = path.basename(filename);
  const safe = basename.replace(/[^a-zA-Z0-9._-]/g, "_");
  if (!safe) {
    return null;
  }

  return safe.toLowerCase().endsWith(".txt") ? safe : `${safe}.txt`;
}

function withLegacyHeaders(response: NextResponse) {
  response.headers.set("x-route-status", LEGACY_ROUTE_NOTICE);
  response.headers.set("x-route-replaced-by", "/api/chat");
  return response;
}

export async function POST(request: Request) {
  let body: ProxyBody;

  try {
    body = (await request.json()) as ProxyBody;
  } catch {
    return withLegacyHeaders(NextResponse.json(
      {
        ok: false,
        error: "Invalid JSON payload"
      },
      { status: 400 }
    ));
  }

  if (!isNonEmptyString(body.agentId) || !isNonEmptyString(body.message)) {
    return withLegacyHeaders(NextResponse.json(
      {
        ok: false,
        error: "agentId and message are required"
      },
      { status: 400 }
    ));
  }

  const sanitizedPayload = {
    agentId: body.agentId.trim(),
    message: body.message.trim(),
    metadata: body.metadata ?? null,
    receivedAt: new Date().toISOString()
  };

  const routeId = persistRoutedMessage({
    agentId: sanitizedPayload.agentId,
    message: sanitizedPayload.message,
    payload: JSON.stringify(sanitizedPayload)
  });

  const proxyMode = process.env.PROXY_MODE?.toLowerCase() ?? "store";
  const webhookUrl = (
    process.env.N8N_WEBHOOK_URL_HOST?.trim() ||
    process.env.N8N_WEBHOOK_URL?.trim() ||
    "http://localhost:5678/webhook/hermes-trend"
  );
  const token = process.env.N8N_WEBHOOK_AUTH_TOKEN?.trim();

  let forwarded = false;
  let forwardStatus = "not_attempted";
  let savedFilename: string | null = null;

  if (proxyMode === "forward" && webhookUrl) {
    try {
      const forwardResponse = await fetch(webhookUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          routeId,
          source: "dashboard",
          ...sanitizedPayload
        })
      });

      forwarded = forwardResponse.ok;
      forwardStatus = `http_${forwardResponse.status}`;

      const responseJson = (await forwardResponse.json().catch(() => null)) as unknown;
      const extracted = extractN8nResult(responseJson);

      if (forwardResponse.ok && extracted) {
        const safeFilename = sanitizeFilename(extracted.filename);
        if (!safeFilename) {
          forwardStatus = `${forwardStatus}_invalid_filename`;
        } else {
          try {
            fs.mkdirSync(N8N_INBOX_DIR, { recursive: true });
            const targetPath = path.join(N8N_INBOX_DIR, safeFilename);
            fs.writeFileSync(targetPath, extracted.finalText, "utf8");
            savedFilename = safeFilename;
            forwardStatus = `${forwardStatus}_saved`;
          } catch {
            forwardStatus = `${forwardStatus}_file_write_error`;
          }
        }
      } else if (forwardResponse.ok) {
        forwardStatus = `${forwardStatus}_missing_result`;
      }
    } catch {
      forwarded = false;
      forwardStatus = "network_error";
    }
  }

  updateForwardStatus(routeId, forwarded, forwardStatus);

  return withLegacyHeaders(NextResponse.json({
    ok: true,
    routeId,
    mode: proxyMode,
    forwarded,
    forwardStatus,
    savedFilename
  }));
}
