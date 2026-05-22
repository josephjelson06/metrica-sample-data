from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from tools.db_engine import find_event, get_event_tracking_window, get_tracking_frame


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
    {"pattern": r"\bcorner(?: kick)?\b", "event_type": "SET PIECE", "subtype_contains": "CORNER KICK"},
    {"pattern": r"\bfree kick\b", "event_type": "SET PIECE", "subtype_contains": "FREE KICK"},
    {"pattern": r"\bkick[\s-]?off\b", "event_type": "SET PIECE", "subtype_contains": "KICK OFF"},
    {"pattern": r"\bthrow[\s-]?in\b", "event_type": "SET PIECE", "subtype_contains": "THROW IN"},
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
    for word, value in ORDINAL_WORDS.items():
        if re.search(rf"\b{word}\b", lower_query):
            return value

    ordinal_number_match = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", user_query, flags=re.IGNORECASE)
    if ordinal_number_match:
        return int(ordinal_number_match.group(1))

    return None


def _extract_order_hint(user_query: str) -> str | None:
    if re.search(r"\b(last|latest|final)\b", user_query, flags=re.IGNORECASE):
        return "last"

    if _extract_occurrence_hint(user_query) is not None or re.search(r"\bfirst\b", user_query, flags=re.IGNORECASE):
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


def _extract_event_hint(user_query: str) -> dict[str, Any] | None:
    lower_query = user_query.lower()
    relation = _extract_relation_hint(user_query)
    anchor_frame = _extract_frame_hint(user_query) if relation is not None else None

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
            }
            if event_pattern["subtype_contains"]:
                hint["subtype_contains"] = event_pattern["subtype_contains"]
            return hint

    return None


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

    user_content = _build_user_content(user_query)

    client = _get_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    resolved_event: dict[str, Any] | None = None
    resolved_frame: int | None = _extract_frame_hint(user_query)
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

            return {
                "coordinates": tracking_result,
                "sequence": tracking_sequence,
                "context": {
                    "query": user_query,
                    "frame": resolved_frame,
                    "event": resolved_event,
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
