from __future__ import annotations

from typing import Any

from backend.tools.db_engine import (
    FRAMES_PER_SECOND,
    compare_frame_structures,
    compare_team_metrics_between_frames,
    get_frame_team_metrics,
    summarize_team_event_chain,
)


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


def _format_event_summary(event: dict[str, Any] | None) -> str | None:
    if not event:
        return None

    team = event.get("team", "Unknown team")
    event_type = str(event.get("type", "event")).lower()
    subtype = event.get("subtype")
    subtype_text = f" ({str(subtype).lower()})" if subtype else ""
    return f"{team} {event_type}{subtype_text} at {_format_match_time(event.get('time_s'))}"


def _format_top_type_counts(counts_by_type: dict[str, int], limit: int = 2) -> str | None:
    if not counts_by_type:
        return None

    ordered_counts = sorted(counts_by_type.items(), key=lambda item: (-item[1], item[0]))
    top_counts = ordered_counts[:limit]
    return ", ".join(f"{count} {event_type.lower()}" for event_type, count in top_counts)


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
                f"Home depth {metrics['Home']['depth']:.3f}, Away depth {metrics['Away']['depth']:.3f}; "
                f"Home line-height proxy {metrics['Home']['line_height_proxy']:.3f}, Away line-height proxy {metrics['Away']['line_height_proxy']:.3f}."
            )
        return None

    if requested_metric == "unit_spacing":
        team = metrics.get("team")
        deep_to_mid = metrics.get("deep_to_mid_spacing")
        mid_to_high = metrics.get("mid_to_high_spacing")
        if team is None or deep_to_mid is None or mid_to_high is None:
            return None
        return (
            f"{team} unit spacing at this moment is deep-to-mid {float(deep_to_mid):.3f} and "
            f"mid-to-high {float(mid_to_high):.3f}."
        )

    metric_value = metrics.get(requested_metric)
    team = metrics.get("team")
    if metric_value is None or team is None:
        return None

    readable_metric = str(requested_metric).replace("_", " ")
    if requested_metric == "line_height_proxy":
        readable_metric = "line-height proxy"
    return f"{team} {readable_metric} at this moment is {float(metric_value):.3f}."


def _sequence_change_line(sequence: dict[str, Any] | None, team: str | None) -> str | None:
    if not sequence or not team:
        return None

    start_frame = sequence.get("start_frame")
    event_frame = sequence.get("event_frame")
    if not isinstance(start_frame, int) or not isinstance(event_frame, int):
        return None

    comparison = compare_team_metrics_between_frames(start_frame, event_frame, team)
    if not comparison:
        return None

    deltas = comparison["deltas"]
    width_delta = float(deltas["width"])
    depth_delta = float(deltas["depth"])
    compactness_delta = float(deltas["compactness_area"])
    line_height_delta = float(deltas["line_height_proxy"])
    deep_to_mid_delta = float(deltas["deep_to_mid_spacing"])
    mid_to_high_delta = float(deltas["mid_to_high_spacing"])
    return (
        f"From the start of the clip to the key frame, {team} width changed by {_format_signed_delta(width_delta)}, "
        f"depth by {_format_signed_delta(depth_delta)}, compactness area by {_format_signed_delta(compactness_delta)}, "
        f"line-height proxy by {_format_signed_delta(line_height_delta)}, deep-to-mid spacing by {_format_signed_delta(deep_to_mid_delta)}, "
        f"and mid-to-high spacing by {_format_signed_delta(mid_to_high_delta)}."
    )


def _comparison_delta_line(comparison_metrics: dict[str, Any]) -> str | None:
    deltas = comparison_metrics.get("deltas")
    team = comparison_metrics.get("team")
    if not deltas or not team:
        return None

    return (
        f"For {team}, width changed by {_format_signed_delta(float(deltas['width']))}, "
        f"depth by {_format_signed_delta(float(deltas['depth']))}, "
        f"line-height proxy by {_format_signed_delta(float(deltas['line_height_proxy']))}, "
        f"deep-to-mid spacing by {_format_signed_delta(float(deltas['deep_to_mid_spacing']))}, "
        f"and mid-to-high spacing by {_format_signed_delta(float(deltas['mid_to_high_spacing']))}."
    )


def _sequence_comparison_line(sequence_comparison: dict[str, Any]) -> str | None:
    deltas = sequence_comparison.get("deltas", {})
    if not deltas:
        return None

    parts: list[str] = []
    before_delta = deltas.get("same_team_before_count")
    if before_delta is not None:
        parts.append(f"lead-in same-team events {_format_signed_delta(float(before_delta))}")
    after_delta = deltas.get("same_team_after_count")
    if after_delta is not None:
        parts.append(f"follow-up same-team events {_format_signed_delta(float(after_delta))}")
    continuation_delta = deltas.get("continuation_count_before_opponent")
    if continuation_delta is not None:
        parts.append(f"continuation-before-opponent {_format_signed_delta(float(continuation_delta))}")
    opponent_after_delta = deltas.get("opponent_after_count")
    if opponent_after_delta is not None:
        parts.append(f"opponent follow-up events {_format_signed_delta(float(opponent_after_delta))}")

    if not parts:
        return None
    return "Sequence comparison deltas: " + ", ".join(parts) + "."


def _build_comparison_explanation(context: dict[str, Any]) -> str:
    comparison = context.get("comparison", {})
    left_label = comparison.get("left_label", "the first moment")
    right_label = comparison.get("right_label", "the second moment")
    left_frame = comparison.get("left_frame")
    right_frame = comparison.get("right_frame")
    lines = [
        f"Compared {left_label} (frame {left_frame}) with {right_label} (frame {right_frame})."
    ]

    left_event = comparison.get("left_event")
    right_event = comparison.get("right_event")
    if left_event is not None and right_event is not None:
        lines.append(
            f"The first moment was at {_format_match_time(left_event.get('start_time_s'))} and "
            f"the second moment was at {_format_match_time(right_event.get('start_time_s'))}."
        )

    metrics_comparison = comparison.get("metrics_comparison", {})
    if "deltas" in metrics_comparison:
        delta_line = _comparison_delta_line(metrics_comparison)
        if delta_line:
            lines.append(delta_line)
    else:
        home_delta_line = _comparison_delta_line(metrics_comparison.get("Home", {}))
        away_delta_line = _comparison_delta_line(metrics_comparison.get("Away", {}))
        if home_delta_line:
            lines.append(home_delta_line)
        if away_delta_line:
            lines.append(away_delta_line)

    sequence_comparison_line = _sequence_comparison_line(comparison.get("sequence_comparison", {}))
    if sequence_comparison_line:
        lines.append(sequence_comparison_line)

    return " ".join(lines)


def _build_buildup_event_mix_line(sequence: dict[str, Any] | None) -> str | None:
    if not sequence:
        return None

    events = sequence.get("events", [])
    if not events:
        return None

    counts: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("type", "event")).lower()
        counts[event_type] = counts.get(event_type, 0) + 1

    ordered_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_counts = ordered_counts[:3]
    mix_text = ", ".join(f"{count} {event_type}" for event_type, count in top_counts)
    return f"The buildup event mix is led by {mix_text}."


def _build_buildup_segmentation_line(context: dict[str, Any]) -> str | None:
    sequence_segments = context.get("sequence_segments")
    event = context.get("event")
    if not sequence_segments or not event or event.get("team") not in {"Home", "Away"}:
        return None

    same_team_before_count = int(sequence_segments.get("same_team_before_count", 0))
    opponent_before_count = int(sequence_segments.get("opponent_before_count", 0))
    same_team_counts = _format_top_type_counts(sequence_segments.get("same_team_before_counts_by_type", {}))
    immediate_pre_event = _format_event_summary(sequence_segments.get("immediate_pre_event"))
    last_same_team_before = _format_event_summary(sequence_segments.get("last_same_team_before_event"))

    line = (
        f"Before the key event, {event['team']} produced {same_team_before_count} same-team lead-in events"
        f" while the opponent contributed {opponent_before_count} events in the same window."
    )
    if same_team_counts:
        line += f" The lead-in was mainly {same_team_counts}."
    if last_same_team_before:
        line += f" The final same-team action before the key event was {last_same_team_before}."
    elif immediate_pre_event:
        line += f" The immediate pre-event in the window was {immediate_pre_event}."
    return line


def _build_transition_chain_line(context: dict[str, Any], sequence: dict[str, Any] | None) -> str | None:
    event = context.get("event")
    if not sequence or not event or event.get("team") not in {"Home", "Away"}:
        return None

    transition_summary = context.get("transition_summary")
    if transition_summary is None:
        transition_summary = summarize_team_event_chain(
            events=sequence.get("events", []),
            team=str(event["team"]),
            anchor_frame=int(event["frame"]),
        )

    if not transition_summary or int(transition_summary.get("event_count", 0)) == 0:
        return f"No same-team follow-up events were recorded for {event.get('team')} inside this transition window."

    counts_by_type = transition_summary.get("counts_by_type", {})
    ordered_counts = sorted(counts_by_type.items(), key=lambda item: (-item[1], item[0]))
    top_counts = ", ".join(
        f"{count} {event_type.lower()}" for event_type, count in ordered_counts[:3]
    )
    line = f"After the trigger, {transition_summary['team']} produced {transition_summary['event_count']} same-team events"
    if float(transition_summary["window_seconds"]) > 0:
        line += f" across {transition_summary['window_seconds']:.1f} seconds"
    line += f", led by {top_counts}."
    first_shot_seconds = transition_summary.get("first_shot_seconds_from_anchor")
    if first_shot_seconds is not None:
        line += f" The first shot arrived {float(first_shot_seconds):.1f} seconds after the trigger."
    elif transition_summary.get("last_event_type"):
        line += f" The sequence ended with {str(transition_summary['last_event_type']).lower()}."
    return line


def _build_transition_segmentation_line(context: dict[str, Any]) -> str | None:
    sequence_segments = context.get("sequence_segments")
    event = context.get("event")
    if not sequence_segments or not event or event.get("team") not in {"Home", "Away"}:
        return None

    continuation_count = int(sequence_segments.get("continuation_count_before_opponent", 0))
    opponent_after_count = int(sequence_segments.get("opponent_after_count", 0))
    continuation_counts = _format_top_type_counts(sequence_segments.get("continuation_counts_by_type", {}))
    first_same_team_after = _format_event_summary(sequence_segments.get("first_same_team_after_event"))
    first_opponent_after = _format_event_summary(sequence_segments.get("first_opponent_after_event"))
    first_shot_after = _format_event_summary(sequence_segments.get("first_same_team_shot_after"))

    line = (
        f"Before the opponent interrupted again, {event['team']} produced {continuation_count} continuation events"
        f" after the trigger."
    )
    if continuation_counts:
        line += f" That continuation was mainly {continuation_counts}."
    if first_same_team_after:
        line += f" The first same-team follow-up was {first_same_team_after}."
    if first_shot_after:
        line += f" The first shot in the chain was {first_shot_after}."
    elif first_opponent_after:
        line += f" The first opponent interruption was {first_opponent_after}."
    elif opponent_after_count == 0:
        line += " The sequence stayed with the same team for the full window."
    return line


def build_explanation(analysis_result: dict[str, Any]) -> str:
    context = analysis_result["context"]
    mode = context.get("mode")

    if mode == "comparison":
        return _build_comparison_explanation(context)

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

    if mode == "buildup":
        lines.append("This response focuses on the longer lead-up into the key event, not just the immediate replay clip.")
    elif mode == "transition":
        lines.append("This response focuses on the immediate phase after the trigger event to capture the transition sequence.")

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

    buildup_mix_line = _build_buildup_event_mix_line(sequence if mode == "buildup" else None)
    if buildup_mix_line:
        lines.append(buildup_mix_line)

    buildup_segmentation_line = _build_buildup_segmentation_line(context if mode == "buildup" else {})
    if buildup_segmentation_line:
        lines.append(buildup_segmentation_line)

    transition_chain_line = _build_transition_chain_line(context, sequence if mode == "transition" else None)
    if transition_chain_line:
        lines.append(transition_chain_line)

    transition_segmentation_line = _build_transition_segmentation_line(context if mode == "transition" else {})
    if transition_segmentation_line:
        lines.append(transition_segmentation_line)

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

    if mode == "comparison":
        comparison = context.get("comparison", {})
        return "\n".join(
            [
                "Football Comparison Report",
                f"Query: {context.get('query')}",
                f"Left moment: {comparison.get('left_label')} (frame {comparison.get('left_frame')})",
                f"Right moment: {comparison.get('right_label')} (frame {comparison.get('right_frame')})",
                f"Summary: {explanation}",
            ]
        )

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
