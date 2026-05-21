from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKING_PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_tracking.parquet"
EVENTS_PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_events.parquet"


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


def _require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found at {path}.")


def find_event(
    event_type: str,
    team: str | None = None,
    subtype_contains: str | None = None,
    occurrence: int = 1,
    order: str = "first",
    relation: str = "exact",
    anchor_frame: int | None = None,
) -> dict[str, Any]:
    if not event_type or not str(event_type).strip():
        raise ValueError("event_type must be a non-empty string.")

    if occurrence < 1:
        raise ValueError("occurrence must be 1 or greater.")

    order = str(order).strip().lower()
    relation = str(relation).strip().lower()
    if order not in {"first", "last"}:
        raise ValueError("order must be either 'first' or 'last'.")

    if relation not in {"exact", "before", "after", "around"}:
        raise ValueError("relation must be one of: exact, before, after, around.")

    if relation != "exact" and anchor_frame is None:
        raise ValueError("anchor_frame is required for before/after/around event lookups.")

    _require_file(EVENTS_PARQUET_PATH, "Events parquet file")

    filters = ['UPPER("Type") = UPPER(?)']
    params: list[Any] = [event_type.strip()]

    if team and str(team).strip():
        filters.append('UPPER("Team") = UPPER(?)')
        params.append(team.strip())

    if subtype_contains and str(subtype_contains).strip():
        filters.append('UPPER(COALESCE("Subtype", \'\')) LIKE UPPER(?)')
        params.append(f"%{subtype_contains.strip()}%")

    if relation == "before":
        filters.append('"Start Frame" < ?')
        params.append(anchor_frame)
    elif relation == "after":
        filters.append('"Start Frame" > ?')
        params.append(anchor_frame)

    order_by_clause = '"Period" ASC, "Start Frame" ASC'
    if relation == "before" or order == "last":
        order_by_clause = '"Period" DESC, "Start Frame" DESC'
    if relation == "after":
        order_by_clause = '"Period" ASC, "Start Frame" ASC'
    if relation == "around":
        order_by_clause = 'ABS("Start Frame" - ?) ASC, "Period" ASC, "Start Frame" ASC'
        params.append(anchor_frame)

    query = f"""
        SELECT
            "Team",
            "Type",
            "Subtype",
            "Period",
            "Start Frame",
            "Start Time [s]",
            "End Frame",
            "End Time [s]",
            "From",
            "To",
            "Start X",
            "Start Y",
            "End X",
            "End Y"
        FROM read_parquet(?)
        WHERE {" AND ".join(filters)}
        ORDER BY {order_by_clause}
        LIMIT 1 OFFSET ?
    """
    params = [str(EVENTS_PARQUET_PATH), *params, occurrence - 1]

    connection = _connect()
    try:
        row = connection.execute(query, params).fetchone()
    finally:
        connection.close()

    if row is None:
        filters_used = {
            "event_type": event_type,
            "team": team,
            "subtype_contains": subtype_contains,
            "occurrence": occurrence,
            "order": order,
            "relation": relation,
            "anchor_frame": anchor_frame,
        }
        raise ValueError(f"No matching event found for {filters_used}.")

    columns = [
        "team",
        "type",
        "subtype",
        "period",
        "start_frame",
        "start_time_s",
        "end_frame",
        "end_time_s",
        "from_player",
        "to_player",
        "start_x",
        "start_y",
        "end_x",
        "end_y",
    ]
    event = dict(zip(columns, row))
    event["occurrence"] = occurrence
    event["order"] = order
    event["relation"] = relation
    event["anchor_frame"] = anchor_frame
    event["frame"] = int(event["start_frame"])
    return event


def find_event_frame(
    event_type: str,
    team: str | None = None,
    subtype_contains: str | None = None,
    occurrence: int = 1,
    order: str = "first",
    relation: str = "exact",
    anchor_frame: int | None = None,
) -> int:
    event = find_event(
        event_type=event_type,
        team=team,
        subtype_contains=subtype_contains,
        occurrence=occurrence,
        order=order,
        relation=relation,
        anchor_frame=anchor_frame,
    )
    return int(event["frame"])


def get_tracking_frame(frame: int) -> dict[str, dict[str, float | int | None]]:
    return get_player_coordinates_for_frame(target_frame=frame)


def get_player_coordinates_for_frame(target_frame: int) -> dict[str, dict[str, float | int | None]]:
    if not isinstance(target_frame, int):
        raise TypeError("target_frame must be an integer.")

    _require_file(TRACKING_PARQUET_PATH, "Tracking parquet file")

    connection = _connect()
    try:
        columns_info = connection.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(TRACKING_PARQUET_PATH)],
        ).fetchall()

        coordinate_columns = [
            column_name
            for column_name, *_ in columns_info
            if column_name.endswith("_x") or column_name.endswith("_y")
        ]

        select_clause = ", ".join(f'"{column_name}"' for column_name in coordinate_columns)
        query = f"""
            SELECT {select_clause}
            FROM read_parquet(?)
            WHERE "Frame" = ?
        """
        row = connection.execute(query, [str(TRACKING_PARQUET_PATH), target_frame]).fetchone()

        if row is None:
            return {}

        result: dict[str, dict[str, float | int | None]] = {}
        for column_name, value in zip(coordinate_columns, row):
            player_name, axis = column_name.rsplit("_", 1)
            result.setdefault(player_name, {})[axis] = value

        return result
    finally:
        connection.close()


if __name__ == "__main__":
    start = time.perf_counter()
    first_away_shot = find_event(event_type="SHOT", team="Away", occurrence=1)
    coordinates = get_tracking_frame(first_away_shot["frame"])
    elapsed = time.perf_counter() - start

    print(first_away_shot)
    print(coordinates)
    print(f"Execution time: {elapsed:.6f} seconds")
