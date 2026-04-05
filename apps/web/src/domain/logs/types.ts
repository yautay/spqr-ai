export type LogLevel = "info" | "success" | "warning" | "error";

export interface LogDraftEntry {
  level: LogLevel;
  title: string;
  detail: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  title: string;
  detail: string;
}
