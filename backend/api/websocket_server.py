from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from backend.core.llm_router import route_analysis_query


app = FastAPI()


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


def _build_render_message(analysis_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "DATA_RENDER",
        "payload": {
            "view": "PITCH_HOME",
            "data": analysis_result["coordinates"],
            "sequence": analysis_result.get("sequence"),
            "context": analysis_result["context"],
        },
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

    try:
        while True:
            message_text = await websocket.receive_text()
            try:
                query = _extract_query(message_text)
                analysis_result = await asyncio.to_thread(route_analysis_query, query)
                await websocket.send_json(_build_render_message(analysis_result))
            except Exception as exc:
                await websocket.send_json(
                    {
                        "type": "ERROR",
                        "payload": {"message": str(exc)},
                    }
                )
    except WebSocketDisconnect:
        return
