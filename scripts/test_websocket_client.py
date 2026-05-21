from __future__ import annotations

import asyncio

import websockets


async def main() -> None:
    uri = "ws://localhost:8000/ws/analysis"
    async with websockets.connect(uri) as websocket:
        await websocket.send("Give me the coordinates for minute 5")
        response = await websocket.recv()
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
