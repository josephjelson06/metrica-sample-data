from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from backend.core.llm_router import route_analysis_query


app = FastAPI()


@dataclass
class ConversationContext:
    """Persisted per WebSocket connection — carries forward between queries."""
    current_team: str | None = None
    current_period: int | None = None
    current_mode: str | None = None
    start_minute: float | None = None
    end_minute: float | None = None
    last_event_type: str | None = None
    turn_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    def update_from_result(self, result: dict[str, Any]) -> None:
        ctx = result.get("context", {})
        mode = ctx.get("mode")
        if mode:
            self.current_mode = mode

        # Carry forward team hint from results that know it
        team_from_network = result.get("pass_network", {})
        if isinstance(team_from_network, dict) and team_from_network.get("team"):
            self.current_team = team_from_network["team"]

        phys = result.get("physicality", {})
        if isinstance(phys, dict) and phys.get("team"):
            self.current_team = phys["team"]

        sonars = result.get("pass_sonars", {})
        if isinstance(sonars, dict) and sonars.get("team"):
            self.current_team = sonars["team"]

        orientation = result.get("orientation", {})
        if isinstance(orientation, dict) and orientation.get("team"):
            self.current_team = orientation["team"]

        # Extract period if context includes it
        if ctx.get("period"):
            self.current_period = ctx["period"]

        # Record history turn
        self.turn_count += 1
        summary = ctx.get("explanation", ctx.get("query", ""))[:120]
        self.history.append({
            "turn": self.turn_count,
            "query": ctx.get("query", ""),
            "mode": mode,
            "summary": summary,
        })
        # Keep only last 8 turns
        if len(self.history) > 8:
            self.history = self.history[-8:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_team": self.current_team,
            "current_period": self.current_period,
            "current_mode": self.current_mode,
            "start_minute": self.start_minute,
            "end_minute": self.end_minute,
            "turn_count": self.turn_count,
            "history": self.history,
        }


def _extract_query(message_text: str) -> str:
    try:
        payload = json.loads(message_text)
    except json.JSONDecodeError:
        payload = message_text

    if isinstance(payload, str):
        query = payload
    elif isinstance(payload, dict):
        query = payload.get("query", "")
    else:
        query = ""

    query = str(query).strip()
    if not query:
        raise ValueError("WebSocket message must contain a non-empty query.")

    return query


def _build_render_message(
    analysis_result: dict[str, Any],
    conversation_ctx: ConversationContext,
) -> dict[str, Any]:
    payload = {
        "view": "PITCH_HOME",
        "data": analysis_result.get("coordinates", {}),
        "sequence": analysis_result.get("sequence"),
        "context": analysis_result.get("context", {}),
        "conversation_context": conversation_ctx.to_dict(),
    }

    # Pass through all analytical dashboard payloads
    for key in [
        "pass_network", "pass_sonars", "physicality",
        "auto_insights", "set_piece_analysis", "orientation",
    ]:
        if key in analysis_result:
            payload[key] = analysis_result[key]

    # Include follow-up suggestions if the result provides them
    if "follow_up_suggestions" in analysis_result:
        payload["follow_up_suggestions"] = analysis_result["follow_up_suggestions"]

    return {
        "type": "DATA_RENDER",
        "payload": payload,
    }


@app.get("/")
async def index() -> JSONResponse:
    return JSONResponse(
        {
            "service": "football-intelligence-backend",
            "status": "ok",
            "websocket": "/ws/analysis",
        }
    )


@app.websocket("/ws/analysis")
async def analysis_socket(websocket: WebSocket) -> None:
    await websocket.accept()

    # One ConversationContext per WebSocket connection — lives for the session
    conv_ctx = ConversationContext()

    try:
        while True:
            message_text = await websocket.receive_text()
            try:
                query = _extract_query(message_text)
                # Pass conversation context into the router so it can resolve
                # vague follow-up phrases (e.g. "same for away team")
                analysis_result = await asyncio.to_thread(
                    route_analysis_query, query, conv_ctx.to_dict()
                )
                conv_ctx.update_from_result(analysis_result)
                await websocket.send_json(
                    _build_render_message(analysis_result, conv_ctx)
                )
            except Exception as exc:
                await websocket.send_json(
                    {
                        "type": "ERROR",
                        "payload": {"message": str(exc)},
                    }
                )
    except WebSocketDisconnect:
        return
