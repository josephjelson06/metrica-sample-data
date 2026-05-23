from __future__ import annotations

from typing import Any

from backend.tools.db_engine import FRAMES_PER_SECOND, get_frame_team_metrics


def _format_match_time(seconds: float | int | None) -> str:
    if seconds is None:
        return "unknown time"

    total_seconds = int(round(float(seconds)))
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"


def _format_signed_delta(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.3f}"


def _describe_filters(filters: dict[str, Any]) -> str:
    parts: list[str] = []
    if filters.get("team"):
        parts.append(str(filters["team"]))
    if filters.get("event_type"):
        parts.append(str(filters["event_type"]).lower())
    if filters.get("subtype_contains"):
        parts.append(str(filters["subtype_contains"]).lower())
    if filters.get("period") is not None:
        parts.append(f"period {filters['period']}")
    if filters.get("pitch_zone"):
        parts.append(str(filters["pitch_zone"]).replace("_", " "))
    if filters.get("phase"):
        parts.append(str(filters["phase"]).replace("_", " "))
    return ", ".join(parts) if parts else "the requested filters"


def _metric_focus_line(metrics: dict[str, Any] | None) -> str | None:
    if not metrics:
        return None

    requested_metric = metrics.get("requested_metric")
    if requested_metric == "shape_metrics":
        if "Home" in metrics and "Away" in metrics:
            return (
                f"Home width {metrics['Home']['width']:.3f}, Away width {metrics['Away']['width']:.3f}; "
                f"Home depth {metrics['Home']['depth']:.3f}, Away depth {metrics['Away']['depth']:.3f}."
            )
        return None

    metric_value = metrics.get(requested_metric)
    team = metrics.get("team")
    if metric_value is None or team is None:
        return None

    readable_metric = str(requested_metric).replace("_", " ")
    return f"{team} {readable_metric} at this moment is {float(metric_value):.3f}."


def _sequence_change_line(sequence: dict[str, Any] | None, team: str | None) -> str | None:
    if not sequence or not team:
        return None

    start_frame = sequence.get("start_frame")
    event_frame = sequence.get("event_frame")
    if not isinstance(start_frame, int) or not isinstance(event_frame, int):
        return None

    start_metrics = get_frame_team_metrics(start_frame, team)
    end_metrics = get_frame_team_metrics(event_frame, team)
    if not start_metrics or not end_metrics:
        return None

    width_delta = float(end_metrics["width"]) - float(start_metrics["width"])
    depth_delta = float(end_metrics["depth"]) - float(start_metrics["depth"])
    compactness_delta = float(end_metrics["compactness_area"]) - float(start_metrics["compactness_area"])
    return (
        f"From the start of the clip to the key frame, {team} width changed by {_format_signed_delta(width_delta)}, "
        f"depth by {_format_signed_delta(depth_delta)}, and compactness area by {_format_signed_delta(compactness_delta)}."
    )


def build_explanation(analysis_result: dict[str, Any]) -> str:
    context = analysis_result["context"]
    mode = context.get("mode")

    if mode == "aggregate":
        aggregate = context.get("aggregate", {})
        filters = aggregate.get("filters", {})
        filter_text = _describe_filters(filters)
        if aggregate.get("query_type") == "count":
            return f"Found {aggregate.get('count', 0)} matching events for {filter_text}."

        events = aggregate.get("events", [])
        if not events:
            return f"No matching events were found for {filter_text}."
        first_event = events[0]
        last_event = events[-1]
        return (
            f"Found {len(events)} matching events for {filter_text}. "
            f"The list starts at {_format_match_time(first_event.get('start_time_s'))} and ends at "
            f"{_format_match_time(last_event.get('start_time_s'))}."
        )

    frame = context.get("frame")
    event = context.get("event")
    sequence = analysis_result.get("sequence")
    metrics = context.get("metrics")

    lines: list[str] = []
    if event is None:
        lines.append(f"Resolved the query to frame {frame}.")
    else:
        team = event.get("team", "Unknown team")
        event_type = str(event.get("type", "event")).lower()
        subtype = event.get("subtype")
        subtype_text = f" ({str(subtype).lower()})" if subtype else ""
        lines.append(
            f"Resolved the key moment as {team} {event_type}{subtype_text} at "
            f"{_format_match_time(event.get('start_time_s'))}, frame {event.get('frame')}."
        )

    if context.get("anchor_event") is not None:
        anchor_event = context["anchor_event"]
        lines.append(
            f"The anchor event was {anchor_event.get('team')} {str(anchor_event.get('type')).lower()} at "
            f"{_format_match_time(anchor_event.get('start_time_s'))}, and the result was resolved relative to it."
        )

    if sequence and sequence.get("frames"):
        nearby_events = sequence.get("events", [])
        lines.append(
            f"The replay window spans {_format_match_time(sequence.get('start_frame', 0) / FRAMES_PER_SECOND)} "
            f"to {_format_match_time(sequence.get('end_frame', 0) / FRAMES_PER_SECOND)} with "
            f"{len(sequence['frames'])} frames and {len(nearby_events)} nearby events."
        )

    metric_line = _metric_focus_line(metrics)
    if metric_line:
        lines.append(metric_line)

    comparison_team = None
    if metrics and metrics.get("team"):
        comparison_team = str(metrics["team"])
    elif event and event.get("team") in {"Home", "Away"}:
        comparison_team = str(event["team"])

    change_line = _sequence_change_line(sequence, comparison_team)
    if change_line:
        lines.append(change_line)

    return " ".join(lines)


def build_report(analysis_result: dict[str, Any]) -> str:
    context = analysis_result["context"]
    mode = context.get("mode")
    explanation = build_explanation(analysis_result)

    if mode == "aggregate":
        aggregate = context.get("aggregate", {})
        filters = _describe_filters(aggregate.get("filters", {}))
        if aggregate.get("query_type") == "count":
            return "\n".join(
                [
                    "Football Query Report",
                    f"Query: {context.get('query')}",
                    f"Result: {aggregate.get('count', 0)} matches for {filters}.",
                    f"Summary: {explanation}",
                ]
            )

        events = aggregate.get("events", [])[:5]
        event_lines = [
            f"- {event.get('team')} {event.get('type')} at {_format_match_time(event.get('start_time_s'))}"
            for event in events
        ]
        return "\n".join(
            [
                "Football Query Report",
                f"Query: {context.get('query')}",
                f"Result: {aggregate.get('count', 0)} listed matches for {filters}.",
                "Examples:",
                *event_lines,
                f"Summary: {explanation}",
            ]
        )

    report_lines = [
        "Football Query Report",
        f"Query: {context.get('query')}",
        f"Resolved frame: {context.get('frame')}",
    ]
    if context.get("event") is not None:
        event = context["event"]
        report_lines.append(
            f"Resolved event: {event.get('team')} {event.get('type')} at {_format_match_time(event.get('start_time_s'))}."
        )
    if context.get("anchor_event") is not None:
        anchor_event = context["anchor_event"]
        report_lines.append(
            f"Anchor event: {anchor_event.get('team')} {anchor_event.get('type')} at {_format_match_time(anchor_event.get('start_time_s'))}."
        )
    if context.get("metrics") is not None:
        metric_line = _metric_focus_line(context["metrics"])
        if metric_line:
            report_lines.append(f"Metric: {metric_line}")
    report_lines.append(f"Summary: {explanation}")
    return "\n".join(report_lines)
