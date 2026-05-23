# Day 1 Progress Report

This document summarizes what was completed on Day 1 for the Metrica sample-data project.

## 1. Dataset Understanding and Documentation

We explored the `Sample_Game_2` dataset and documented both the tracking data and the events data in simple language.

### Tracking data work completed

- Reviewed:
  - `data/Sample_Game_2/Sample_Game_2_RawTrackingData_Home_Team.csv`
  - `data/Sample_Game_2/Sample_Game_2_RawTrackingData_Away_Team.csv`
- Confirmed how the tracking files are structured
- Explained:
  - `Period`, `Frame`, and `Time [s]`
  - how player coordinates are stored as `x, y` pairs
  - how the ball is stored
  - how normalized pitch coordinates work
  - what `NaN` means in this dataset
  - why more than 11 players can appear in the file

### Events data work completed

- Reviewed:
  - `data/Sample_Game_2/Sample_Game_2_RawEventsData.csv`
- Analyzed unique values in the events file
- Mapped event `Type` values to their `Subtype` values
- Explained in simple words how:
  - `Type` is the main event category
  - `Subtype` is the detail under that category
  - some subtypes can appear under more than one type

### Documentation created

- [Sample_Game_2_Data_Guide.md](C:/Users/josep/OneDrive/Desktop/sample-data/docs/guides/Sample_Game_2_Data_Guide.md)

This guide explains the Sample Game 2 tracking and events data in simple words so it can be reused to explain the dataset to others.

## 2. Data Conversion Pipeline

We created scripts to convert raw CSV files into compressed Parquet files using `pandas` and `pyarrow`.

### Tracking conversion work

Created:

- [convert_metrica_tracking_to_parquet.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_metrica_tracking_to_parquet.py)

This script:

- reads a Metrica tracking CSV
- normalizes the header into usable column names
- keeps row-level missing values
- drops columns that are completely empty
- forces `Frame` to `int64`
- writes a compressed Parquet file using `pyarrow`

### Events conversion work

Created:

- [convert_metrica_events_to_parquet.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_metrica_events_to_parquet.py)

This script:

- reads the events CSV
- drops columns that are completely empty
- keeps row-level missing values
- forces `Period`, `Start Frame`, and `End Frame` to integer
- writes a compressed Parquet file

### Merged tracking conversion work

Created:

- [convert_data.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_data.py)

This script:

- loads both home and away tracking CSVs with pandas
- prefixes player columns as `Home_...` and `Away_...`
- merges the two tracking files horizontally on `Period` and `Frame`
- removes duplicate shared columns such as overlapping `Time [s]`
- keeps a single shared `Ball_x` and `Ball_y`
- drops completely empty columns
- saves the merged data as:
  - [metrica_tracking.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_tracking.parquet)

### Generated Parquet outputs

At the end of the conversion work, these outputs were created:

- [metrica_tracking_away.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_tracking_away.parquet)
- [metrica_tracking_home.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_tracking_home.parquet)
- [metrica_events.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_events.parquet)
- [metrica_tracking.parquet](C:/Users/josep/OneDrive/Desktop/sample-data/data/parquet/metrica_tracking.parquet)

The final merged tracking Parquet is the main file used by the backend query layer.

## 3. Python Environment Setup

### Environment work completed

- Created a local virtual environment:
  - `.venv`
- Installed required packages inside the virtual environment
- Added a dependency file:
  - [requirements.txt](C:/Users/josep/OneDrive/Desktop/sample-data/requirements.txt)

Current requirements include:

- `pandas`
- `pyarrow`
- `duckdb`
- `groq`
- `python-dotenv`
- `fastapi`
- `uvicorn`
- `websockets`

## 4. DuckDB Query Layer

Created:

- [tools/db_engine.py](C:/Users/josep/OneDrive/Desktop/sample-data/tools/db_engine.py)

This module provides a DuckDB-based function that:

- connects to an in-memory DuckDB database
- queries `data/parquet/metrica_tracking.parquet` directly
- looks up a specific `Frame`
- returns player and ball coordinates as a Python dictionary

Main function:

- `get_player_coordinates_for_frame(target_frame: int)`

This file also includes a simple local test block under `if __name__ == "__main__":`.

## 5. Groq LLM Router

Created:

- [core/llm_router.py](C:/Users/josep/OneDrive/Desktop/sample-data/core/llm_router.py)

This module:

- loads the Groq API key from:
  - [.env](C:/Users/josep/OneDrive/Desktop/sample-data/.env)
- uses the Groq Python SDK
- accepts a natural language query
- uses Groq tool-calling to route the request to the DuckDB function
- converts minute-based queries into frame numbers
- returns the dictionary of coordinates from DuckDB

### Router improvement completed

We fixed a tool-calling issue where Groq sometimes tried to send arithmetic expressions instead of valid JSON integers.

To fix that:

- minute-to-frame conversion is pre-resolved locally when possible
- the model is given an explicit integer frame hint
- the prompt now clearly says tool arguments must be valid JSON integers

This fixed websocket/backend failures for queries such as:

- `Give me the coordinates for minute 5`

## 6. FastAPI WebSocket Backend

Created:

- [api/websocket_server.py](C:/Users/josep/OneDrive/Desktop/sample-data/api/websocket_server.py)
- [main.py](C:/Users/josep/OneDrive/Desktop/sample-data/main.py)

### WebSocket server features

The FastAPI app now includes:

- a WebSocket endpoint at:
  - `/ws/analysis`
- a root route at:
  - `/`

The websocket server:

- accepts incoming websocket messages
- supports both:
  - plain text queries
  - JSON messages like `{"query": "..."}`
- sends the query to the Groq router
- receives back DuckDB coordinate data
- streams a payload back to the client in this format:

```json
{
  "type": "DATA_RENDER",
  "payload": {
    "view": "PITCH_HOME",
    "data": {}
  }
}
```

### App runner

- [main.py](C:/Users/josep/OneDrive/Desktop/sample-data/main.py) runs the FastAPI app with Uvicorn

## 7. WebSocket Test Client

Created:

- [test_websocket_client.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/test_websocket_client.py)

This test script:

- connects to:
  - `ws://localhost:8000/ws/analysis`
- sends a sample natural language query
- prints the websocket response returned by the backend

## 8. Tiny Frontend

Created:

- [static/index.html](C:/Users/josep/OneDrive/Desktop/sample-data/static/index.html)

### Frontend features

The frontend includes:

- a simple natural-language query box
- websocket connection to the backend
- live connection status
- a rendered football pitch
- home players, away players, and ball markers plotted on the pitch
- a raw JSON response viewer

The frontend is served directly by the FastAPI backend at:

- `http://127.0.0.1:8000/`

## 9. Testing Completed

### Conversion testing

- Verified the Parquet conversion scripts run successfully
- Confirmed tracking and event Parquet files were created
- Confirmed merged tracking Parquet was created with one row per frame

### DuckDB testing

- Verified `db_engine.py` imports correctly
- Verified frame-based coordinate lookup works against `data/parquet/metrica_tracking.parquet`

### Groq router testing

- Verified the router successfully handles natural language prompts
- Confirmed minute-based queries return coordinate dictionaries
- Fixed and retested the Groq tool-calling failure case

### Backend pipeline testing

- Started the FastAPI app with Uvicorn
- Ran the websocket client against `/ws/analysis`
- Confirmed the backend returned a valid `DATA_RENDER` response with coordinate data

### Frontend serving test

- Verified the homepage loads successfully from the FastAPI app
- Confirmed the HTML frontend is reachable at `/`

## 10. Main Deliverables from Day 1

Files created or added:

- [Sample_Game_2_Data_Guide.md](C:/Users/josep/OneDrive/Desktop/sample-data/docs/guides/Sample_Game_2_Data_Guide.md)
- [convert_metrica_tracking_to_parquet.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_metrica_tracking_to_parquet.py)
- [convert_metrica_events_to_parquet.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_metrica_events_to_parquet.py)
- [convert_data.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/convert_data.py)
- [tools/db_engine.py](C:/Users/josep/OneDrive/Desktop/sample-data/tools/db_engine.py)
- [core/llm_router.py](C:/Users/josep/OneDrive/Desktop/sample-data/core/llm_router.py)
- [api/websocket_server.py](C:/Users/josep/OneDrive/Desktop/sample-data/api/websocket_server.py)
- [main.py](C:/Users/josep/OneDrive/Desktop/sample-data/main.py)
- [test_websocket_client.py](C:/Users/josep/OneDrive/Desktop/sample-data/scripts/test_websocket_client.py)
- [static/index.html](C:/Users/josep/OneDrive/Desktop/sample-data/static/index.html)
- [requirements.txt](C:/Users/josep/OneDrive/Desktop/sample-data/requirements.txt)

## 11. Day 1 Outcome

By the end of Day 1, the project has:

- documented understanding of the Sample Game 2 dataset
- compressed Parquet versions of the tracking and event data
- a merged tracking dataset ready for querying
- a DuckDB query layer
- a Groq-based LLM router
- a FastAPI websocket backend
- a working websocket test client
- a tiny browser frontend that can display player positions on a pitch

This means the Day 1 foundation is complete: the data layer, LLM routing layer, backend transport layer, and a first frontend visualization are all in place.
