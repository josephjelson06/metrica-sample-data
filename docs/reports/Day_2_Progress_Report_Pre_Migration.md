# Day 2 Progress Report (Pre-Migration Checkpoint)

This document summarizes the Day 2 work completed before moving to a larger frontend migration.

The main goal of Day 2 was to move the system from simple frame-based coordinate lookup to event-aware tactical lookup.

## 1. Main Day 2 Goal

At the end of Day 1, the system could do this well:

- take a natural language prompt
- convert it into a frame-based query
- fetch tracking coordinates
- return those coordinates through the websocket
- render them on the pitch

That solved the data-access problem, but the system still had no tactical event understanding.

Day 2 added that missing layer.

Now the assistant can handle questions like:

- `Show me the away team's first shot`
- `Show me the player positions when the first goal happened`
- `Show me the home team's first saved shot`
- `Show me the last goal before 70:00`

## 2. Event Query Layer Added

The biggest backend improvement was in:

- [db_engine.py](C:/Users/josep/OneDrive/Desktop/sample-data/tools/db_engine.py)

### New capability added

We added a richer event lookup function:

- `find_event(...)`

This function queries:

- [metrica_events.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_events.parquet)

and returns event metadata such as:

- team
- type
- subtype
- period
- start frame
- start time
- end frame
- from player
- to player
- pitch coordinates

### Compatibility helper retained

We also kept:

- `find_event_frame(...)`

as a simpler compatibility wrapper that returns only the event frame when needed.

### Tracking lookup remains available

The tracking lookup function remains:

- `get_tracking_frame(frame)`

which returns the player and ball coordinates from:

- [metrica_tracking.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_tracking.parquet)

## 3. Two-Step Tool Chain Implemented

Day 2 introduced the real sequential tool flow:

1. find the event
2. get the frame from that event
3. fetch tracking coordinates for that frame

This is the key architectural upgrade from Day 1.

Example:

- user asks: `Show me the away team's first shot`
- system finds the first matching event in the events parquet
- system gets the event frame
- system fetches player and ball coordinates from the tracking parquet
- websocket sends the final render payload to the frontend

## 4. Groq Router Upgraded

The main Day 2 orchestration work was done in:

- [llm_router.py](C:/Users/josep/OneDrive/Desktop/sample-data/core/llm_router.py)

### Router changes completed

The Groq router was upgraded from a one-step tracking call into a multi-step local tool loop.

It now supports:

- `find_event(...)`
- `get_tracking_frame(...)`

and can chain them together automatically.

### Router now returns structured output

Instead of returning only coordinates, the router now returns:

- `coordinates`
- `context`

The `context` object includes:

- original user query
- resolved frame
- matched event metadata
- whether the query was resolved as:
  - direct frame lookup
  - event-based lookup

## 5. Query Understanding Improved

The local parsing layer in the router was expanded so Groq gets stronger hints before tool-calling.

### Time understanding added

The router now understands:

- `minute 5`
- `2:30`
- `70:00`
- `15th minute`
- `frame 12000`

### Order and occurrence understanding added

The router now supports:

- `first`
- `second`
- `third`
- `fourth`
- `fifth`
- `last`
- `latest`
- `final`

### Relative event queries added

The router now supports:

- `before`
- `after`
- `around`
- `near`
- `closest`

Examples:

- `Show me the last goal before 70:00`
- `Show me the first pass after 2:30`
- `Show me the corner around minute 15`

### Event phrase understanding added

The router now recognizes common football event language such as:

- `goal`
- `saved shot`
- `shot`
- `corner`
- `free kick`
- `kick off`
- `throw in`
- `penalty`
- `pass`
- `recovery`
- `interception`
- `yellow card`
- `ball out`
- `offside`

## 6. WebSocket Payload Improved

The websocket server was updated in:

- [websocket_server.py](C:/Users/josep/OneDrive/Desktop/sample-data/api/websocket_server.py)

### Day 1 payload

Previously the server returned only:

- coordinates data

### Day 2 payload

Now the websocket payload includes:

- `view`
- `data`
- `context`

This allows the frontend to render not only player positions, but also event information about what was found.

## 7. Frontend Updated with Event Context

The tiny frontend in:

- [index.html](C:/Users/josep/OneDrive/Desktop/sample-data/static/index.html)

was updated to show more than just dots on the pitch.

### Frontend improvements completed

- added an event context banner above the pitch
- shows resolved frame information
- shows event type and subtype when available
- shows event time
- shows player source information such as `From`
- still renders all players and the ball on the pitch
- still shows raw JSON for debugging and explanation

### Example visible improvement

Instead of only saying:

- `27 tracked entities rendered`

the frontend can now show something like:

- `Away SET PIECE / CORNER KICK found at frame 86036`

This makes the demo much easier to explain to others.

## 8. End-to-End Testing Completed

Day 2 work was tested at multiple layers.

### Direct DuckDB tests

Verified event lookup examples such as:

- first away shot
- first goal
- first corner

### Direct router tests

Verified queries like:

- `Show me the positions at 2:30`
- `Show me the away team's second corner`
- `Show me the home team's first saved shot`
- `Show me the last goal before 70:00`
- `Show me the first pass after 2:30`
- `Show me the corner around minute 15`

### WebSocket end-to-end tests

Verified websocket responses still return a valid `DATA_RENDER` payload, now with both:

- coordinate data
- event context

## 9. Files Updated During Day 2

Core source files updated:

- [db_engine.py](C:/Users/josep/OneDrive/Desktop/sample-data/tools/db_engine.py)
- [llm_router.py](C:/Users/josep/OneDrive/Desktop/sample-data/core/llm_router.py)
- [websocket_server.py](C:/Users/josep/OneDrive/Desktop/sample-data/api/websocket_server.py)
- [index.html](C:/Users/josep/OneDrive/Desktop/sample-data/static/index.html)

Relevant supporting data already used:

- [metrica_events.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_events.parquet)
- [metrica_tracking.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_tracking.parquet)

## 10. Why This Matters

This Day 2 checkpoint is important because the system is no longer a simple coordinate fetcher.

It is now:

- event-aware
- context-aware
- frame-aware
- ready for richer tactical queries

This is the point where the assistant starts becoming genuinely useful for football analysis instead of only functioning as a data demo.

## 11. Pre-Migration Conclusion

Before migrating to a bigger frontend stack, the backend is now strong enough to support:

- natural language event queries
- time-relative queries
- sequential tool chaining
- structured event context
- websocket-driven tactical rendering

That makes this a good checkpoint to commit before moving toward a more serious frontend architecture such as:

- Next.js
- TypeScript
- canvas-based rendering
- smoother animation and interaction

This concludes the Day 2 pre-migration checkpoint.
