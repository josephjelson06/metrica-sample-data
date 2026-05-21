from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from tools.db_engine import get_player_coordinates_for_frame


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = "llama-3.3-70b-versatile"
FRAMES_PER_SECOND = 25

SYSTEM_PROMPT = f"""
You route football tracking queries to a local database tool.
Always call the get_player_coordinates_for_frame tool for position requests.

Rules:
- If the user gives a minute value, convert it to a frame number using:
  frame = minute * 60 * {FRAMES_PER_SECOND}
- Return the frame number as an integer.
- Tool arguments must be valid JSON values.
- Never send arithmetic expressions like 5 * 60 * 25 as tool arguments.
- If the user already gives a frame number, use it directly.
- Only provide the tool argument needed for the database lookup.
""".strip()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_player_coordinates_for_frame",
            "description": (
                "Look up all available x and y coordinates for players and the ball "
                "for one exact tracking frame."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_frame": {
                        "type": "integer",
                        "description": (
                            "The exact tracking frame number. "
                            "If the user mentions a minute, convert it using "
                            "minute * 60 * 25 before calling the tool."
                        ),
                    }
                },
                "required": ["target_frame"],
            },
        },
    }
]

AVAILABLE_FUNCTIONS = {
    "get_player_coordinates_for_frame": get_player_coordinates_for_frame,
}


def _extract_frame_hint(user_query: str) -> int | None:
    minute_match = re.search(r"\bminute\s+(\d+(?:\.\d+)?)\b", user_query, flags=re.IGNORECASE)
    if minute_match:
        minute_value = float(minute_match.group(1))
        return int(round(minute_value * 60 * FRAMES_PER_SECOND))

    frame_match = re.search(r"\bframe\s+(\d+)\b", user_query, flags=re.IGNORECASE)
    if frame_match:
        return int(frame_match.group(1))

    return None


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set. Add it to your .env file.")
    return Groq(api_key=api_key)


def _execute_tool_call(tool_call: Any) -> dict[str, dict[str, float | int | None]]:
    function_name = tool_call.function.name
    if function_name not in AVAILABLE_FUNCTIONS:
        raise ValueError(f"Unsupported tool call: {function_name}")

    function_args = json.loads(tool_call.function.arguments or "{}")
    return AVAILABLE_FUNCTIONS[function_name](**function_args)


def route_tracking_query(user_query: str) -> dict[str, dict[str, float | int | None]]:
    if not user_query or not user_query.strip():
        raise ValueError("user_query must be a non-empty string.")

    frame_hint = _extract_frame_hint(user_query)
    user_content = user_query.strip()
    if frame_hint is not None:
        user_content = (
            f"{user_content}\n\n"
            f"Resolved tool argument hint: call get_player_coordinates_for_frame "
            f"with target_frame={frame_hint} as a JSON integer."
        )

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0,
    )

    response_message = response.choices[0].message
    if not response_message.tool_calls:
        raise RuntimeError("The model did not request a database tool call.")

    # We only need the database result, so execute the first tool call and return its dictionary.
    return _execute_tool_call(response_message.tool_calls[0])


if __name__ == "__main__":
    sample_query = "Show me the player positions at minute 2"
    result = route_tracking_query(sample_query)
    print(result)
