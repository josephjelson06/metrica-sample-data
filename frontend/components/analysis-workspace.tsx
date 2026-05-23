"use client";

import { startTransition, useDeferredValue, useEffect, useEffectEvent, useState } from "react";

import { PitchCanvas } from "@/components/pitch-canvas";
import { useAnalysisStore } from "@/lib/analysis-store";
import type {
  AggregateContext,
  AnalysisContext,
  ComparisonContext,
  CoordinateMap,
  MetricMap,
  SequenceEvent,
  SequenceSegments,
  TrackingSequence,
} from "@/lib/types";

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

function formatMatchTime(seconds: number | null | undefined) {
  if (seconds == null) {
    return "unknown";
  }

  const totalSeconds = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function formatMetricLabel(metricKey: string) {
  return metricKey
    .replace(/_/g, " ")
    .replace(/\bproxy\b/gi, "proxy")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatMetricValue(metricValue: unknown) {
  if (typeof metricValue === "number") {
    return metricValue.toFixed(3);
  }
  if (typeof metricValue === "string") {
    return metricValue;
  }
  if (metricValue == null) {
    return "n/a";
  }
  return JSON.stringify(metricValue);
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

function getEventDisplayLabel(event: AnalysisContext["event"] | ComparisonContext["left_event"]) {
  if (!event) {
    return "Unknown event";
  }

  return event.subtype ? `${event.type} / ${event.subtype}` : event.type;
}

function cardStyle() {
  return {
    borderRadius: 18,
    padding: "16px 18px",
    background: "rgba(255,255,255,0.72)",
    border: "1px solid rgba(21,32,23,0.08)",
  } as const;
}

function sectionTitleStyle() {
  return {
    margin: 0,
    fontSize: "1rem",
    letterSpacing: "0.03em",
  } as const;
}

function actionButtonStyle() {
  return {
    border: "1px solid rgba(21,32,23,0.1)",
    borderRadius: 999,
    padding: "8px 12px",
    background: "rgba(255,255,255,0.86)",
    color: "var(--ink)",
    fontWeight: 700,
    cursor: "pointer",
  } as const;
}

function getPrimaryResultTitle(context: AnalysisContext | null) {
  if (!context) {
    return "Waiting For Analysis";
  }

  switch (context.mode) {
    case "aggregate":
      return "Aggregate View";
    case "comparison":
      return "Comparison View";
    case "buildup":
      return "Buildup View";
    case "transition":
      return "Transition View";
    case "sequence_event":
      return "Sequence Event View";
    case "frame":
      return "Frame View";
    case "event":
    default:
      return "Match View";
  }
}

function flattenMetricMap(metrics: MetricMap | null | undefined, prefix = ""): Array<{ label: string; value: string }> {
  if (!metrics) {
    return [];
  }

  const entries: Array<{ label: string; value: string }> = [];
  for (const [metricKey, metricValue] of Object.entries(metrics)) {
    if (
      metricKey === "requested_metric" ||
      metricKey === "team" ||
      metricKey === "frame"
    ) {
      continue;
    }

    const nextLabel = prefix ? `${prefix} ${formatMetricLabel(metricKey)}` : formatMetricLabel(metricKey);
    if (
      metricValue &&
      typeof metricValue === "object" &&
      !Array.isArray(metricValue)
    ) {
      entries.push(...flattenMetricMap(metricValue as MetricMap, nextLabel));
      continue;
    }

    entries.push({
      label: nextLabel,
      value: formatMetricValue(metricValue),
    });
  }
  return entries;
}

function renderMetricGrid(metrics: MetricMap | null | undefined) {
  const metricEntries = flattenMetricMap(metrics);
  if (metricEntries.length === 0) {
    return null;
  }

  return (
    <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
      {metricEntries.slice(0, 12).map((metric) => (
        <div key={metric.label} style={cardStyle()}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            {metric.label}
          </p>
          <strong style={{ fontSize: "1.05rem" }}>{metric.value}</strong>
        </div>
      ))}
    </div>
  );
}

function renderSequenceChips(sequenceEvents: SequenceEvent[], framesPerSecond: number) {
  if (sequenceEvents.length === 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {sequenceEvents.slice(0, 10).map((sequenceEvent, index) => (
        <span
          key={`${sequenceEvent.frame}-${sequenceEvent.type}-${index}-chip-display`}
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
          {formatClockFromFrame(sequenceEvent.frame, framesPerSecond)} {getSequenceEventLabel(sequenceEvent)}
        </span>
      ))}
    </div>
  );
}

function renderAggregatePanel(
  aggregate: AggregateContext | null | undefined,
  onOpenEventFrame: ((frame: number) => void) | null,
) {
  if (!aggregate) {
    return null;
  }

  const filterTokens = Object.entries(aggregate.filters)
    .filter(([, value]) => value != null && value !== "")
    .map(([filterKey, value]) => `${formatMetricLabel(filterKey)}: ${String(value).replace(/_/g, " ")}`);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={cardStyle()}>
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Aggregate Result
        </p>
        <h3 style={{ margin: "6px 0 8px", fontSize: "1.3rem" }}>
          {aggregate.query_type === "count" ? `${aggregate.count} matches` : `${aggregate.count} listed events`}
        </h3>
        {filterTokens.length > 0 ? (
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.5 }}>{filterTokens.join(" | ")}</p>
        ) : null}
      </div>

      {aggregate.query_type === "list" && aggregate.events && aggregate.events.length > 0 ? (
        <div style={{ ...cardStyle(), padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "16px 18px", borderBottom: "1px solid rgba(21,32,23,0.08)" }}>
            <h3 style={sectionTitleStyle()}>Matching Events</h3>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--muted)" }}>
                  <th style={{ padding: "12px 18px" }}>Time</th>
                  <th style={{ padding: "12px 18px" }}>Team</th>
                  <th style={{ padding: "12px 18px" }}>Type</th>
                  <th style={{ padding: "12px 18px" }}>Subtype</th>
                  <th style={{ padding: "12px 18px" }}>Frame</th>
                  <th style={{ padding: "12px 18px" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {aggregate.events.slice(0, 12).map((event, index) => (
                  <tr key={`${event.frame}-${event.type}-${index}`} style={{ borderTop: "1px solid rgba(21,32,23,0.06)" }}>
                    <td style={{ padding: "12px 18px" }}>{formatMatchTime(event.start_time_s)}</td>
                    <td style={{ padding: "12px 18px" }}>{event.team ?? "Unknown"}</td>
                    <td style={{ padding: "12px 18px" }}>{event.type}</td>
                    <td style={{ padding: "12px 18px" }}>{event.subtype ?? "-"}</td>
                    <td style={{ padding: "12px 18px" }}>{event.frame}</td>
                    <td style={{ padding: "12px 18px" }}>
                      {onOpenEventFrame ? (
                        <button
                          type="button"
                          onClick={() => onOpenEventFrame(event.frame)}
                          style={actionButtonStyle()}
                        >
                          Open frame
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function renderSequenceSegmentsPanel(sequenceSegments: SequenceSegments | null | undefined, title: string) {
  if (!sequenceSegments) {
    return null;
  }

  const countRows = [
    ["Before events", sequenceSegments.before_events_count],
    ["Anchor events", sequenceSegments.anchor_events_count],
    ["After events", sequenceSegments.after_events_count],
    ["Same-team before", sequenceSegments.same_team_before_count],
    ["Same-team after", sequenceSegments.same_team_after_count],
    ["Opponent before", sequenceSegments.opponent_before_count],
    ["Opponent after", sequenceSegments.opponent_after_count],
    ["Continuation before opponent", sequenceSegments.continuation_count_before_opponent],
  ].filter(([, value]) => value != null);

  return (
    <div style={cardStyle()}>
      <h3 style={sectionTitleStyle()}>{title}</h3>
      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", marginTop: 12 }}>
        {countRows.map(([label, value]) => (
          <div key={label}>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              {label}
            </p>
            <strong>{String(value)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function renderCountMapEntries(
  title: string,
  countMap: Record<string, number> | null | undefined,
) {
  if (!countMap || Object.keys(countMap).length === 0) {
    return null;
  }

  return (
    <div style={cardStyle()}>
      <h3 style={sectionTitleStyle()}>{title}</h3>
      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", marginTop: 12 }}>
        {Object.entries(countMap)
          .sort((left, right) => right[1] - left[1])
          .map(([type, count]) => (
            <div key={`${title}-${type}`}>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {formatMetricLabel(type)}
              </p>
              <strong>{count}</strong>
            </div>
          ))}
      </div>
    </div>
  );
}

function renderSequenceTypeBreakdown(sequenceSegments: SequenceSegments | null | undefined) {
  if (!sequenceSegments) {
    return null;
  }

  return (
    <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
      {renderCountMapEntries("Before Event Mix", sequenceSegments.before_counts_by_type)}
      {renderCountMapEntries("Anchor Event Mix", sequenceSegments.anchor_counts_by_type)}
      {renderCountMapEntries("After Event Mix", sequenceSegments.after_counts_by_type)}
    </div>
  );
}

function renderComparisonPanel(
  comparison: ComparisonContext | null | undefined,
  onOpenComparisonFrame: ((frame: number) => void) | null,
) {
  if (!comparison) {
    return null;
  }

  const sequenceDeltas = comparison.sequence_comparison?.deltas
    ? Object.entries(comparison.sequence_comparison.deltas)
      .filter(([, value]) => value != null)
      .map(([deltaKey, deltaValue]) => ({
        label: formatMetricLabel(deltaKey),
        value: String(deltaValue),
      }))
    : [];

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <div style={cardStyle()}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Left Moment
          </p>
          <h3 style={{ margin: "6px 0 8px", fontSize: "1.1rem" }}>{comparison.left_label}</h3>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
            {comparison.left_event
              ? `${comparison.left_event.team ?? "Unknown"} ${getEventDisplayLabel(comparison.left_event)} at ${formatMatchTime(comparison.left_event.start_time_s)}`
              : `Frame ${comparison.left_frame}`}
          </p>
        </div>
        <div style={cardStyle()}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Right Moment
          </p>
          <h3 style={{ margin: "6px 0 8px", fontSize: "1.1rem" }}>{comparison.right_label}</h3>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
            {comparison.right_event
              ? `${comparison.right_event.team ?? "Unknown"} ${getEventDisplayLabel(comparison.right_event)} at ${formatMatchTime(comparison.right_event.start_time_s)}`
              : `Frame ${comparison.right_frame}`}
          </p>
        </div>
      </div>

      <div style={cardStyle()}>
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Comparison
        </p>
        <h3 style={{ margin: "6px 0 8px", fontSize: "1.25rem" }}>
          {comparison.left_label} vs {comparison.right_label}
        </h3>
        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
          Left frame {comparison.left_frame} at {formatMatchTime(comparison.left_event?.start_time_s)}. Right frame {comparison.right_frame} at {formatMatchTime(comparison.right_event?.start_time_s)}.
        </p>
        {comparison.comparison_kind && comparison.comparison_kind !== "moment" ? (
          <p style={{ margin: "10px 0 0", color: "var(--ink)" }}>
            Comparison kind: <strong>{comparison.comparison_kind.replace(/_/g, " ")}</strong>
          </p>
        ) : null}
        {onOpenComparisonFrame ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 14 }}>
            <button
              type="button"
              onClick={() => onOpenComparisonFrame(comparison.left_frame)}
              style={actionButtonStyle()}
            >
              Open left frame
            </button>
            <button
              type="button"
              onClick={() => onOpenComparisonFrame(comparison.right_frame)}
              style={actionButtonStyle()}
            >
              Open right frame
            </button>
          </div>
        ) : null}
      </div>

      {renderMetricGrid(comparison.metrics_comparison)}

      {sequenceDeltas.length > 0 ? (
        <div style={cardStyle()}>
          <h3 style={sectionTitleStyle()}>Sequence Deltas</h3>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", marginTop: 12 }}>
            {sequenceDeltas.map((delta) => (
              <div key={delta.label}>
                <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {delta.label}
                </p>
                <strong>{delta.value}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function renderEventContextPanel(
  title: string,
  eventContext: AnalysisContext["event"] | null | undefined,
  onOpenEventFrame: ((frame: number) => void) | null,
) {
  if (!eventContext) {
    return null;
  }

  return (
    <div style={cardStyle()}>
      <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {title}
      </p>
      <h3 style={{ margin: "6px 0 8px", fontSize: "1.1rem" }}>
        {eventContext.team ?? "Unknown"} {getEventDisplayLabel(eventContext)}
      </h3>
      {onOpenEventFrame ? (
        <div style={{ marginBottom: 12 }}>
          <button
            type="button"
            onClick={() => onOpenEventFrame(eventContext.frame)}
            style={actionButtonStyle()}
          >
            Open event frame
          </button>
        </div>
      ) : null}
      <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))" }}>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Frame
          </p>
          <strong>{eventContext.frame}</strong>
        </div>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Time
          </p>
          <strong>{formatMatchTime(eventContext.start_time_s)}</strong>
        </div>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Relation
          </p>
          <strong>{eventContext.relation}</strong>
        </div>
        {eventContext.phase ? (
          <div>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Phase
            </p>
            <strong>{eventContext.phase.replace(/_/g, " ")}</strong>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function renderTransitionSummaryPanel(transitionSummary: AnalysisContext["transition_summary"] | null | undefined) {
  if (!transitionSummary) {
    return null;
  }

  return (
    <div style={cardStyle()}>
      <h3 style={sectionTitleStyle()}>Transition Summary</h3>
      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", marginTop: 12 }}>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Team
          </p>
          <strong>{transitionSummary.team}</strong>
        </div>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Window
          </p>
          <strong>{transitionSummary.window_seconds.toFixed(1)}s</strong>
        </div>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Events
          </p>
          <strong>{transitionSummary.event_count}</strong>
        </div>
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            First shot
          </p>
          <strong>
            {transitionSummary.first_shot_seconds_from_anchor == null
              ? "No shot"
              : `${transitionSummary.first_shot_seconds_from_anchor.toFixed(1)}s`}
          </strong>
        </div>
      </div>
      {transitionSummary.counts_by_type && Object.keys(transitionSummary.counts_by_type).length > 0 ? (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
            {Object.entries(transitionSummary.counts_by_type)
              .sort((left, right) => right[1] - left[1])
              .map(([type, count]) => (
                <div key={`transition-${type}`}>
                  <p style={{ margin: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    {formatMetricLabel(type)}
                  </p>
                  <strong>{count}</strong>
                </div>
              ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function renderReportBody(report: string) {
  const blocks = report
    .split(/\r?\n\r?\n/)
    .map((block) => block.trim())
    .filter(Boolean);

  return blocks.map((block, index) => {
    const lines = block.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const isList = lines.every((line) => /^[-*]\s+/.test(line));

    if (isList) {
      return (
        <ul key={`report-list-${index}`} style={{ margin: "0 0 0 18px", padding: 0, lineHeight: 1.7 }}>
          {lines.map((line, lineIndex) => (
            <li key={`report-list-line-${lineIndex}`}>{line.replace(/^[-*]\s+/, "")}</li>
          ))}
        </ul>
      );
    }

    return (
      <p key={`report-paragraph-${index}`} style={{ margin: 0, lineHeight: 1.7 }}>
        {lines.join(" ")}
      </p>
    );
  });
}

function renderExplanationPanel(context: AnalysisContext | null) {
  if (!context?.explanation) {
    return null;
  }

  return (
    <div style={cardStyle()}>
      <h3 style={sectionTitleStyle()}>Explanation</h3>
      <p style={{ margin: "12px 0 0", lineHeight: 1.7, color: "var(--ink)" }}>{context.explanation}</p>
    </div>
  );
}

function renderReportPanel(
  context: AnalysisContext | null,
  onCopyReport: (() => void) | null,
  reportCopied: boolean,
) {
  if (!context?.report) {
    return null;
  }

  return (
    <div style={cardStyle()}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h3 style={sectionTitleStyle()}>Report</h3>
        {onCopyReport ? (
          <button type="button" onClick={onCopyReport} style={actionButtonStyle()}>
            {reportCopied ? "Copied" : "Copy report"}
          </button>
        ) : null}
      </div>
      <div
        style={{
          display: "grid",
          gap: 12,
          marginTop: 12,
          color: "var(--ink)",
          fontFamily: "var(--font-ui), sans-serif",
        }}
      >
        {renderReportBody(context.report)}
      </div>
    </div>
  );
}

function renderResultMeta(context: AnalysisContext | null) {
  if (!context) {
    return null;
  }

  const badges = [
    `Mode: ${context.mode}`,
    `Family: ${context.query_family ?? context.mode}`,
    `Contract: ${context.response_contract_version ?? "unknown"}`,
    context.sequence_type ? `Sequence: ${context.sequence_type}` : null,
    context.comparison_kind ? `Comparison: ${context.comparison_kind}` : null,
  ].filter(Boolean) as string[];

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {badges.map((badge) => (
        <span
          key={badge}
          style={{
            borderRadius: 999,
            padding: "6px 10px",
            background: "rgba(255,255,255,0.72)",
            border: "1px solid rgba(21,32,23,0.08)",
            color: "var(--muted)",
            fontSize: 12,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          {badge}
        </span>
      ))}
    </div>
  );
}

function renderPrimarySummary(context: AnalysisContext | null, activeFrame: number, hasSequence: boolean, clipStartLabel: string | null, clipEndLabel: string | null) {
  if (!context) {
    return "Waiting for your first query.";
  }

  const eventContext = context.event;
  if (context.mode === "aggregate" && context.aggregate) {
    return (
      <>
        <strong>Aggregate query</strong>
        {` resolved as a ${context.aggregate.query_type} result with ${context.aggregate.count} matches.`}
      </>
    );
  }

  if (context.mode === "comparison" && context.comparison) {
    return (
      <>
        <strong>Comparison result</strong>
        {` comparing ${context.comparison.left_label} against ${context.comparison.right_label}.`}
        {context.comparison.comparison_kind && context.comparison.comparison_kind !== "moment"
          ? ` Comparison kind: ${context.comparison.comparison_kind.replace(/_/g, " ")}.`
          : ""}
      </>
    );
  }

  if (eventContext) {
    return (
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
        {hasSequence && clipStartLabel && clipEndLabel ? ` Clip window: ${clipStartLabel} to ${clipEndLabel}.` : ""}
      </>
    );
  }

  if (context.frame != null) {
    return (
      <>
        <strong>Direct frame lookup</strong>
        {` resolved to frame ${context.frame}.`}
      </>
    );
  }

  return "Waiting for your first query.";
}

function renderQueryContextPanel(context: AnalysisContext | null) {
  if (!context) {
    return null;
  }

  return (
    <div style={cardStyle()}>
      <h3 style={sectionTitleStyle()}>Query Context</h3>
      <p style={{ margin: "12px 0 0", color: "var(--ink)", lineHeight: 1.7 }}>
        {context.query}
      </p>
    </div>
  );
}

function renderResultSurface(
  context: AnalysisContext | null,
  displayedCoordinates: CoordinateMap | null,
  deferredCoordinates: CoordinateMap | null,
  activeFrame: number,
  sequenceEvents: SequenceEvent[],
  replaySequence: TrackingSequence | null,
  pitchTransitionMs: number,
  onOpenEventFrame: ((frame: number) => void) | null,
  onCopyReport: (() => void) | null,
  reportCopied: boolean,
) {
  if (!context) {
    return (
      <div style={cardStyle()}>
        <h3 style={sectionTitleStyle()}>No Result Yet</h3>
        <p style={{ margin: "10px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
          Submit a query to load the first football analysis result.
        </p>
      </div>
    );
  }

  if (context.mode === "aggregate") {
    return (
      <div style={{ display: "grid", gap: 14 }}>
        {renderAggregatePanel(context.aggregate, onOpenEventFrame)}
        {renderExplanationPanel(context)}
        {renderReportPanel(context, onCopyReport, reportCopied)}
      </div>
    );
  }

  if (context.mode === "comparison") {
    return (
      <div style={{ display: "grid", gap: 14 }}>
        {renderComparisonPanel(context.comparison, onOpenEventFrame)}
        {displayedCoordinates ? (
          <div style={{ ...cardStyle(), padding: 20 }}>
            <h3 style={sectionTitleStyle()}>Reference Pitch</h3>
            <p style={{ margin: "8px 0 16px", color: "var(--muted)", lineHeight: 1.6 }}>
              This pitch reflects the currently returned reference frame from the comparison result.
            </p>
            <PitchCanvas
              coordinates={deferredCoordinates}
              activeFrame={activeFrame}
              sequenceEvents={sequenceEvents}
              framesPerSecond={replaySequence?.frames_per_second ?? 25}
              transitionMs={pitchTransitionMs}
            />
          </div>
        ) : null}
        {renderExplanationPanel(context)}
        {renderReportPanel(context, onCopyReport, reportCopied)}
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
        {renderEventContextPanel("Primary Event", context.event, onOpenEventFrame)}
        {renderEventContextPanel("Anchor Event", context.anchor_event ?? null, onOpenEventFrame)}
      </div>
      {renderQueryContextPanel(context)}
      {renderMetricGrid(context.metrics)}
      {renderTransitionSummaryPanel(context.transition_summary)}
      {renderSequenceSegmentsPanel(
        context.sequence_segments,
        context.mode === "buildup" ? "Buildup Segmentation" : context.mode === "transition" ? "Transition Segmentation" : "Sequence Segmentation",
      )}
      {renderSequenceTypeBreakdown(context.sequence_segments)}
      {sequenceEvents.length > 0 && replaySequence ? (
        <div style={cardStyle()}>
          <h3 style={sectionTitleStyle()}>Sequence Events</h3>
          <div style={{ marginTop: 12 }}>
            {renderSequenceChips(sequenceEvents, replaySequence.frames_per_second)}
          </div>
        </div>
      ) : null}
      {displayedCoordinates ? (
        <div style={{ ...cardStyle(), padding: 20 }}>
          <h3 style={sectionTitleStyle()}>
            {context.mode === "buildup"
              ? "Buildup Replay"
              : context.mode === "transition"
                ? "Transition Replay"
                : context.mode === "sequence_event"
                  ? "Sequence Event Replay"
                  : "Pitch View"}
          </h3>
          <div style={{ marginTop: 14 }}>
            <PitchCanvas
              coordinates={deferredCoordinates}
              activeFrame={activeFrame}
              sequenceEvents={sequenceEvents}
              framesPerSecond={replaySequence?.frames_per_second ?? 25}
              transitionMs={pitchTransitionMs}
            />
          </div>
        </div>
      ) : null}
      {renderExplanationPanel(context)}
      {renderReportPanel(context, onCopyReport, reportCopied)}
    </div>
  );
}

export function AnalysisWorkspace() {
  const [reportCopied, setReportCopied] = useState(false);
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
  const context = latestPayload?.context ?? null;
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
  const clipStartLabel = replaySequence ? formatClockFromFrame(replaySequence.start_frame, replaySequence.frames_per_second) : null;
  const clipEndLabel = replaySequence ? formatClockFromFrame(replaySequence.end_frame, replaySequence.frames_per_second) : null;

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
  }, [advancePlaybackTick, hasSequence, isPlaying, playbackIntervalMs, sequence, setPlaying, status]);

  const openResultFrame = useEffectEvent((frame: number) => {
    startTransition(() => requestFrame(frame));
  });

  const copyReport = useEffectEvent(() => {
    const report = latestPayload?.context.report;
    if (!report || typeof navigator === "undefined" || !navigator.clipboard) {
      return;
    }

    void navigator.clipboard.writeText(report);
    setReportCopied(true);
    window.setTimeout(() => {
      setReportCopied(false);
    }, 1600);
  });

  return (
    <main
      style={{
        width: "min(1360px, calc(100vw - 32px))",
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
          The frontend is now moving from one pitch-first page into a result-aware football analysis workspace with dedicated surfaces for replay, aggregate, comparison, and report outputs.
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
          Run Analysis Query
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
                <span>Start {clipStartLabel}</span>
                <span>Event {formatClockFromFrame(replaySequence.event_frame, replaySequence.frames_per_second)}</span>
                <span>End {clipEndLabel}</span>
              </div>
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
          Try prompts across the full backend range, like "Show me the away team's second corner",
          "How many away shots were there in period 2?", "Show me the buildup to the goal",
          or "Compare the transition after the first and second away recoveries".
        </p>
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
            {getPrimaryResultTitle(context)}
          </h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
            {displayedCoordinates ? `${Object.keys(displayedCoordinates).length} tracked entities` : "Data-first result"}
          </p>
        </div>

        {renderResultMeta(context)}

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
          {renderPrimarySummary(context, activeFrame, hasSequence, clipStartLabel, clipEndLabel)}
        </div>

        {renderResultSurface(
          context,
          displayedCoordinates,
          deferredCoordinates,
          activeFrame,
          sequenceEvents,
          replaySequence,
          pitchTransitionMs,
          openResultFrame,
          copyReport,
          reportCopied,
        )}
      </section>
    </main>
  );
}
