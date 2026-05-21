from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from core.llm_router import route_tracking_query


app = FastAPI()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_INDEX = PROJECT_ROOT / "static" / "index.html"


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


def _build_render_message(coordinates: dict[str, dict[str, float | int | None]]) -> dict[str, Any]:
    return {
        "type": "DATA_RENDER",
        "payload": {
            "view": "PITCH_HOME",
            "data": coordinates,
        },
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_INDEX)


@app.websocket("/ws/analysis")
async def analysis_socket(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        while True:
            message_text = await websocket.receive_text()
            try:
                query = _extract_query(message_text)
                coordinates = await asyncio.to_thread(route_tracking_query, query)
                await websocket.send_json(_build_render_message(coordinates))
            except Exception as exc:
                await websocket.send_json(
                    {
                        "type": "ERROR",
                        "payload": {"message": str(exc)},
                    }
                )
    except WebSocketDisconnect:
        return
