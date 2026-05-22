"use client";

import { startTransition, useDeferredValue, useEffect, useEffectEvent } from "react";

import { PitchCanvas } from "@/components/pitch-canvas";
import { useAnalysisStore } from "@/lib/analysis-store";
import type { SequenceEvent } from "@/lib/types";

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

function formatClockFromFrame(frame: number, framesPerSecond: number) {
  const totalSeconds = Math.max(0, Math.floor(frame / Math.max(framesPerSecond, 1)));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function getSequenceEventColor(event: SequenceEvent) {
  const upperType = event.type.toUpperCase();
  if (upperType === "SHOT") {
    return "#d75b1f";
  }
  if (upperType === "PASS") {
    return "#2f7d45";
  }
  if (upperType === "SET PIECE") {
    return "#1b365c";
  }
  if (upperType === "CARD") {
    return "#b38a15";
  }
  return "#425443";
}

function getSequenceEventLabel(event: SequenceEvent) {
  if (event.subtype) {
    return `${event.type} / ${event.subtype}`;
  }
  return event.type;
}

export function AnalysisWorkspace() {
  const status = useAnalysisStore((state) => state.status);
  const query = useAnalysisStore((state) => state.query);
  const latestPayload = useAnalysisStore((state) => state.latestPayload);
  const errorMessage = useAnalysisStore((state) => state.errorMessage);
  const isPlaying = useAnalysisStore((state) => state.isPlaying);
  const playbackIntervalMs = useAnalysisStore((state) => state.playbackIntervalMs);
  const playbackStep = useAnalysisStore((state) => state.playbackStep);
  const sequenceFrameIndex = useAnalysisStore((state) => state.sequenceFrameIndex);
  const sendQuery = useAnalysisStore((state) => state.sendQuery);
  const requestFrame = useAnalysisStore((state) => state.requestFrame);
  const stepFrameBy = useAnalysisStore((state) => state.stepFrameBy);
  const stepSequenceBy = useAnalysisStore((state) => state.stepSequenceBy);
  const advancePlaybackInStore = useAnalysisStore((state) => state.advancePlayback);
  const setQuery = useAnalysisStore((state) => state.setQuery);
  const togglePlayback = useAnalysisStore((state) => state.togglePlayback);
  const setPlaying = useAnalysisStore((state) => state.setPlaying);

  const activeSequenceFrame = latestPayload?.sequence?.frames[sequenceFrameIndex] ?? null;
  const displayedCoordinates = activeSequenceFrame?.coordinates ?? latestPayload?.data ?? null;
  const displayedFrame = activeSequenceFrame?.frame ?? latestPayload?.context.frame ?? 1;
  const deferredCoordinates = useDeferredValue(displayedCoordinates);
  const eventContext = latestPayload?.context.event;
  const frame = latestPayload?.context.frame;
  const activeFrame = displayedFrame;
  const sequence = latestPayload?.sequence ?? null;
  const hasSequence = Boolean(sequence && sequence.frames.length > 0);
  const replaySequence = hasSequence ? sequence : null;
  const clipProgressPercent = hasSequence && sequence && sequence.frames.length > 1
    ? (sequenceFrameIndex / (sequence.frames.length - 1)) * 100
    : 0;
  const eventProgressPercent = hasSequence && sequence
    ? ((sequence.event_frame - sequence.start_frame) / Math.max(sequence.end_frame - sequence.start_frame, 1)) * 100
    : 0;
  const pitchTransitionMs = hasSequence && sequence
    ? Math.max(20, Math.round(1000 / Math.max(sequence.frames_per_second, 1)))
    : 180;
  const sequenceEvents = replaySequence?.events ?? [];

  useEffect(() => {
    const { connect, disconnect } = useAnalysisStore.getState();
    connect();
    return () => {
      disconnect();
    };
  }, []);

  const advancePlaybackTick = useEffectEvent(() => {
    if (status !== "connected") {
      setPlaying(false);
      return;
    }

    advancePlaybackInStore();
  });

  useEffect(() => {
    if (!isPlaying) {
      return;
    }

    const timer = window.setInterval(() => {
      advancePlaybackTick();
    }, hasSequence ? Math.max(16, Math.round(1000 / (sequence?.frames_per_second ?? 25))) : playbackIntervalMs);

    return () => window.clearInterval(timer);
  }, [advancePlaybackTick, hasSequence, isPlaying, playbackIntervalMs, sequence]);

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
            step={hasSequence ? 1 : 25}
            value={activeFrame}
            onChange={(event) => {
              const nextFrame = Number(event.target.value);
              startTransition(() => requestFrame(nextFrame));
            }}
          />

          {replaySequence ? (
            <div style={{ display: "grid", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "var(--muted)", fontSize: 14 }}>
                <span>Sequence replay</span>
                <span>
                  Clip frame {sequenceFrameIndex + 1} / {replaySequence.frames.length}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={Math.max(replaySequence.frames.length - 1, 0)}
                step={1}
                value={sequenceFrameIndex}
                onChange={(event) => {
                  const nextIndex = Number(event.target.value);
                  startTransition(() => {
                    const delta = nextIndex - sequenceFrameIndex;
                    stepSequenceBy(delta);
                  });
                }}
              />
              <div
                style={{
                  position: "relative",
                  height: 12,
                  borderRadius: 999,
                  overflow: "hidden",
                  background: "rgba(25, 42, 29, 0.12)",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: "linear-gradient(90deg, rgba(35,69,47,0.12), rgba(186,79,23,0.12))",
                  }}
                />
                {sequenceEvents.map((sequenceEvent, index) => {
                  const markerPercent = ((sequenceEvent.frame - replaySequence.start_frame) / Math.max(replaySequence.end_frame - replaySequence.start_frame, 1)) * 100;
                  const isPrimaryEvent = sequenceEvent.frame === replaySequence.event_frame;
                  return (
                    <div
                      key={`${sequenceEvent.frame}-${sequenceEvent.type}-${index}`}
                      title={`${getSequenceEventLabel(sequenceEvent)} at ${formatClockFromFrame(sequenceEvent.frame, replaySequence.frames_per_second)}`}
                      style={{
                        position: "absolute",
                        top: isPrimaryEvent ? -2 : 1,
                        bottom: isPrimaryEvent ? -2 : 1,
                        left: `calc(${Math.max(0, Math.min(markerPercent, 100))}% - 2px)`,
                        width: isPrimaryEvent ? 4 : 3,
                        borderRadius: 999,
                        background: getSequenceEventColor(sequenceEvent),
                        opacity: isPrimaryEvent ? 1 : 0.88,
                      }}
                    />
                  );
                })}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    bottom: 0,
                    left: `${Math.max(0, Math.min(eventProgressPercent, 100))}%`,
                    width: 2,
                    background: "#d75b1f",
                    boxShadow: "0 0 0 3px rgba(215,91,31,0.15)",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: 1,
                    bottom: 1,
                    left: `calc(${Math.max(0, Math.min(clipProgressPercent, 100))}% - 6px)`,
                    width: 12,
                    borderRadius: 999,
                    background: "#21472f",
                    border: "2px solid rgba(255,248,239,0.92)",
                    boxShadow: "0 2px 8px rgba(20,32,19,0.18)",
                  }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "var(--muted)", fontSize: 12 }}>
                <span>
                  Start {formatClockFromFrame(replaySequence.start_frame, replaySequence.frames_per_second)}
                </span>
                <span>
                  Event {formatClockFromFrame(replaySequence.event_frame, replaySequence.frames_per_second)}
                </span>
                <span>
                  End {formatClockFromFrame(replaySequence.end_frame, replaySequence.frames_per_second)}
                </span>
              </div>
              {sequenceEvents.length > 0 ? (
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  {sequenceEvents.slice(0, 8).map((sequenceEvent, index) => (
                    <span
                      key={`${sequenceEvent.frame}-${sequenceEvent.type}-${index}-chip`}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        borderRadius: 999,
                        padding: "5px 10px",
                        background: "rgba(255,255,255,0.78)",
                        border: "1px solid rgba(21,32,23,0.08)",
                        color: "var(--ink)",
                        fontSize: 12,
                      }}
                      title={`${getSequenceEventLabel(sequenceEvent)} at frame ${sequenceEvent.frame}`}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: 999,
                          background: getSequenceEventColor(sequenceEvent),
                          flex: "0 0 auto",
                        }}
                      />
                      {formatClockFromFrame(sequenceEvent.frame, replaySequence.frames_per_second)} {getSequenceEventLabel(sequenceEvent)}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            <button
              type="button"
              onClick={() => {
                if (hasSequence) {
                  stepSequenceBy(-1);
                  return;
                }
                stepFrameBy(-playbackStep);
              }}
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
              {hasSequence ? "Previous Clip Frame" : "Previous Frame"}
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
              {isPlaying ? "Pause Playback" : hasSequence ? "Play Sequence" : "Play Frames"}
            </button>
            <button
              type="button"
              onClick={() => {
                if (hasSequence) {
                  stepSequenceBy(1);
                  return;
                }
                stepFrameBy(playbackStep);
              }}
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
              {hasSequence ? "Next Clip Frame" : "Next Frame"}
            </button>
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, color: "var(--muted)", fontSize: 14 }}>
          <span>Home: cream markers</span>
          <span>Away: orange markers</span>
          <span>Ball: black marker</span>
          <span>Team hulls: shaded shape overlays</span>
          <span>Event arrows: nearby pass and shot directions</span>
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
            {displayedCoordinates ? `${Object.keys(displayedCoordinates).length} tracked entities` : "No frame loaded"}
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
              {` at event frame ${eventContext.frame}`}
              {eventContext.start_time_s != null ? ` (${eventContext.start_time_s.toFixed(2)}s)` : ""}
              {eventContext.from_player ? `, from ${eventContext.from_player}` : ""}
              {hasSequence ? `, replaying around frame ${activeFrame}.` : "."}
              {` Relation: ${eventContext.relation}.`}
              {hasSequence && sequence
                ? ` Clip window: ${formatClockFromFrame(sequence.start_frame, sequence.frames_per_second)} to ${formatClockFromFrame(sequence.end_frame, sequence.frames_per_second)}.`
                : ""}
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

        <PitchCanvas
          coordinates={deferredCoordinates}
          activeFrame={activeFrame}
          sequenceEvents={sequenceEvents}
          framesPerSecond={replaySequence?.frames_per_second ?? 25}
          transitionMs={pitchTransitionMs}
        />
      </section>
    </main>
  );
}
