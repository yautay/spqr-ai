/* eslint-disable no-unused-vars */

import type { GameEventPayload } from "@shared-schema/game";

const RECONNECT_DELAY_MS = 1_500;

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;
  const baseUrl = configuredBaseUrl && configuredBaseUrl.length > 0 ? configuredBaseUrl : "http://127.0.0.1:8000";
  return baseUrl.replace(/\/$/, "");
}

function resolveWebSocketUrl(): string {
  const apiBaseUrl = resolveApiBaseUrl();
  if (apiBaseUrl.startsWith("https://")) {
    return `${apiBaseUrl.replace("https://", "wss://")}/game/ws/events`;
  }

  return `${apiBaseUrl.replace("http://", "ws://")}/game/ws/events`;
}

export interface GameEventsSocketHandle {
  close: () => void;
}

export type GameEventsStatus = "connected" | "reconnecting" | "closed";

export function connectGameEventsStream(
  onEvent: (...args: [GameEventPayload]) => void,
  onStatus?: (...args: [GameEventsStatus]) => void,
): GameEventsSocketHandle {
  let socket: WebSocket | null = null;
  let isClosed = false;
  let reconnectTimer: number | null = null;

  const connect = (): void => {
    if (isClosed) {
      return;
    }

    socket = new WebSocket(resolveWebSocketUrl());

    socket.addEventListener("open", () => {
      onStatus?.("connected");
    });

    socket.addEventListener("message", (messageEvent) => {
      try {
        const payload = JSON.parse(String(messageEvent.data)) as GameEventPayload;
        onEvent(payload);
      } catch {
        return;
      }
    });

    socket.addEventListener("close", () => {
      if (isClosed) {
        onStatus?.("closed");
        return;
      }

      onStatus?.("reconnecting");
      reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
    });

    socket.addEventListener("error", () => {
      socket?.close();
    });
  };

  connect();

  return {
    close: () => {
      isClosed = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }

      socket?.close();
      socket = null;
      onStatus?.("closed");
    },
  };
}
