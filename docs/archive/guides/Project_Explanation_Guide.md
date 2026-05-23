# Project Explanation Guide

This file is a speaking guide for explaining the project to a group of young people.

The goal is not only to say what each file does, but also to explain why we built it this way.

You can use this document as:

- a presentation outline
- a teaching guide
- a demo walkthrough
- a cheat sheet while answering questions

Related deeper strategy guide:

- [Football Intelligence System Design Map](C:/Users/josep/OneDrive/Desktop/sample-data/docs/guides/Football_Intelligence_System_Design_Map.md)

## 1. The Simple Big Picture

Before talking about files, start with the problem in one simple sentence:

> We built a small AI football analysis system that can understand natural language, find the right moment in a match, fetch the player positions, and show them on a pitch.

Then explain the pipeline in a very simple sequence:

1. We have football match data.
2. A user asks a question in normal English.
3. The AI understands what moment or event the user is asking about.
4. The backend finds the correct frame in the match data.
5. The backend fetches player and ball positions for that frame.
6. The frontend shows those positions on a football pitch.

If you want an even simpler analogy, say:

> Think of it like Google Maps for a football match, but controlled with natural language.

## 2. Best Way to Start the Presentation

A good opening is:

> This project started with raw football match data in CSV files. Those files are useful, but hard to search quickly and hard to explain visually. So we built a system that turns that raw data into something an AI can query fast, and something a frontend can display clearly.

Then explain the three layers:

- `Data layer`
  - raw CSV and optimized Parquet files
- `Backend intelligence layer`
  - DuckDB, Groq, routing, WebSocket API
- `Frontend layer`
  - simple browser pitch view

That gives your audience a mental map before you go file by file.

## 3. What the Data Is

The core raw data for this project comes from `Sample_Game_2`.

Important raw data files:

- `data/Sample_Game_2/Sample_Game_2_RawTrackingData_Home_Team.csv`
- `data/Sample_Game_2/Sample_Game_2_RawTrackingData_Away_Team.csv`
- `data/Sample_Game_2/Sample_Game_2_RawEventsData.csv`

### How to explain tracking data

Say:

> Tracking data tells us where every player and the ball are at each moment of the match.

Important ideas:

- each row is one moment in time
- each player has an `x` and `y` position
- the pitch is normalized from `0` to `1`
- the data is sampled many times per second

### How to explain events data

Say:

> Events data tells us what happened in the match, like a shot, pass, recovery, corner, or goal.

Important ideas:

- each row is one football action
- `Type` is the big category
- `Subtype` is the extra detail
- event rows also include frame and time information

## 4. Why We Converted CSV to Parquet

This is one of the most important architecture decisions to explain clearly.

### The simple answer

Say:

> CSV is easy for humans to open, but not ideal for fast querying. Parquet is much better for analytics because it is smaller, faster, and more structured.

### Why CSV was not enough

CSV is good because:

- it is simple
- it is readable
- it is easy to share

But CSV is not ideal for this project because:

- it is larger on disk
- it is slower to query repeatedly
- it is not optimized for analytical reads
- it becomes expensive when you want low-latency responses

### Why Parquet was chosen

Parquet is good because:

- it is compressed
- it is columnar
- it is much better for analytics
- it works very well with DuckDB

### What “columnar” means in simple words

Say:

> CSV stores data row by row. Parquet stores it more efficiently by columns. That matters because many analytical questions only need a few columns, not the whole file.

### Why this matters for our project

If the user asks:

> Show me the player positions at frame 1500

we do not want to scan giant raw CSV files over and over. We want fast access to structured data.

That is why Parquet is part of the foundation.

## 5. Why We Chose DuckDB

This is another key reasoning section.

### The simple answer

Say:

> DuckDB is a lightweight analytical database that can query Parquet files directly without needing a heavy database server.

### Why not use a full database server?

For this project, we did not need:

- a separate cloud database
- a complicated server setup
- user accounts and multi-tenant management

We mainly needed:

- fast analytical queries
- local simplicity
- direct Parquet support

DuckDB was a great fit because:

- it is easy to use in Python
- it is fast
- it reads Parquet directly
- it works well for local analytics

### Good explanation line

> DuckDB gives us database power without database heaviness.

## 6. What the Main Files Are

For explanation purposes, the project can be grouped into:

- `scripts`
  - data preparation
- `tools`
  - database queries
- `core`
  - AI routing logic
- `api`
  - websocket communication
- `static`
  - browser visualization
- `data`
  - raw and processed match data

The most important files to explain are:

- [convert_metrica_tracking_to_parquet.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_metrica_tracking_to_parquet.py)
- [convert_metrica_events_to_parquet.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_metrica_events_to_parquet.py)
- [convert_data.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_data.py)
- [db_engine.py](C:/Users/josep/OneDrive/Desktop/sample-data/tools/db_engine.py)
- [llm_router.py](C:/Users/josep/OneDrive/Desktop/sample-data/core/llm_router.py)
- [websocket_server.py](C:/Users/josep/OneDrive/Desktop/sample-data/api/websocket_server.py)
- [main.py](C:/Users/josep/OneDrive/Desktop/sample-data/main.py)
- [test_websocket_client.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/test_websocket_client.py)
- [index.html](C:/Users/josep/OneDrive/Desktop/sample-data/static/index.html)

## 7. Explain the Scripts First

This is a good place to start the technical explanation, because scripts are easy to understand.

### 7.1 `scripts/convert_metrica_tracking_to_parquet.py`

This script converts one tracking CSV file into one Parquet file.

Main purpose:

- read a tracking CSV
- clean the headers
- remove fully empty columns
- force the `Frame` column to integer
- save the result as compressed Parquet

### Important function: `normalize_tracking_columns(columns)`

How to explain it:

> The raw tracking CSV has awkward headers. This function turns those messy headers into clean column names like `Player25_x` and `Player25_y`.

Why this matters:

- later code becomes easier to read
- querying becomes more reliable
- the data becomes easier to explain to others

### Important function: `convert_csv_to_parquet(input_csv, output_parquet)`

How to explain it:

> This is the main conversion function. It reads the file, cleans it, keeps important missing values, and writes a smaller, faster Parquet version.

Important design choice:

- row-level `NaN` values are kept

Why?

Because missing values can mean something real, like:

- a player not being on the pitch yet
- ball position not being available at that moment

So we do not remove meaningful missing data. We only remove columns that are completely empty.

### 7.2 `scripts/convert_metrica_events_to_parquet.py`

This script converts the events CSV into Parquet.

Main purpose:

- read event data
- remove fully empty columns
- make important frame columns integers
- save to Parquet

How to explain it:

> This does for event data what the first script did for tracking data. It makes the file more query-friendly and much better for the backend.

### 7.3 `scripts/convert_data.py`

This is one of the most important data preparation files.

Main purpose:

- load both home and away tracking files
- clean both files
- merge them horizontally
- keep one row per frame
- save the final merged tracking data

### Why merging home and away matters

Say:

> If home players are in one file and away players are in another file, querying them together is more annoying. We merged them so that one frame contains the full picture of the match.

This is a huge simplification for later steps.

### Important function: `load_tracking_csv(csv_path, team_prefix)`

How to explain it:

> This reads a team’s tracking file and adds a prefix like `Home_` or `Away_` so we know which player belongs to which team later.

### Important function: `merge_tracking_data(home_df, away_df)`

How to explain it:

> This combines the two team dataframes using `Period` and `Frame` as the keys, which means we line them up by exact match moment.

Important reasoning:

- `Period` tells us which half
- `Frame` tells us the exact time step

That makes them the perfect join keys.

### Important helper: `coalesce_duplicate_column(...)`

How to explain it:

> When we merge the two team files, some columns appear twice, like time or ball position. This helper keeps the useful version and removes the duplicate.

## 8. Explain the Database Layer Next

### `tools/db_engine.py`

This file is one of the true backend cores.

This file connects the AI layer to the data.

Good explanation line:

> If the scripts prepared the books, `db_engine.py` is the librarian that knows how to find the right page quickly.

### Why this file exists

We do not want the AI model reading huge files directly.

Instead:

- the AI decides what it needs
- this file fetches exactly that data

That separation is important.

### Important helper: `_connect()`

How to explain it:

> This creates an in-memory DuckDB connection. It is lightweight, fast, and good for short analytical queries.

### Important helper: `_require_file(path, description)`

How to explain it:

> This is a safety check. Before querying a file, we confirm it actually exists.

Why this matters:

- better error messages
- less confusion during debugging

### Important function: `get_player_coordinates_for_frame(target_frame)`

This is one of the most important functions in the whole project.

What it does:

- checks the frame is an integer
- reads the tracking parquet
- finds coordinate columns
- queries one frame
- returns a Python dictionary of coordinates

How to explain it simply:

> This function answers the question: “At this exact frame, where was everyone?”

Why it returns a dictionary:

Because the frontend and backend can work with it easily.

Example shape:

```python
{
  "Home_Player11": {"x": 0.82, "y": 0.47},
  "Away_Player25": {"x": 0.06, "y": 0.41},
  "Ball": {"x": 0.33, "y": 0.05}
}
```

### Important function: `find_event(...)`

This is the big Day 2 function.

What it does:

- reads the events parquet
- filters by event type
- can filter by team
- can filter by subtype
- can find first or last match
- can find events before, after, or around a frame
- returns rich event metadata

How to explain it simply:

> This function answers the question: “Which moment in the match are we talking about?”

This is what gives the system tactical context.

Without it, the system only knows frame numbers.

With it, the system understands football events like:

- first shot
- second corner
- last goal before 70:00

### Important function: `find_event_frame(...)`

How to explain it:

> This is a simpler helper built on top of `find_event(...)`. It only returns the frame number, which is useful when we do not need the full event details.

### Important function: `get_tracking_frame(frame)`

How to explain it:

> This is a small wrapper around the frame-coordinate lookup. It gives the router a simpler tool name and cleaner intent.

## 9. Explain the AI Routing Layer

### `core/llm_router.py`

This file is the intelligence bridge.

It connects:

- natural language from a user
- Groq’s model
- local tools in `db_engine.py`

Good explanation line:

> This file is the brain that decides what needs to be looked up.

### Why this file matters

The user does not say:

- “Run SQL query X”

The user says:

- “Show me the away team’s second corner”

That normal-English request must be translated into structured tool calls.

That is what `llm_router.py` does.

### Important constants

- `MODEL_NAME`
- `FRAMES_PER_SECOND`
- `MAX_TOOL_ITERATIONS`

How to explain them:

- `MODEL_NAME`
  - which Groq model we use
- `FRAMES_PER_SECOND`
  - how we convert time into frame numbers
- `MAX_TOOL_ITERATIONS`
  - a safety cap so the tool loop does not continue forever

### Important variable: `SYSTEM_PROMPT`

How to explain it:

> This is the instruction sheet we give the AI model so it knows how to behave and which tools to use.

This is extremely important because:

- the model needs boundaries
- the model needs mappings like “goal means shot with subtype goal”
- the model needs to know the final step must be tracking coordinates

### Important variable: `TOOLS`

How to explain it:

> This is the list of tools the AI is allowed to call.

In this project, the main tools are:

- `find_event`
- `get_tracking_frame`

### Important variable: `AVAILABLE_FUNCTIONS`

How to explain it:

> This connects tool names from the AI world to real Python functions in our code.

### Important helper: `_extract_frame_hint(user_query)`

This tries to pull frame information from the user’s sentence.

It supports:

- `minute 5`
- `2:30`
- `15th minute`
- `frame 10000`

How to explain it:

> This is a local shortcut. Before asking the AI, we try to understand obvious time formats ourselves.

Why this is smart:

- less work for the model
- fewer model mistakes
- faster, cleaner tool calls

### Important helper: `_extract_occurrence_hint(user_query)`

How to explain it:

> This extracts words like first, second, third, and converts them into numbers.

### Important helper: `_extract_order_hint(user_query)`

How to explain it:

> This detects whether the user wants the earliest event or the latest one.

For example:

- `first goal`
- `last shot`

### Important helper: `_extract_team_hint(user_query)`

How to explain it:

> This checks whether the user is asking about Home or Away.

### Important helper: `_extract_relation_hint(user_query)`

How to explain it:

> This detects words like before, after, and around.

These words change how the event search should behave.

### Important helper: `_extract_event_hint(user_query)`

How to explain it:

> This is where we recognize football language patterns like goal, shot, corner, pass, interception, and card.

This is a very important function because it adds domain understanding before the AI model even runs.

### Important helper: `_build_user_content(user_query)`

How to explain it:

> This builds a smarter version of the user’s query by adding useful hints for the AI model.

Example:

- if the user says `Show me the away team's second corner`
- this helper might add structured hints like:
  - event type
  - team
  - occurrence

Why this matters:

- the model becomes more reliable
- tool calls become cleaner

### Important helper: `_execute_tool_call(tool_call)`

How to explain it:

> Once the AI chooses a tool, this function actually runs the real Python function behind it.

### Important helper: `_serialize_tool_result(...)`

How to explain it:

> After a tool runs, this formats the result so it can be sent back into the AI conversation loop.

### Most important function: `route_analysis_query(user_query)`

This is the core function of the AI system.

What it does:

1. validates the user query
2. builds smarter hints
3. sends messages to Groq
4. lets Groq choose tools
5. executes those tools locally
6. feeds the tool results back into the conversation loop
7. stops when tracking coordinates are resolved
8. returns:
   - coordinates
   - context

How to explain it simply:

> This is the traffic controller. It listens to the user, talks to the AI model, runs the right tools, and sends back the final answer.

### Important function: `route_tracking_query(user_query)`

How to explain it:

> This is a simpler wrapper kept for compatibility. It only returns the coordinate part of the analysis result.

## 10. Explain the WebSocket API

### `api/websocket_server.py`

This is the real-time communication layer.

Good explanation line:

> If `llm_router.py` is the brain, `websocket_server.py` is the phone line between the frontend and the backend.

### Why WebSocket instead of normal HTTP?

Say:

> We chose WebSocket because it is better for ongoing, real-time interaction. Once the connection is open, the frontend and backend can keep talking without reopening a new request every time.

Why that helps:

- lower overhead
- better for interactive UIs
- more natural for live data applications

### Important object: `app = FastAPI()`

How to explain it:

> This creates the FastAPI application itself.

### Important helper: `_extract_query(message_text)`

What it does:

- reads incoming WebSocket message text
- supports:
  - plain string
  - JSON with a `query` field
- validates that the query is not empty

How to explain it:

> This makes the socket more flexible and user-friendly. The backend can understand both simple and structured client messages.

### Important helper: `_build_render_message(analysis_result)`

What it does:

- packages the backend result into a frontend-friendly JSON structure

Output shape:

```json
{
  "type": "DATA_RENDER",
  "payload": {
    "view": "PITCH_HOME",
    "data": {},
    "context": {}
  }
}
```

How to explain it:

> This gives the frontend one consistent response format to work with.

### Important route: `@app.get("/")`

How to explain it:

> This serves the tiny frontend page when someone opens the app in a browser.

### Most important route: `@app.websocket("/ws/analysis")`

This is the key backend endpoint.

What it does:

1. accepts a WebSocket connection
2. waits for incoming messages
3. extracts the query
4. sends the query into `route_analysis_query(...)`
5. gets back coordinates and context
6. sends the render payload back to the client
7. catches errors and sends an `ERROR` payload instead of crashing

How to explain it simply:

> This is the live conversation channel between the browser and the AI backend.

## 11. Explain `main.py`

This file is very small, but important.

### What it does

It runs the FastAPI app using Uvicorn.

How to explain it:

> `main.py` is the file that starts the server.

Simple enough.

## 12. Explain the Test Client

### `scripts/test_websocket_client.py`

What it does:

- opens a websocket connection
- sends a sample query
- waits for a response
- prints the response

How to explain it:

> This is our quick backend tester. It helps us verify the websocket pipeline without needing the browser UI.

Why this file matters:

- fast debugging
- helps isolate frontend vs backend issues

## 13. Explain the Frontend Simply

### `static/index.html`

This is the tiny visual demo layer.

What it does:

- gives the user a text box
- opens a websocket connection to the backend
- sends natural-language queries
- receives render payloads
- draws the players and ball on a pitch
- shows extra event context
- shows raw JSON for debugging

How to explain it:

> This file is a simple proof-of-concept frontend. It is not the final polished app, but it shows that the whole system works from end to end.

### Why it is useful even if it is simple

Because it proves:

- the data pipeline works
- the AI routing works
- the websocket works
- the coordinates can be visualized correctly

## 14. Suggested Order for Explaining the Whole Project

This is a very good order to use in front of an audience:

1. Explain the problem
   - raw football data is hard to search and visualize
2. Explain the data
   - tracking and events
3. Explain why CSV was converted to Parquet
4. Explain why DuckDB was chosen
5. Explain the scripts
   - data preparation
6. Explain `db_engine.py`
   - data lookup layer
7. Explain `llm_router.py`
   - AI + tool orchestration
8. Explain `websocket_server.py`
   - frontend/backend communication
9. Explain `index.html`
   - simple visual demo
10. Do a live example
   - `Show me the away team's second corner`

This order works well because it moves from:

- simple ideas
- to prepared data
- to backend intelligence
- to live user experience

## 15. A Good Live Demo Script

You can say something like:

> First, we take raw football CSV data. Then we convert it into Parquet so it becomes faster to search. Next, DuckDB gives us quick local analytics. Then Groq helps us understand a human question like “Show me the last goal before 70 minutes.” The AI does not directly search the files itself. Instead, it calls our local Python tools. Those tools find the event, get the frame, fetch the tracking coordinates, and return them through a WebSocket to the frontend. Finally, the frontend draws the players and ball on the pitch.

That one paragraph is a very strong explanation.

## 16. Questions Young People May Ask

### “Why not just use CSV directly?”

Answer:

> Because CSV is easy to read, but not ideal when you want repeated fast queries. Parquet is much better for speed and analytics.

### “Why do we need both events and tracking?”

Answer:

> Tracking tells us where everyone is. Events tell us what happened. Together, they tell a much richer story.

### “Why use AI at all?”

Answer:

> Because people naturally ask questions in English, not SQL or code. The AI acts like a translator between human language and structured data tools.

### “Why use DuckDB?”

Answer:

> Because it is fast, simple, local, and works very well with Parquet files.

### “Why WebSocket?”

Answer:

> Because we want the frontend and backend to communicate smoothly and continuously, not as separate disconnected requests every time.

## 17. Best Final Closing

A strong ending is:

> This project shows how raw sports data, databases, AI tool-calling, APIs, and frontend visualization can work together in one system. The real achievement is not just showing dots on a pitch. It is building a full pipeline where a natural-language football question becomes a fast, visual, data-driven answer.

## 18. Final Reminder for Yourself

When explaining this project, do not rush into code first.

Always start with:

1. the problem
2. the data
3. the architecture
4. then the files

That will make the explanation much easier for others to follow.
