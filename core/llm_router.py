from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from tools.db_engine import count_events, find_event, get_event_tracking_window, get_frame_team_metrics, get_tracking_frame, list_events


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = "llama-3.3-70b-versatile"
FRAMES_PER_SECOND = 25
MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = f"""
You route football match-analysis queries to local database tools.

Rules:
- If the user gives a minute or clock time, convert it to a tracking frame using {FRAMES_PER_SECOND} fps.
- Tool arguments must be valid JSON values.
- Never send arithmetic expressions like 5 * 60 * 25 as tool arguments.
- If the user already gives a frame number, use it directly and call get_tracking_frame.
- For event-based questions, first call find_event and then call get_tracking_frame
  using the returned frame.
- Prefer these mappings when useful:
  - goal -> event_type="SHOT", subtype_contains="GOAL"
  - saved shot -> event_type="SHOT", subtype_contains="SAVED"
  - shot -> event_type="SHOT"
  - corner -> event_type="SET PIECE", subtype_contains="CORNER KICK"
  - free kick -> event_type="SET PIECE", subtype_contains="FREE KICK"
  - kick off -> event_type="SET PIECE", subtype_contains="KICK OFF"
  - throw in -> event_type="SET PIECE", subtype_contains="THROW IN"
  - penalty -> event_type="SET PIECE", subtype_contains="PENALTY"
  - pass -> event_type="PASS"
  - recovery -> event_type="RECOVERY"
  - interception -> event_type="RECOVERY", subtype_contains="INTERCEPTION"
  - yellow card -> event_type="CARD", subtype_contains="YELLOW"
- Support order words like first, second, third, fourth, fifth, and last.
- Support relative lookups like before, after, and around when the user provides a time or frame.
- Support period filters such as first half, second half, period 1, and period 2.
- Support pitch zones such as attacking third, middle third, defensive third, left wing,
  right wing, central channel, and penalty box.
- Support phase filters such as set piece, in possession, out of possession,
  attacking transition, and defensive transition.
- The final tool you should use for returning coordinates is always get_tracking_frame.
""".strip()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_event",
            "description": (
                "Find a matching football event in the events parquet file and return "
                "rich event metadata including the event frame."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Main Metrica event type such as SHOT, PASS, SET PIECE, RECOVERY, CARD, or BALL OUT.",
                    },
                    "team": {
                        "type": "string",
                        "description": "Optional team filter, usually Home or Away.",
                    },
                    "subtype_contains": {
                        "type": "string",
                        "description": "Optional subtype filter such as GOAL, SAVED, CORNER KICK, FREE KICK, THROW IN, or YELLOW.",
                    },
                    "occurrence": {
                        "type": "integer",
                        "description": "Occurrence number in the ordered result set. Use 1 for first match.",
                    },
                    "order": {
                        "type": "string",
                        "description": "Use first or last to control chronological direction.",
                    },
                    "relation": {
                        "type": "string",
                        "description": "Use exact, before, after, or around.",
                    },
                    "anchor_frame": {
                        "type": "integer",
                        "description": "Reference frame for before, after, or around lookups.",
                    },
                    "period": {
                        "type": "integer",
                        "description": "Optional match period filter such as 1 or 2.",
                    },
                    "pitch_zone": {
                        "type": "string",
                        "description": "Optional normalized pitch zone such as attacking_third, middle_third, defensive_third, left_wing, right_wing, central_channel, or penalty_box.",
                    },
                    "phase": {
                        "type": "string",
                        "description": "Optional phase label such as set_piece, in_possession, out_of_possession, attacking_transition, or defensive_transition.",
                    },
                },
                "required": ["event_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tracking_frame",
            "description": (
                "Look up all available x and y coordinates for players and the ball "
                "for one exact tracking frame."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "frame": {
                        "type": "integer",
                        "description": "The exact tracking frame number.",
                    }
                },
                "required": ["frame"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "find_event": find_event,
    "get_tracking_frame": get_tracking_frame,
}

ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}

EVENT_PATTERNS = [
    {"pattern": r"\byellow card\b|\bcard\b", "event_type": "CARD", "subtype_contains": "YELLOW"},
    {"pattern": r"\bgoal(?:s)?\b", "event_type": "SHOT", "subtype_contains": "GOAL"},
    {"pattern": r"\bsaved shot\b|\bshot saved\b|\bon target saved\b|\bsaved\b", "event_type": "SHOT", "subtype_contains": "SAVED"},
    {"pattern": r"\bcorners?\b|\bcorner kicks?\b", "event_type": "SET PIECE", "subtype_contains": "CORNER KICK"},
    {"pattern": r"\bfree kicks?\b", "event_type": "SET PIECE", "subtype_contains": "FREE KICK"},
    {"pattern": r"\bkick[\s-]?off\b", "event_type": "SET PIECE", "subtype_contains": "KICK OFF"},
    {"pattern": r"\bthrow[\s-]?ins?\b", "event_type": "SET PIECE", "subtype_contains": "THROW IN"},
    {"pattern": r"\bpenalt(?:y|ies)\b", "event_type": "SET PIECE", "subtype_contains": "PENALTY"},
    {"pattern": r"\boffside\b", "event_type": "BALL LOST", "subtype_contains": "OFFSIDE"},
    {"pattern": r"\bball out\b", "event_type": "BALL OUT", "subtype_contains": None},
    {"pattern": r"\brecover(?:y|ies)?\b", "event_type": "RECOVERY", "subtype_contains": None},
    {"pattern": r"\binterception(?:s)?\b", "event_type": "RECOVERY", "subtype_contains": "INTERCEPTION"},
    {"pattern": r"\bpass(?:es)?\b", "event_type": "PASS", "subtype_contains": None},
    {"pattern": r"\bshot(?:s)?\b", "event_type": "SHOT", "subtype_contains": None},
]


def _extract_frame_hint(user_query: str) -> int | None:
    clock_match = re.search(r"\b(\d{1,2}):(\d{2})\b", user_query)
    if clock_match:
        minutes = int(clock_match.group(1))
        seconds = int(clock_match.group(2))
        total_seconds = (minutes * 60) + seconds
        return int(round(total_seconds * FRAMES_PER_SECOND))

    ordinal_minute_match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+minute\b", user_query, flags=re.IGNORECASE)
    if ordinal_minute_match:
        minute_value = float(ordinal_minute_match.group(1))
        return int(round(minute_value * 60 * FRAMES_PER_SECOND))

    minute_match = re.search(r"\bminute\s+(\d+(?:\.\d+)?)\b", user_query, flags=re.IGNORECASE)
    if minute_match:
        minute_value = float(minute_match.group(1))
        return int(round(minute_value * 60 * FRAMES_PER_SECOND))

    frame_match = re.search(r"\bframe\s+(\d+)\b", user_query, flags=re.IGNORECASE)
    if frame_match:
        return int(frame_match.group(1))

    return None


def _extract_occurrence_hint(user_query: str) -> int | None:
    lower_query = user_query.lower()
    ordinal_context_pattern = (
        r"(goal|shot|corner|corner kick|pass|recovery|interception|card|"
        r"throw[\s-]?in|free kick|penalty|saved shot|event|foul|minute)"
    )

    for word, value in ORDINAL_WORDS.items():
        if re.search(rf"\b{word}\s+{ordinal_context_pattern}\b", lower_query):
            return value

    ordinal_number_match = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", user_query, flags=re.IGNORECASE)
    if ordinal_number_match:
        return int(ordinal_number_match.group(1))

    return None


def _extract_order_hint(user_query: str) -> str | None:
    order_context_pattern = (
        r"(goal|shot|corner|corner kick|pass|recovery|interception|card|"
        r"throw[\s-]?in|free kick|penalty|saved shot|event|foul)"
    )

    if re.search(rf"\b(last|latest|final)\s+{order_context_pattern}\b", user_query, flags=re.IGNORECASE):
        return "last"

    if _extract_occurrence_hint(user_query) is not None or re.search(rf"\bfirst\s+{order_context_pattern}\b", user_query, flags=re.IGNORECASE):
        return "first"

    return None


def _extract_team_hint(user_query: str) -> str | None:
    if re.search(r"\bhome\b", user_query, flags=re.IGNORECASE):
        return "Home"

    if re.search(r"\baway\b", user_query, flags=re.IGNORECASE):
        return "Away"

    return None


def _extract_relation_hint(user_query: str) -> str | None:
    if re.search(r"\bbefore\b", user_query, flags=re.IGNORECASE):
        return "before"

    if re.search(r"\bafter\b", user_query, flags=re.IGNORECASE):
        return "after"

    if re.search(r"\b(around|near|nearest|closest)\b", user_query, flags=re.IGNORECASE):
        return "around"

    return None


def _extract_period_hint(user_query: str) -> int | None:
    if re.search(r"\b(first half|period 1|period one)\b", user_query, flags=re.IGNORECASE):
        return 1

    if re.search(r"\b(second half|period 2|period two)\b", user_query, flags=re.IGNORECASE):
        return 2

    period_match = re.search(r"\bperiod\s+(\d+)\b", user_query, flags=re.IGNORECASE)
    if period_match:
        return int(period_match.group(1))

    return None


def _extract_pitch_zone_hint(user_query: str) -> str | None:
    zone_patterns = [
        (r"\b(attacking|final)\s+third\b", "attacking_third"),
        (r"\bmiddle\s+third\b", "middle_third"),
        (r"\bdefensive\s+third\b", "defensive_third"),
        (r"\b(left wing|left flank)\b", "left_wing"),
        (r"\b(right wing|right flank)\b", "right_wing"),
        (r"\b(central channel|centre channel|center channel|central area)\b", "central_channel"),
        (r"\b(penalty box|the box|into the box|in the box)\b", "penalty_box"),
    ]

    for pattern, zone in zone_patterns:
        if re.search(pattern, user_query, flags=re.IGNORECASE):
            return zone

    return None


def _extract_aggregate_intent(user_query: str) -> str | None:
    if re.search(r"\b(how many|count|number of)\b", user_query, flags=re.IGNORECASE):
        return "count"

    if re.search(r"\b(list|show all|all\b|every)\b", user_query, flags=re.IGNORECASE):
        return "list"

    return None


def _extract_phase_hint(user_query: str) -> str | None:
    phase_patterns = [
        (r"\bset piece\b", "set_piece"),
        (r"\bin possession\b", "in_possession"),
        (r"\bout of possession\b", "out_of_possession"),
        (r"\b(attacking transition|attack transition|counter(?:-|\s)?attack)\b", "attacking_transition"),
        (r"\b(defensive transition|transition to defense|transition to defence)\b", "defensive_transition"),
    ]

    for pattern, phase in phase_patterns:
        if re.search(pattern, user_query, flags=re.IGNORECASE):
            return phase

    return None


def _extract_metric_hint(user_query: str) -> dict[str, Any] | None:
    metric_patterns = [
        (r"\bwidth\b", "width"),
        (r"\bdepth\b", "depth"),
        (r"\bcompact(?:ness)?\b", "compactness_area"),
        (r"\bhull area\b|\bhull\b", "hull_area"),
        (r"\bcentroid\b|\bcenter\b|\bcentre\b", "centroid"),
        (r"\bshape metrics\b|\bmetrics\b|\bteam shape\b|\bshape\b", "shape_metrics"),
    ]

    for pattern, metric_name in metric_patterns:
        if re.search(pattern, user_query, flags=re.IGNORECASE):
            return {
                "metric": metric_name,
                "team": _extract_team_hint(user_query),
            }

    return None


def _extract_sequence_event_query(user_query: str) -> dict[str, Any] | None:
    sequence_match = re.search(r"\b(after|before)\b", user_query, flags=re.IGNORECASE)
    if sequence_match is None:
        return None

    relation = sequence_match.group(1).lower()
    target_segment = user_query[: sequence_match.start()].strip(" ,.")
    anchor_segment = user_query[sequence_match.end() :].strip(" ,.")
    if not target_segment or not anchor_segment:
        return None

    target_hint = _extract_event_hint(target_segment)
    anchor_hint = _extract_event_hint(anchor_segment)
    if target_hint is None or anchor_hint is None:
        return None

    if target_hint.get("event_type") is None or anchor_hint.get("event_type") is None:
        return None

    return {
        "relation": relation,
        "target": target_hint,
        "anchor": anchor_hint,
    }


def _extract_event_hint(user_query: str) -> dict[str, Any] | None:
    lower_query = user_query.lower()
    relation = _extract_relation_hint(user_query)
    anchor_frame = _extract_frame_hint(user_query) if relation is not None else None
    period = _extract_period_hint(user_query)
    pitch_zone = _extract_pitch_zone_hint(user_query)
    phase = _extract_phase_hint(user_query)

    for event_pattern in EVENT_PATTERNS:
        if re.search(event_pattern["pattern"], lower_query, flags=re.IGNORECASE):
            order = _extract_order_hint(user_query) or "first"
            occurrence = _extract_occurrence_hint(user_query) or 1
            if order == "last" and _extract_occurrence_hint(user_query) is None:
                occurrence = 1

            hint: dict[str, Any] = {
                "event_type": event_pattern["event_type"],
                "team": _extract_team_hint(user_query),
                "occurrence": occurrence,
                "order": order,
                "relation": relation or "exact",
                "anchor_frame": anchor_frame,
                "period": period,
                "pitch_zone": pitch_zone,
                "phase": phase,
            }
            if event_pattern["subtype_contains"]:
                hint["subtype_contains"] = event_pattern["subtype_contains"]
            return hint

    if period is not None or pitch_zone is not None or phase is not None:
        return {
            "event_type": None,
            "team": _extract_team_hint(user_query),
            "occurrence": 1,
            "order": "first",
            "relation": relation or "exact",
            "anchor_frame": anchor_frame,
            "period": period,
            "pitch_zone": pitch_zone,
            "phase": phase,
        }

    return None


def _resolve_aggregate_query(user_query: str) -> dict[str, Any] | None:
    aggregate_intent = _extract_aggregate_intent(user_query)
    if aggregate_intent is None:
        return None

    event_hint = _extract_event_hint(user_query) or {}
    period = _extract_period_hint(user_query)
    pitch_zone = _extract_pitch_zone_hint(user_query)
    phase = _extract_phase_hint(user_query)

    query_filters = {
        "event_type": event_hint.get("event_type"),
        "team": event_hint.get("team"),
        "subtype_contains": event_hint.get("subtype_contains"),
        "relation": event_hint.get("relation", "exact"),
        "anchor_frame": event_hint.get("anchor_frame"),
        "period": period if period is not None else event_hint.get("period"),
        "pitch_zone": pitch_zone if pitch_zone is not None else event_hint.get("pitch_zone"),
        "phase": phase if phase is not None else event_hint.get("phase"),
    }

    if aggregate_intent == "count":
        total_count = count_events(**query_filters)
        return {
            "coordinates": {},
            "sequence": None,
            "context": {
                "query": user_query,
                "frame": query_filters["anchor_frame"],
                "event": None,
                "mode": "aggregate",
                "aggregate": {
                    "query_type": "count",
                    "count": total_count,
                    "filters": query_filters,
                },
            },
        }

    events = list_events(**query_filters)
    return {
        "coordinates": {},
        "sequence": None,
        "context": {
            "query": user_query,
            "frame": query_filters["anchor_frame"],
            "event": None,
            "mode": "aggregate",
            "aggregate": {
                "query_type": "list",
                "count": len(events),
                "events": events,
                "filters": query_filters,
            },
        },
    }


def _build_user_content(user_query: str) -> str:
    user_content = user_query.strip()
    frame_hint = _extract_frame_hint(user_query)
    event_hint = _extract_event_hint(user_query)

    hint_lines: list[str] = []
    if frame_hint is not None:
        hint_lines.append(
            "Resolved tool argument hint: if you need direct tracking data, "
            f"call get_tracking_frame with frame={frame_hint} as a JSON integer."
        )

    if event_hint is not None:
        event_parts = [f'event_type="{event_hint["event_type"]}"']
        if event_hint.get("team"):
            event_parts.append(f'team="{event_hint["team"]}"')
        if event_hint.get("subtype_contains"):
            event_parts.append(f'subtype_contains="{event_hint["subtype_contains"]}"')
        event_parts.append(f'occurrence={event_hint["occurrence"]}')
        event_parts.append(f'order="{event_hint["order"]}"')
        event_parts.append(f'relation="{event_hint["relation"]}"')
        if event_hint.get("anchor_frame") is not None:
            event_parts.append(f'anchor_frame={event_hint["anchor_frame"]}')
        if event_hint.get("period") is not None:
            event_parts.append(f'period={event_hint["period"]}')
        if event_hint.get("pitch_zone") is not None:
            event_parts.append(f'pitch_zone="{event_hint["pitch_zone"]}"')
        if event_hint.get("phase") is not None:
            event_parts.append(f'phase="{event_hint["phase"]}"')
        hint_lines.append(
            "Resolved event hint: if you need an event lookup first, "
            f"call find_event with {', '.join(event_parts)}."
        )

    if not hint_lines:
        return user_content

    return f"{user_content}\n\n" + "\n".join(hint_lines)


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set. Add it to your .env file.")
    return Groq(api_key=api_key)


def _execute_tool_call(tool_call: Any) -> tuple[str, Any]:
    function_name = tool_call.function.name
    if function_name not in AVAILABLE_FUNCTIONS:
        raise ValueError(f"Unsupported tool call: {function_name}")

    function_args = json.loads(tool_call.function.arguments or "{}")
    return function_name, AVAILABLE_FUNCTIONS[function_name](**function_args)


def _serialize_tool_result(function_name: str, function_response: Any) -> str:
    return json.dumps(function_response)


def route_analysis_query(user_query: str) -> dict[str, Any]:
    if not user_query or not user_query.strip():
        raise ValueError("user_query must be a non-empty string.")

    aggregate_result = _resolve_aggregate_query(user_query)
    if aggregate_result is not None:
        return aggregate_result

    frame_hint = _extract_frame_hint(user_query)
    event_hint = _extract_event_hint(user_query)
    metric_hint = _extract_metric_hint(user_query)
    sequence_hint = _extract_sequence_event_query(user_query)
    if frame_hint is not None and (event_hint is None or event_hint.get("event_type") is None):
        tracking_result = get_tracking_frame(frame_hint)
        metrics_result: dict[str, Any] | None = None
        if metric_hint is not None:
            metrics_result = get_frame_team_metrics(frame=frame_hint, team=metric_hint.get("team"))
            if metrics_result:
                metrics_result["requested_metric"] = metric_hint["metric"]

        return {
            "coordinates": tracking_result,
            "sequence": None,
            "context": {
                "query": user_query,
                "frame": frame_hint,
                "event": None,
                "metrics": metrics_result,
                "mode": "frame",
            },
        }

    if sequence_hint is not None:
        anchor_hint = dict(sequence_hint["anchor"])
        target_hint = dict(sequence_hint["target"])
        anchor_event = find_event(
            event_type=anchor_hint["event_type"],
            team=anchor_hint.get("team"),
            subtype_contains=anchor_hint.get("subtype_contains"),
            occurrence=anchor_hint.get("occurrence", 1),
            order=anchor_hint.get("order", "first"),
            relation=anchor_hint.get("relation", "exact"),
            anchor_frame=anchor_hint.get("anchor_frame"),
            period=anchor_hint.get("period"),
            pitch_zone=anchor_hint.get("pitch_zone"),
            phase=anchor_hint.get("phase"),
        )
        target_event = find_event(
            event_type=target_hint["event_type"],
            team=target_hint.get("team"),
            subtype_contains=target_hint.get("subtype_contains"),
            occurrence=target_hint.get("occurrence", 1),
            order=target_hint.get("order", "first"),
            relation=sequence_hint["relation"],
            anchor_frame=int(anchor_event["frame"]),
            period=target_hint.get("period"),
            pitch_zone=target_hint.get("pitch_zone"),
            phase=target_hint.get("phase"),
        )
        resolved_frame = int(target_event["frame"])
        tracking_result = get_tracking_frame(resolved_frame)
        tracking_sequence = get_event_tracking_window(event_frame=resolved_frame)
        metrics_result: dict[str, Any] | None = None
        if metric_hint is not None:
            metrics_result = get_frame_team_metrics(frame=resolved_frame, team=metric_hint.get("team"))
            if metrics_result:
                metrics_result["requested_metric"] = metric_hint["metric"]

        return {
            "coordinates": tracking_result,
            "sequence": tracking_sequence,
            "context": {
                "query": user_query,
                "frame": resolved_frame,
                "event": target_event,
                "anchor_event": anchor_event,
                "metrics": metrics_result,
                "mode": "sequence_event",
            },
        }

    user_content = _build_user_content(user_query)

    client = _get_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    resolved_event: dict[str, Any] | None = None
    resolved_frame: int | None = frame_hint
    tracking_sequence: dict[str, Any] | None = None

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            parallel_tool_calls=False,
            temperature=0,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls or []
        messages.append(response_message.model_dump(exclude_none=True))

        if not tool_calls:
            raise RuntimeError("The model did not request a database tool call.")

        tracking_result: dict[str, dict[str, float | int | None]] | None = None
        for tool_call in tool_calls:
            function_name, function_response = _execute_tool_call(tool_call)

            if function_name == "find_event":
                resolved_event = function_response
                resolved_frame = int(function_response["frame"])

            if function_name == "get_tracking_frame":
                tracking_result = function_response
                if resolved_frame is None:
                    resolved_frame = json.loads(tool_call.function.arguments or "{}").get("frame")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": _serialize_tool_result(function_name, function_response),
                }
            )

        if tracking_result is not None:
            if resolved_event is not None and resolved_frame is not None:
                tracking_sequence = get_event_tracking_window(event_frame=resolved_frame)

            metrics_result: dict[str, Any] | None = None
            if resolved_frame is not None and metric_hint is not None:
                metrics_result = get_frame_team_metrics(frame=resolved_frame, team=metric_hint.get("team"))
                if metrics_result:
                    metrics_result["requested_metric"] = metric_hint["metric"]

            return {
                "coordinates": tracking_result,
                "sequence": tracking_sequence,
                "context": {
                    "query": user_query,
                    "frame": resolved_frame,
                    "event": resolved_event,
                    "metrics": metrics_result,
                    "mode": "event" if resolved_event is not None else "frame",
                },
            }

    raise RuntimeError("Max tool iterations reached before resolving tracking coordinates.")


def route_tracking_query(user_query: str) -> dict[str, dict[str, float | int | None]]:
    return route_analysis_query(user_query)["coordinates"]


if __name__ == "__main__":
    sample_query = "Show me the away team's last corner before minute 70"
    result = route_analysis_query(sample_query)
    print(json.dumps(result, indent=2))
