"use client";

import { startTransition, useDeferredValue, useEffect, useEffectEvent } from "react";

import { PitchCanvas } from "@/components/pitch-canvas";
import { useAnalysisStore } from "@/lib/analysis-store";

function getStatusLabel(status: ReturnType<typeof useAnalysisStore.getState>["status"]) {
  if (status === "connected") {
    return "Connected";
  }

  if (status === "connecting") {
    return "Connecting";
  }

  if (status === "error") {
    return "Attention needed";
  }

  return "Idle";
}

export function AnalysisWorkspace() {
  const {
    status,
    query,
    latestPayload,
    errorMessage,
    isPlaying,
    playbackIntervalMs,
    playbackStep,
    connect,
    disconnect,
    sendQuery,
    requestFrame,
    stepFrameBy,
    setQuery,
    togglePlayback,
    setPlaying,
  } = useAnalysisStore();

  const connectOnMount = useEffectEvent(() => {
    connect();
  });

  useEffect(() => {
    connectOnMount();
    return () => disconnect();
  }, [connectOnMount, disconnect]);

  const advancePlayback = useEffectEvent(() => {
    if (status !== "connected") {
      setPlaying(false);
      return;
    }

    stepFrameBy(playbackStep);
  });

  useEffect(() => {
    if (!isPlaying) {
      return;
    }

    const timer = window.setInterval(() => {
      advancePlayback();
    }, playbackIntervalMs);

    return () => window.clearInterval(timer);
  }, [advancePlayback, isPlaying, playbackIntervalMs]);

  const deferredPayload = useDeferredValue(latestPayload);
  const eventContext = latestPayload?.context.event;
  const frame = latestPayload?.context.frame;
  const activeFrame = frame ?? 1;

  return (
    <main
      style={{
        width: "min(1280px, calc(100vw - 32px))",
        margin: "24px auto",
        display: "grid",
        gridTemplateColumns: "minmax(320px, 400px) minmax(0, 1fr)",
        gap: "24px",
      }}
    >
      <section
        style={{
          background: "var(--panel)",
          border: "1px solid var(--panel-border)",
          borderRadius: "24px",
          boxShadow: "var(--shadow)",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "18px",
        }}
      >
        <p style={{ margin: 0, letterSpacing: "0.18em", textTransform: "uppercase", fontSize: 12, color: "var(--accent)" }}>
          Next.js Frontend
        </p>
        <h1
          style={{
            margin: 0,
            fontFamily: "var(--font-display), serif",
            fontSize: "clamp(2.3rem, 4vw, 4rem)",
            lineHeight: 0.95,
          }}
        >
          Tactical Cinema Console
        </h1>
        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
          This migrated frontend keeps the live websocket pipeline, but moves the browser side into
          a proper Next.js + TypeScript structure with a dedicated state layer and canvas renderer.
        </p>

        <div
          style={{
            borderRadius: 18,
            background: "rgba(255,255,255,0.65)",
            border: "1px solid rgba(21,32,23,0.08)",
            padding: "14px 16px",
          }}
        >
          <strong>Status:</strong> {getStatusLabel(status)}
          {errorMessage ? (
            <p style={{ margin: "8px 0 0", color: "var(--accent)" }}>{errorMessage}</p>
          ) : null}
        </div>

        <label style={{ display: "flex", flexDirection: "column", gap: 10, fontWeight: 700 }}>
          Natural language query
          <textarea
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              startTransition(() => setQuery(nextQuery));
            }}
            style={{
              minHeight: 124,
              resize: "vertical",
              borderRadius: 18,
              border: "1px solid rgba(20, 32, 19, 0.14)",
              padding: "14px 16px",
              background: "rgba(255,255,255,0.86)",
              color: "var(--ink)",
            }}
          />
        </label>

        <button
          type="button"
          onClick={() => sendQuery(query)}
          disabled={status === "connecting"}
          style={{
            border: 0,
            borderRadius: 999,
            padding: "14px 20px",
            fontWeight: 700,
            color: "#fff8ef",
            background: "linear-gradient(135deg, #a43408, #d75b1f)",
            boxShadow: "0 16px 30px rgba(194,65,12,0.26)",
            cursor: status === "connecting" ? "wait" : "pointer",
          }}
        >
          Render Tactical Snapshot
        </button>

        <div
          style={{
            display: "grid",
            gap: 12,
            borderRadius: 18,
            padding: 16,
            background: "rgba(255,255,255,0.7)",
            border: "1px solid rgba(21,32,23,0.08)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <strong>Frame Controls</strong>
            <span style={{ color: "var(--muted)", fontSize: 14 }}>Current frame: {activeFrame}</span>
          </div>

          <input
            type="range"
            min={1}
            max={141156}
            step={25}
            value={activeFrame}
            onChange={(event) => {
              const nextFrame = Number(event.target.value);
              startTransition(() => requestFrame(nextFrame));
            }}
          />

          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            <button
              type="button"
              onClick={() => stepFrameBy(-playbackStep)}
              style={{
                border: 0,
                borderRadius: 999,
                padding: "10px 16px",
                fontWeight: 700,
                color: "#fff8ef",
                background: "linear-gradient(135deg, #23452f, #34734a)",
                cursor: "pointer",
              }}
            >
              Previous Frame
            </button>
            <button
              type="button"
              onClick={togglePlayback}
              style={{
                border: 0,
                borderRadius: 999,
                padding: "10px 16px",
                fontWeight: 700,
                color: "#fff8ef",
                background: "linear-gradient(135deg, #1b365c, #2c5f9e)",
                cursor: "pointer",
              }}
            >
              {isPlaying ? "Pause Playback" : "Play Frames"}
            </button>
            <button
              type="button"
              onClick={() => stepFrameBy(playbackStep)}
              style={{
                border: 0,
                borderRadius: 999,
                padding: "10px 16px",
                fontWeight: 700,
                color: "#fff8ef",
                background: "linear-gradient(135deg, #23452f, #34734a)",
                cursor: "pointer",
              }}
            >
              Next Frame
            </button>
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, color: "var(--muted)", fontSize: 14 }}>
          <span>Home: cream markers</span>
          <span>Away: orange markers</span>
          <span>Ball: black marker</span>
        </div>

        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
          Try prompts like "Show me the last goal before 70:00", "Show me the away team's second corner",
          or "Show me the first pass after 2:30".
        </p>

        <pre
          style={{
            margin: 0,
            maxHeight: 260,
            overflow: "auto",
            borderRadius: 18,
            padding: 16,
            background: "rgba(20, 32, 19, 0.92)",
            color: "#edf4e5",
            fontSize: 12,
            lineHeight: 1.45,
          }}
        >
          {JSON.stringify(latestPayload, null, 2) || "Waiting for data..."}
        </pre>
      </section>

      <section
        style={{
          background: "var(--panel)",
          border: "1px solid var(--panel-border)",
          borderRadius: "24px",
          boxShadow: "var(--shadow)",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
          <h2 style={{ margin: 0, fontFamily: "var(--font-display), serif", fontSize: "1.55rem" }}>
            Match View
          </h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
            {latestPayload ? `${Object.keys(latestPayload.data).length} tracked entities` : "No frame loaded"}
          </p>
        </div>

        <div
          style={{
            borderRadius: 18,
            padding: "14px 16px",
            background: "rgba(255, 248, 239, 0.92)",
            border: "1px solid rgba(186,79,23,0.14)",
            color: "var(--ink)",
            lineHeight: 1.55,
          }}
        >
          {eventContext ? (
            <>
              <strong>
                {eventContext.team} {eventContext.type}
                {eventContext.subtype ? ` / ${eventContext.subtype}` : ""}
              </strong>
              {` at frame ${eventContext.frame}`}
              {eventContext.start_time_s != null ? ` (${eventContext.start_time_s.toFixed(2)}s)` : ""}
              {eventContext.from_player ? `, from ${eventContext.from_player}` : ""}
              {`. Relation: ${eventContext.relation}.`}
            </>
          ) : frame ? (
            <>
              <strong>Direct frame lookup</strong>
              {` resolved to frame ${frame}.`}
            </>
          ) : (
            "Waiting for your first query."
          )}
        </div>

        <PitchCanvas payload={deferredPayload} />
      </section>
    </main>
  );
}
