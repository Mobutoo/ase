import { useEffect, useRef, useCallback } from "react";
import { useAgentStore } from "../stores/agentStore";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;

/**
 * Connects to the agent WebSocket for a circle and auto-reconnects
 * with exponential backoff on disconnection.
 */
export function useAgentWebSocket(circleId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.id) {
        // Update the action in store
        useAgentStore.setState((prev) => ({
          actions: prev.actions.map((a) =>
            a.id === data.id ? { ...a, ...data } : a
          ),
        }));
      }
    } catch {
      // ignore malformed messages
    }
  }, []);

  const connect = useCallback(() => {
    if (!circleId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/circles/${circleId}/agents/`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.addEventListener("open", () => {
      retryRef.current = 0;
    });

    ws.addEventListener("message", handleMessage);

    ws.addEventListener("close", () => {
      wsRef.current = null;
      if (retryRef.current < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * Math.pow(2, retryRef.current) + Math.random() * 500;
        retryRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      }
    });

    ws.addEventListener("error", () => {
      // close event will fire after error, triggering reconnect
    });
  }, [circleId, handleMessage]);

  useEffect(() => {
    connect();

    return () => {
      clearTimeout(timerRef.current);
      retryRef.current = MAX_RETRIES; // prevent reconnect during cleanup
      wsRef.current?.close();
    };
  }, [connect]);
}
