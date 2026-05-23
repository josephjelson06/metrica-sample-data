from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from backend.core.presenter import build_explanation, build_report
from backend.tools.db_engine import (
    compare_sequence_segments,
    compare_frame_structures,
    count_events,
    find_event,
    get_buildup_tracking_window,
    get_event_tracking_window,
    get_team_shape_metrics_for_coordinates,
    get_tracking_frame,
    get_tracking_window,
    get_pass_network,
    get_pass_sonars,
    get_physicality_summary,
    find_dangerous_transitions,
    analyze_set_piece,
    list_events,
    segment_sequence_events,
    summarize_team_event_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_network",
            "description": "Calculate passing network nodes and edges for a given team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (e.g. 'Home' or 'Away')"},
                    "period": {"type": "integer", "description": "Optional period (1 or 2)"}
                },
                "required": ["team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_sonars",
            "description": "Calculate pass sonars (angular pass frequency) for a given team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (e.g. 'Home' or 'Away')"},
                    "period": {"type": "integer", "description": "Optional period (1 or 2)"}
                },
                "required": ["team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_physicality_summary",
            "description": "Calculate total distance, HSR, and sprint distance per player.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name (e.g. 'Home' or 'Away')"},
                    "period": {"type": "integer", "description": "Required period (1 or 2)"}
                },
                "required": ["team", "period"]
            }
        }
    },
]

AVAILABLE_FUNCTIONS = {
    "find_event": find_event,
    "get_tracking_frame": get_tracking_frame,
    "get_pass_network": get_pass_network,
    "get_pass_sonars": get_pass_sonars,
    "get_physicality_summary": get_physicality_summary,
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
    {"pattern": r"\b(ball win|win the ball|ball won)\b", "event_type": "RECOVERY", "subtype_contains": None},
    {"pattern": r"\b(ball loss|lose the ball|lost the ball|turnover)\b", "event_type": "BALL LOST", "subtype_contains": None},
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


def _has_explicit_order_selector(user_query: str) -> bool:
    return re.search(r"\b(first|second|third|fourth|fifth|last|latest|final)\b", user_query, flags=re.IGNORECASE) is not None


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
        (r"\bline height\b|\bline-height\b", "line_height_proxy"),
        (r"\b(unit spacing|team spacing|line spacing)\b", "unit_spacing"),
        (r"\bteam length\b|\blength\b", "team_length_proxy"),
        (r"\bnearest teammate distance\b|\bnearest distance\b", "average_nearest_teammate_distance"),
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


def _extract_report_intent(user_query: str) -> bool:
    return re.search(r"\b(report|summari[sz]e|summary|breakdown|coach note|write up)\b", user_query, flags=re.IGNORECASE) is not None


def _extract_buildup_intent(user_query: str) -> bool:
    return re.search(
        r"\b(buildup|build up|lead[\s-]?up|sequence leading to|lead(?:ing)? to)\b",
        user_query,
        flags=re.IGNORECASE,
    ) is not None


def _extract_transition_intent(user_query: str) -> bool:
    has_transition_phrase = re.search(
        r"\b(transition|counter(?:-|\s)?attack|attack sequence)\b",
        user_query,
        flags=re.IGNORECASE,
    ) is not None
    has_direction_phrase = re.search(r"\b(after|from)\b", user_query, flags=re.IGNORECASE) is not None
    return has_transition_phrase and has_direction_phrase


def _extract_pass_network_intent(user_query: str) -> bool:
    query = user_query.lower()
    return "pass network" in query or "passing network" in query or "passing web" in query

def _extract_pass_sonars_intent(user_query: str) -> bool:
    query = user_query.lower()
    return "sonar" in query or "passing flow" in query or "pass directions" in query

def _extract_physicality_intent(user_query: str) -> bool:
    query = user_query.lower()
    return "physicality" in query or "work rate" in query or "distance run" in query or "sprint" in query or "hsr" in query

def _extract_pattern_recognition_intent(user_query: str) -> bool:
    query = user_query.lower()
    return "dangerous transition" in query or "auto insight" in query or "pattern" in query or "vulnerability" in query

def _extract_set_piece_intent(user_query: str) -> bool:
    query = user_query.lower()
    return "set piece analysis" in query or "analyze corner" in query or "marking" in query or "free kick structure" in query


def _event_comparison_label(event_pattern: dict[str, Any]) -> str:
    subtype = str(event_pattern.get("subtype_contains") or "").lower()
    event_type = str(event_pattern.get("event_type") or "").lower()
    if "corner" in subtype:
        return "corner"
    if "free kick" in subtype:
        return "free kick"
    if "throw in" in subtype:
        return "throw in"
    if "kick off" in subtype:
        return "kick off"
    if "penalty" in subtype:
        return "penalty"
    if "goal" in subtype:
        return "goal"
    if "saved" in subtype:
        return "saved shot"
    if event_type == "shot":
        return "shot"
    if event_type == "pass":
        return "pass"
    if event_type == "recovery":
        return "recovery"
    if event_type == "card":
        return "card"
    return event_type


def _parse_order_token(token: str) -> tuple[str, int]:
    normalized_token = str(token).strip().lower()
    if normalized_token in {"last", "latest", "final"}:
        return "last", 1
    return "first", ORDINAL_WORDS[normalized_token]


def _extract_same_event_comparison(user_query: str) -> dict[str, Any] | None:
    lower_query = user_query.lower()
    ordinal_matches = re.findall(r"\b(first|second|third|fourth|fifth|last|latest|final)\b", lower_query)
    if len(ordinal_matches) < 2:
        return None

    matched_pattern: dict[str, Any] | None = None
    for event_pattern in EVENT_PATTERNS:
        if re.search(event_pattern["pattern"], lower_query, flags=re.IGNORECASE):
            matched_pattern = event_pattern
            break

    if matched_pattern is None:
        return None

    team = _extract_team_hint(user_query)
    period = _extract_period_hint(user_query)
    pitch_zone = _extract_pitch_zone_hint(user_query)
    phase = _extract_phase_hint(user_query)
    event_label = _event_comparison_label(matched_pattern)

    left_order, left_occurrence = _parse_order_token(ordinal_matches[0])
    right_order, right_occurrence = _parse_order_token(ordinal_matches[1])

    def _build_event_hint(order: str, occurrence: int) -> dict[str, Any]:
        hint: dict[str, Any] = {
            "event_type": matched_pattern["event_type"],
            "team": team,
            "occurrence": occurrence,
            "order": order,
            "relation": "exact",
            "anchor_frame": None,
            "period": period,
            "pitch_zone": pitch_zone,
            "phase": phase,
        }
        if matched_pattern["subtype_contains"]:
            hint["subtype_contains"] = matched_pattern["subtype_contains"]
        return hint

    return {
        "left": {"kind": "event", "hint": _build_event_hint(left_order, left_occurrence), "label": f"{ordinal_matches[0]} {event_label}"},
        "right": {"kind": "event", "hint": _build_event_hint(right_order, right_occurrence), "label": f"{ordinal_matches[1]} {event_label}"},
        "team": team,
    }


def _extract_reference_hint(segment: str) -> dict[str, Any] | None:
    frame_hint = _extract_frame_hint(segment)
    if frame_hint is not None:
        return {"kind": "frame", "frame": frame_hint, "label": segment.strip()}

    event_hint = _extract_event_hint(segment)
    if event_hint is not None and event_hint.get("event_type") is not None:
        return {"kind": "event", "hint": event_hint, "label": segment.strip()}

    return None


def _extract_comparison_query(user_query: str) -> dict[str, Any] | None:
    comparison_match = re.search(r"\bcompar(?:e|ing)\b", user_query, flags=re.IGNORECASE)
    if comparison_match is None:
        return None

    stripped_query = user_query[comparison_match.end() :].strip(" ,.")
    same_event_comparison = _extract_same_event_comparison(stripped_query)
    if same_event_comparison is not None:
        return same_event_comparison

    parts = re.split(r"\band\b", stripped_query, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None

    left_reference = _extract_reference_hint(parts[0].strip(" ,."))
    right_reference = _extract_reference_hint(parts[1].strip(" ,."))
    if left_reference is None or right_reference is None:
        return None

    return {
        "left": left_reference,
        "right": right_reference,
        "team": _extract_team_hint(user_query),
    }


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


def _resolve_reference(reference: dict[str, Any]) -> dict[str, Any]:
    if reference["kind"] == "frame":
        frame = int(reference["frame"])
        return {
            "frame": frame,
            "event": None,
            "coordinates": get_tracking_frame(frame),
            "label": reference.get("label", f"frame {frame}"),
        }

    event_hint = reference["hint"]
    event = find_event(
        event_type=event_hint["event_type"],
        team=event_hint.get("team"),
        subtype_contains=event_hint.get("subtype_contains"),
        occurrence=event_hint.get("occurrence", 1),
        order=event_hint.get("order", "first"),
        relation=event_hint.get("relation", "exact"),
        anchor_frame=event_hint.get("anchor_frame"),
        period=event_hint.get("period"),
        pitch_zone=event_hint.get("pitch_zone"),
        phase=event_hint.get("phase"),
    )
    frame = int(event["frame"])
    return {
        "frame": frame,
        "event": event,
        "coordinates": get_tracking_frame(frame),
        "label": reference.get("label", f"frame {frame}"),
    }


def _extract_event_hint(user_query: str) -> dict[str, Any] | None:
    lower_query = user_query.lower()
    raw_relation = _extract_relation_hint(user_query)
    anchor_frame = _extract_frame_hint(user_query) if raw_relation is not None else None
    relation = raw_relation if anchor_frame is not None else None
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
    if aggregate_intent is None and _extract_report_intent(user_query):
        report_event_hint = _extract_event_hint(user_query) or {}
        if (
            report_event_hint.get("event_type") is not None
            and _extract_frame_hint(user_query) is None
            and _extract_relation_hint(user_query) is None
            and not _has_explicit_order_selector(user_query)
        ):
            aggregate_intent = "list"

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


def _finalize_analysis_result(result: dict[str, Any], wants_report: bool) -> dict[str, Any]:
    context = result["context"]
    sequence = result.get("sequence")

    context["response_contract_version"] = "v1"
    context["query_family"] = str(context.get("mode", "unknown"))
    context["has_event"] = context.get("event") is not None
    context["has_anchor_event"] = context.get("anchor_event") is not None
    context["has_metrics"] = context.get("metrics") is not None
    context["has_sequence"] = bool(sequence)
    context["sequence_type"] = sequence.get("sequence_type") if isinstance(sequence, dict) else None
    context["has_aggregate"] = context.get("aggregate") is not None
    context["has_comparison"] = context.get("comparison") is not None
    if context.get("comparison") is not None:
        context["comparison_kind"] = context["comparison"].get("comparison_kind")
    context["has_pass_network"] = result.get("pass_network") is not None
    context["has_pass_sonars"] = result.get("pass_sonars") is not None
    context["has_physicality"] = result.get("physicality") is not None
    context["has_auto_insights"] = result.get("auto_insights") is not None
    context["has_set_piece_analysis"] = result.get("set_piece_analysis") is not None
    context["has_report"] = wants_report
    context["explanation"] = build_explanation(result)
    context["has_explanation"] = True
    if wants_report:
        context["report"] = build_report(result)
    else:
        context.pop("report", None)
    return result


def route_analysis_query(user_query: str) -> dict[str, Any]:
    if not user_query or not user_query.strip():
        raise ValueError("user_query must be a non-empty string.")

    wants_report = _extract_report_intent(user_query)
    buildup_intent = _extract_buildup_intent(user_query)
    transition_intent = _extract_transition_intent(user_query)
    pass_network_intent = _extract_pass_network_intent(user_query)

    if pass_network_intent:
        team_hint = _extract_team_hint(user_query) or "Home"
        period_hint = _extract_period_hint(user_query)
        network_data = get_pass_network(team=team_hint, period=period_hint)
        result = {
            "coordinates": {},
            "sequence": None,
            "pass_network": network_data,
            "context": {
                "query": user_query,
                "frame": None,
                "event": None,
                "mode": "pass_network",
            },
        }
        return _finalize_analysis_result(result, wants_report)

    pass_sonars_intent = _extract_pass_sonars_intent(user_query)
    if pass_sonars_intent:
        team_hint = _extract_team_hint(user_query) or "Home"
        period_hint = _extract_period_hint(user_query)
        sonars_data = get_pass_sonars(team=team_hint, period=period_hint)
        result = {
            "coordinates": {},
            "sequence": None,
            "pass_sonars": sonars_data,
            "context": {
                "query": user_query,
                "frame": None,
                "event": None,
                "mode": "pass_sonars",
            },
        }
        return _finalize_analysis_result(result, wants_report)
        
    physicality_intent = _extract_physicality_intent(user_query)
    if physicality_intent:
        team_hint = _extract_team_hint(user_query) or "Home"
        period_hint = _extract_period_hint(user_query) or 1
        phys_data = get_physicality_summary(period=period_hint, team=team_hint)
        result = {
            "coordinates": {},
            "sequence": None,
            "physicality": phys_data,
            "context": {
                "query": user_query,
                "frame": None,
                "event": None,
                "mode": "physicality",
            },
        }
        return _finalize_analysis_result(result, wants_report)

    pattern_intent = _extract_pattern_recognition_intent(user_query)
    if pattern_intent:
        team_hint = _extract_team_hint(user_query) or "Home"
        insights = find_dangerous_transitions(team=team_hint)
        result = {
            "coordinates": {},
            "sequence": None,
            "auto_insights": insights,
            "context": {
                "query": user_query,
                "frame": None,
                "event": None,
                "mode": "auto_insights",
            },
        }
        return _finalize_analysis_result(result, wants_report)

    set_piece_intent = _extract_set_piece_intent(user_query)
    if set_piece_intent:
        # Find the specific event they are asking for or just grab the first set piece
        event_hint = _extract_event_hint(user_query)
        team_hint = _extract_team_hint(user_query)
        period_hint = _extract_period_hint(user_query)
        target_events = list_events(event_type="SET PIECE", team=team_hint, period=period_hint, limit=1)
        if target_events:
            analysis = analyze_set_piece(str(target_events[0]["index"]))
            result = {
                "coordinates": analysis["coordinates"],
                "sequence": None,
                "set_piece_analysis": analysis,
                "context": {
                    "query": user_query,
                    "frame": analysis["frame"],
                    "event": analysis["event"],
                    "mode": "set_piece",
                },
            }
            return _finalize_analysis_result(result, wants_report)

    if not buildup_intent and not transition_intent:
        aggregate_result = _resolve_aggregate_query(user_query)
        if aggregate_result is not None:
            return _finalize_analysis_result(aggregate_result, wants_report)

    frame_hint = _extract_frame_hint(user_query)
    event_hint = _extract_event_hint(user_query)
    metric_hint = _extract_metric_hint(user_query)
    comparison_hint = _extract_comparison_query(user_query)
    sequence_hint = _extract_sequence_event_query(user_query)
    if comparison_hint is None and buildup_intent and event_hint is not None and event_hint.get("event_type") is not None:
        resolved_event = find_event(
            event_type=event_hint["event_type"],
            team=event_hint.get("team"),
            subtype_contains=event_hint.get("subtype_contains"),
            occurrence=event_hint.get("occurrence", 1),
            order=event_hint.get("order", "first"),
            relation=event_hint.get("relation", "exact"),
            anchor_frame=event_hint.get("anchor_frame"),
            period=event_hint.get("period"),
            pitch_zone=event_hint.get("pitch_zone"),
            phase=event_hint.get("phase"),
        )
        resolved_frame = int(resolved_event["frame"])
        tracking_result = get_tracking_frame(resolved_frame)
        buildup_sequence = get_buildup_tracking_window(event_frame=resolved_frame)
        sequence_segments: dict[str, Any] | None = None
        if resolved_event.get("team") in {"Home", "Away"}:
            sequence_segments = segment_sequence_events(
                events=buildup_sequence.get("events", []),
                anchor_frame=resolved_frame,
                team=str(resolved_event["team"]),
            )
        metrics_result: dict[str, Any] | None = None
        if metric_hint is not None:
            metrics_result = get_frame_team_metrics(frame=resolved_frame, team=metric_hint.get("team"))
            if metrics_result:
                metrics_result["requested_metric"] = metric_hint["metric"]

        result = {
            "coordinates": tracking_result,
            "sequence": buildup_sequence,
            "context": {
                "query": user_query,
                "frame": resolved_frame,
                "event": resolved_event,
                "metrics": metrics_result,
                "sequence_segments": sequence_segments,
                "mode": "buildup",
            },
        }
        return _finalize_analysis_result(result, wants_report)

    if comparison_hint is None and transition_intent and event_hint is not None and event_hint.get("event_type") is not None:
        resolved_event = find_event(
            event_type=event_hint["event_type"],
            team=event_hint.get("team"),
            subtype_contains=event_hint.get("subtype_contains"),
            occurrence=event_hint.get("occurrence", 1),
            order=event_hint.get("order", "first"),
            relation=event_hint.get("relation", "exact"),
            anchor_frame=event_hint.get("anchor_frame"),
            period=event_hint.get("period"),
            pitch_zone=event_hint.get("pitch_zone"),
            phase=event_hint.get("phase"),
        )
        resolved_frame = int(resolved_event["frame"])
        tracking_result = get_tracking_frame(resolved_frame)
        transition_sequence = get_transition_tracking_window(event_frame=resolved_frame)
        sequence_segments: dict[str, Any] | None = None
        if resolved_event.get("team") in {"Home", "Away"}:
            sequence_segments = segment_sequence_events(
                events=transition_sequence.get("events", []),
                anchor_frame=resolved_frame,
                team=str(resolved_event["team"]),
            )
        metrics_result: dict[str, Any] | None = None
        if metric_hint is not None:
            metrics_result = get_frame_team_metrics(frame=resolved_frame, team=metric_hint.get("team"))
            if metrics_result:
                metrics_result["requested_metric"] = metric_hint["metric"]

        transition_summary: dict[str, Any] | None = None
        if resolved_event.get("team") in {"Home", "Away"}:
            transition_summary = summarize_team_event_chain(
                events=transition_sequence.get("events", []),
                team=str(resolved_event["team"]),
                anchor_frame=resolved_frame,
            )

        result = {
            "coordinates": tracking_result,
            "sequence": transition_sequence,
            "context": {
                "query": user_query,
                "frame": resolved_frame,
                "event": resolved_event,
                "metrics": metrics_result,
                "sequence_segments": sequence_segments,
                "transition_summary": transition_summary,
                "mode": "transition",
            },
        }
        return _finalize_analysis_result(result, wants_report)

    if comparison_hint is not None:
        left_reference = _resolve_reference(comparison_hint["left"])
        right_reference = _resolve_reference(comparison_hint["right"])
        comparison_team = comparison_hint.get("team")
        left_event = left_reference.get("event")
        right_event = right_reference.get("event")
        if comparison_team is None:
            if (
                left_event is not None
                and right_event is not None
                and left_event.get("team") == right_event.get("team")
                and left_event.get("team") in {"Home", "Away"}
            ):
                comparison_team = str(left_event["team"])

        sequence_comparison: dict[str, Any] | None = None
        if buildup_intent or transition_intent:
            if (
                left_event is not None
                and right_event is not None
                and left_event.get("team") in {"Home", "Away"}
                and right_event.get("team") in {"Home", "Away"}
            ):
                if buildup_intent:
                    left_sequence = get_buildup_tracking_window(event_frame=int(left_reference["frame"]))
                    right_sequence = get_buildup_tracking_window(event_frame=int(right_reference["frame"]))
                else:
                    left_sequence = get_transition_tracking_window(event_frame=int(left_reference["frame"]))
                    right_sequence = get_transition_tracking_window(event_frame=int(right_reference["frame"]))

                left_segments = segment_sequence_events(
                    events=left_sequence.get("events", []),
                    anchor_frame=int(left_reference["frame"]),
                    team=str(left_event["team"]),
                )
                right_segments = segment_sequence_events(
                    events=right_sequence.get("events", []),
                    anchor_frame=int(right_reference["frame"]),
                    team=str(right_event["team"]),
                )
                sequence_comparison = compare_sequence_segments(left_segments, right_segments)

        metrics_comparison = compare_frame_structures(
            start_frame=int(left_reference["frame"]),
            end_frame=int(right_reference["frame"]),
            team=comparison_team,
        )
        result = {
            "coordinates": right_reference["coordinates"],
            "sequence": None,
            "context": {
                "query": user_query,
                "frame": right_reference["frame"],
                "event": right_reference.get("event"),
                "mode": "comparison",
                "comparison": {
                    "team": comparison_team,
                    "left_label": left_reference["label"],
                    "right_label": right_reference["label"],
                    "left_frame": left_reference["frame"],
                    "right_frame": right_reference["frame"],
                    "left_event": left_event,
                    "right_event": right_event,
                    "metrics_comparison": metrics_comparison,
                    "sequence_comparison": sequence_comparison,
                    "comparison_kind": "buildup_sequence" if buildup_intent else ("transition_sequence" if transition_intent else "moment"),
                },
            },
        }
        return _finalize_analysis_result(result, wants_report)

    if frame_hint is not None and (event_hint is None or event_hint.get("event_type") is None):
        tracking_result = get_tracking_frame(frame_hint)
        metrics_result: dict[str, Any] | None = None
        if metric_hint is not None:
            metrics_result = get_frame_team_metrics(frame=frame_hint, team=metric_hint.get("team"))
            if metrics_result:
                metrics_result["requested_metric"] = metric_hint["metric"]

        result = {
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
        return _finalize_analysis_result(result, wants_report)

    if sequence_hint is None and event_hint is not None and event_hint.get("event_type") is not None:
        resolved_event = find_event(
            event_type=event_hint["event_type"],
            team=event_hint.get("team"),
            subtype_contains=event_hint.get("subtype_contains"),
            occurrence=event_hint.get("occurrence", 1),
            order=event_hint.get("order", "first"),
            relation=event_hint.get("relation", "exact"),
            anchor_frame=event_hint.get("anchor_frame"),
            period=event_hint.get("period"),
            pitch_zone=event_hint.get("pitch_zone"),
            phase=event_hint.get("phase"),
        )
        resolved_frame = int(resolved_event["frame"])
        tracking_result = get_tracking_frame(resolved_frame)
        tracking_sequence = get_event_tracking_window(event_frame=resolved_frame)
        metrics_result: dict[str, Any] | None = None
        if metric_hint is not None:
            metrics_result = get_frame_team_metrics(frame=resolved_frame, team=metric_hint.get("team"))
            if metrics_result:
                metrics_result["requested_metric"] = metric_hint["metric"]

        result = {
            "coordinates": tracking_result,
            "sequence": tracking_sequence,
            "context": {
                "query": user_query,
                "frame": resolved_frame,
                "event": resolved_event,
                "metrics": metrics_result,
                "mode": "event",
            },
        }
        return _finalize_analysis_result(result, wants_report)

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

        result = {
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
        return _finalize_analysis_result(result, wants_report)

    user_content = _build_user_content(user_query)

    client = _get_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    resolved_event: dict[str, Any] | None = None
    resolved_frame: int | None = frame_hint
    tracking_sequence: dict[str, Any] | None = None
    synthesis_payloads: dict[str, Any] = {}

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
            if synthesis_payloads:
                result = {
                    "coordinates": {},
                    "sequence": tracking_sequence,
                    "pass_network": synthesis_payloads.get("get_pass_network"),
                    "pass_sonars": synthesis_payloads.get("get_pass_sonars"),
                    "physicality": synthesis_payloads.get("get_physicality_summary"),
                    "context": {
                        "query": user_query,
                        "frame": resolved_frame,
                        "event": resolved_event,
                        "mode": "synthesis",
                        "explanation": response_message.content,
                    },
                }
                return _finalize_analysis_result(result, wants_report)
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
                    
            if function_name in ["get_pass_network", "get_pass_sonars", "get_physicality_summary"]:
                synthesis_payloads[function_name] = function_response

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": _serialize_tool_result(function_name, function_response),
                }
            )

        if tracking_result is not None and not synthesis_payloads:
            if resolved_event is not None and resolved_frame is not None:
                tracking_sequence = get_event_tracking_window(event_frame=resolved_frame)

            metrics_result: dict[str, Any] | None = None
            if resolved_frame is not None and metric_hint is not None:
                metrics_result = get_frame_team_metrics(frame=resolved_frame, team=metric_hint.get("team"))
                if metrics_result:
                    metrics_result["requested_metric"] = metric_hint["metric"]

            result = {
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
            return _finalize_analysis_result(result, wants_report)

    raise RuntimeError("Max tool iterations reached before resolving tracking coordinates.")


def route_tracking_query(user_query: str) -> dict[str, dict[str, float | int | None]]:
    return route_analysis_query(user_query)["coordinates"]


if __name__ == "__main__":
    sample_query = "Show me the away team's last corner before minute 70"
    result = route_analysis_query(sample_query)
    print(json.dumps(result, indent=2))
