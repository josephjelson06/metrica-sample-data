"use client";

import { create } from "zustand";

import type { ConnectionStatus, DataRenderPayload, ServerMessage } from "@/lib/types";

const DEFAULT_QUERY = "Show me the away team's second corner";
const MAX_TRACKING_FRAME = 141156;

type AnalysisStore = {
  status: ConnectionStatus;
  query: string;
  latestPayload: DataRenderPayload | null;
  errorMessage: string | null;
  socket: WebSocket | null;
  isPlaying: boolean;
  playbackStep: number;
  playbackIntervalMs: number;
  setQuery: (query: string) => void;
  connect: () => void;
  disconnect: () => void;
  sendQuery: (query: string) => void;
  requestFrame: (frame: number) => void;
  stepFrameBy: (delta: number) => void;
  setPlaying: (isPlaying: boolean) => void;
  togglePlayback: () => void;
};

function getWebSocketUrl() {
  if (typeof window === "undefined") {
    return "";
  }

  const envUrl = process.env.NEXT_PUBLIC_BACKEND_WS_URL;
  if (envUrl) {
    return envUrl;
  }

  return "ws://127.0.0.1:8000/ws/analysis";
}

export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  status: "idle",
  query: DEFAULT_QUERY,
  latestPayload: null,
  errorMessage: null,
  socket: null,
  isPlaying: false,
  playbackStep: 25,
  playbackIntervalMs: 250,

  setQuery: (query) => set({ query }),

  connect: () => {
    const currentSocket = get().socket;
    if (currentSocket && currentSocket.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = getWebSocketUrl();
    if (!wsUrl) {
      return;
    }

    set({ status: "connecting", errorMessage: null });
    const socket = new WebSocket(wsUrl);

    socket.addEventListener("open", () => {
      set({ status: "connected", socket, errorMessage: null });
    });

    socket.addEventListener("close", () => {
      set((state) => ({
        status: "idle",
        socket: state.socket === socket ? null : state.socket,
      }));
    });

    socket.addEventListener("error", () => {
      set({ status: "error", errorMessage: "WebSocket connection error" });
    });

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data) as ServerMessage;

      if (message.type === "ERROR") {
        set({
          errorMessage: message.payload.message,
          status: "error",
        });
        return;
      }

      set({
        latestPayload: message.payload,
        errorMessage: null,
        status: "connected",
      });
    });

    set({ socket });
  },

  disconnect: () => {
    const currentSocket = get().socket;
    if (currentSocket) {
      currentSocket.close();
    }
    set({ socket: null, status: "idle" });
  },

  sendQuery: (query) => {
    const currentSocket = get().socket;
    if (!currentSocket || currentSocket.readyState !== WebSocket.OPEN) {
      set({ errorMessage: "Backend socket is not connected yet.", status: "error" });
      return;
    }

    currentSocket.send(JSON.stringify({ query }));
    set({ status: "connected", errorMessage: null, query });
  },

  requestFrame: (frame) => {
    const boundedFrame = Math.max(1, Math.min(frame, MAX_TRACKING_FRAME));
    const frameQuery = `Show me the positions at frame ${boundedFrame}`;
    get().sendQuery(frameQuery);
  },

  stepFrameBy: (delta) => {
    const currentFrame = get().latestPayload?.context.frame ?? 1;
    get().requestFrame(currentFrame + delta);
  },

  setPlaying: (isPlaying) => set({ isPlaying }),

  togglePlayback: () => {
    set((state) => ({ isPlaying: !state.isPlaying }));
  },
}));
