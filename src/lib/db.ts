import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";

export type RoutedMessage = {
  agentId: string;
  message: string;
  payload: string;
};

const DEFAULT_DB_PATH = path.join(process.cwd(), "shared_data", "agent_router.db");

function resolveDbPath() {
  const configured = process.env.SQLITE_PATH?.trim();
  if (!configured) {
    return DEFAULT_DB_PATH;
  }

  return path.isAbsolute(configured) ? configured : path.join(process.cwd(), configured);
}

const dbFilePath = resolveDbPath();
fs.mkdirSync(path.dirname(dbFilePath), { recursive: true });

const db = new Database(dbFilePath);
db.pragma("journal_mode = WAL");
db.exec(`
  CREATE TABLE IF NOT EXISTS routed_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    message TEXT NOT NULL,
    payload TEXT NOT NULL,
    forwarded INTEGER NOT NULL DEFAULT 0,
    forward_status TEXT NOT NULL DEFAULT 'not_attempted',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  )
`);

export function persistRoutedMessage(record: RoutedMessage) {
  const statement = db.prepare(
    `
      INSERT INTO routed_messages (
        agent_id,
        message,
        payload
      ) VALUES (?, ?, ?)
    `
  );

  const result = statement.run(record.agentId, record.message, record.payload);
  return Number(result.lastInsertRowid);
}

export function updateForwardStatus(routeId: number, forwarded: boolean, status: string) {
  const statement = db.prepare(
    `
      UPDATE routed_messages
      SET forwarded = ?, forward_status = ?
      WHERE id = ?
    `
  );

  statement.run(forwarded ? 1 : 0, status, routeId);
}
