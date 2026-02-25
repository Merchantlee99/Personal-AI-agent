import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

type QueuedNotification = {
  id?: string;
  agent_id?: string;
  agent_name?: string;
  title?: string;
  content?: string;
  type?: string;
  source?: string;
  created_at?: string;
  [key: string]: unknown;
};

type AgentUpdate = {
  id: string;
  agentId: "ace" | "owl" | "dolphin";
  agentName: string;
  title: string;
  content: string;
  type: string;
  source: string;
  createdAt: string;
};

const USER_INBOX_DIR = path.resolve(process.cwd(), "shared_data", "agent_comms", "inbox", "user");
const ARCHIVE_ROOT_DIR = path.resolve(process.cwd(), "shared_data", "agent_comms", "archive", "user");
const DEADLETTER_DIR = path.resolve(process.cwd(), "shared_data", "agent_comms", "deadletter");

const AGENT_ALIASES: Record<string, "ace" | "owl" | "dolphin"> = {
  ace: "ace",
  "에이스": "ace",
  morpheus: "ace",
  "모르피어스": "ace",
  owl: "owl",
  clio: "owl",
  "클리오": "owl",
  dolphin: "dolphin",
  hermes: "dolphin",
  "헤르메스": "dolphin",
};

function normalizeAgentId(raw: string | undefined): "ace" | "owl" | "dolphin" {
  const normalized = (raw ?? "").trim().toLowerCase();
  return AGENT_ALIASES[normalized] ?? "dolphin";
}

function uniquePath(targetPath: string): Promise<string> {
  return fs
    .access(targetPath)
    .then(() => {
      const ext = path.extname(targetPath);
      const base = targetPath.slice(0, targetPath.length - ext.length);
      return `${base}_${Date.now()}${ext}`;
    })
    .catch(() => targetPath);
}

async function moveToArchive(filePath: string) {
  const datePart = new Date().toISOString().slice(0, 10).replaceAll("-", "");
  const archiveDir = path.join(ARCHIVE_ROOT_DIR, datePart);
  await fs.mkdir(archiveDir, { recursive: true });
  const destination = await uniquePath(path.join(archiveDir, path.basename(filePath)));
  await fs.rename(filePath, destination);
}

async function moveToDeadletter(filePath: string) {
  await fs.mkdir(DEADLETTER_DIR, { recursive: true });
  const destination = await uniquePath(path.join(DEADLETTER_DIR, path.basename(filePath)));
  await fs.rename(filePath, destination);
}

async function parseNotification(filePath: string): Promise<AgentUpdate | null> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    const parsed = JSON.parse(raw) as QueuedNotification;
    const agentId = normalizeAgentId(parsed.agent_id);
    const agentName = String(parsed.agent_name || (agentId === "dolphin" ? "Hermes" : agentId));
    const content = String(parsed.content || "").trim();
    if (!content) {
      return null;
    }

    return {
      id: String(parsed.id || path.basename(filePath, ".json")),
      agentId,
      agentName,
      title: String(parsed.title || "Hermes 자동 브리핑"),
      content,
      type: String(parsed.type || "daily_briefing"),
      source: String(parsed.source || "n8n_schedule"),
      createdAt: String(parsed.created_at || new Date().toISOString()),
    };
  } catch {
    return null;
  }
}

export async function GET() {
  try {
    await fs.mkdir(USER_INBOX_DIR, { recursive: true });
    const fileNames = (await fs.readdir(USER_INBOX_DIR))
      .filter((name) => name.endsWith(".json"))
      .sort();

    const notifications: AgentUpdate[] = [];

    for (const fileName of fileNames) {
      const filePath = path.join(USER_INBOX_DIR, fileName);
      const parsed = await parseNotification(filePath);

      if (!parsed) {
        await moveToDeadletter(filePath);
        continue;
      }

      notifications.push(parsed);
      await moveToArchive(filePath);
    }

    return NextResponse.json({ notifications });
  } catch (error) {
    console.error("[/api/agent-updates] error", error);
    return NextResponse.json({ error: "Failed to fetch agent updates" }, { status: 500 });
  }
}
