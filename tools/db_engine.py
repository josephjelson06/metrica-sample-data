from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKING_PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_tracking.parquet"
EVENTS_PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_events.parquet"
FRAMES_PER_SECOND = 25
DEFAULT_EVENT_LIST_LIMIT = 25

PITCH_ZONE_SQL = {
    "attacking_third": '"Start X" >= 0.6666666667',
    "middle_third": '"Start X" >= 0.3333333333 AND "Start X" < 0.6666666667',
    "defensive_third": '"Start X" < 0.3333333333',
    "left_wing": '"Start Y" < 0.22',
    "right_wing": '"Start Y" > 0.78',
    "central_channel": '"Start Y" >= 0.33 AND "Start Y" <= 0.67',
    "penalty_box": '(("Start X" <= 0.1571428571 OR "Start X" >= 0.8428571429) AND "Start Y" >= 0.2058823529 AND "Start Y" <= 0.7941176471)',
}

CoordinateValue = float | int | None
CoordinateMap = dict[str, dict[str, CoordinateValue]]


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


def _require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} not found at {path}.")


def _get_tracking_coordinate_columns(connection: duckdb.DuckDBPyConnection) -> list[str]:
    columns_info = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(TRACKING_PARQUET_PATH)],
    ).fetchall()
    return [
        column_name
        for column_name, *_ in columns_info
        if column_name.endswith("_x") or column_name.endswith("_y")
    ]


def _build_coordinate_map(coordinate_columns: list[str], row_values: tuple[Any, ...]) -> CoordinateMap:
    result: CoordinateMap = {}
    for column_name, value in zip(coordinate_columns, row_values):
        player_name, axis = column_name.rsplit("_", 1)
        result.setdefault(player_name, {})[axis] = value
    return result


def _build_event_dict(row: tuple[Any, ...]) -> dict[str, Any]:
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
    event["frame"] = int(event["start_frame"])
    return event


def _normalize_pitch_zone(pitch_zone: str | None) -> str | None:
    if pitch_zone is None:
        return None

    normalized_zone = str(pitch_zone).strip().lower().replace(" ", "_")
    if not normalized_zone:
        return None

    if normalized_zone not in PITCH_ZONE_SQL:
        valid_zones = ", ".join(sorted(PITCH_ZONE_SQL))
        raise ValueError(f"pitch_zone must be one of: {valid_zones}.")

    return normalized_zone


def _build_event_where_clause(
    *,
    event_type: str | None = None,
    team: str | None = None,
    subtype_contains: str | None = None,
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
) -> tuple[list[str], list[Any]]:
    relation = str(relation).strip().lower()
    if relation not in {"exact", "before", "after", "around"}:
        raise ValueError("relation must be one of: exact, before, after, around.")

    if relation != "exact" and anchor_frame is None:
        raise ValueError("anchor_frame is required for before/after/around event lookups.")

    filters: list[str] = []
    params: list[Any] = []

    if event_type and str(event_type).strip():
        filters.append('UPPER("Type") = UPPER(?)')
        params.append(str(event_type).strip())

    if team and str(team).strip():
        filters.append('UPPER("Team") = UPPER(?)')
        params.append(str(team).strip())

    if subtype_contains and str(subtype_contains).strip():
        filters.append('UPPER(COALESCE("Subtype", \'\')) LIKE UPPER(?)')
        params.append(f"%{str(subtype_contains).strip()}%")

    if period is not None:
        if not isinstance(period, int):
            raise TypeError("period must be an integer when provided.")
        filters.append('"Period" = ?')
        params.append(period)

    normalized_zone = _normalize_pitch_zone(pitch_zone)
    if normalized_zone is not None:
        filters.append(PITCH_ZONE_SQL[normalized_zone])

    if relation == "before":
        filters.append('"Start Frame" < ?')
        params.append(anchor_frame)
    elif relation == "after":
        filters.append('"Start Frame" > ?')
        params.append(anchor_frame)

    return filters, params


def _build_event_order_by_clause(relation: str, order: str) -> str:
    if relation == "around":
        return 'ABS("Start Frame" - ?) ASC, "Period" ASC, "Start Frame" ASC'
    if relation == "before" or order == "last":
        return '"Period" DESC, "Start Frame" DESC'
    return '"Period" ASC, "Start Frame" ASC'


def find_event(
    event_type: str,
    team: str | None = None,
    subtype_contains: str | None = None,
    occurrence: int = 1,
    order: str = "first",
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
) -> dict[str, Any]:
    if not event_type or not str(event_type).strip():
        raise ValueError("event_type must be a non-empty string.")

    if occurrence < 1:
        raise ValueError("occurrence must be 1 or greater.")

    order = str(order).strip().lower()
    relation = str(relation).strip().lower()
    if order not in {"first", "last"}:
        raise ValueError("order must be either 'first' or 'last'.")

    _require_file(EVENTS_PARQUET_PATH, "Events parquet file")

    filters, params = _build_event_where_clause(
        event_type=event_type,
        team=team,
        subtype_contains=subtype_contains,
        relation=relation,
        anchor_frame=anchor_frame,
        period=period,
        pitch_zone=pitch_zone,
    )
    order_by_clause = _build_event_order_by_clause(relation=relation, order=order)
    if relation == "around":
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
            "period": period,
            "pitch_zone": pitch_zone,
        }
        raise ValueError(f"No matching event found for {filters_used}.")

    event = _build_event_dict(row)
    event["occurrence"] = occurrence
    event["order"] = order
    event["relation"] = relation
    event["anchor_frame"] = anchor_frame
    event["period_filter"] = period
    event["pitch_zone"] = _normalize_pitch_zone(pitch_zone)
    return event


def find_event_frame(
    event_type: str,
    team: str | None = None,
    subtype_contains: str | None = None,
    occurrence: int = 1,
    order: str = "first",
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
) -> int:
    event = find_event(
        event_type=event_type,
        team=team,
        subtype_contains=subtype_contains,
        occurrence=occurrence,
        order=order,
        relation=relation,
        anchor_frame=anchor_frame,
        period=period,
        pitch_zone=pitch_zone,
    )
    return int(event["frame"])


def list_events(
    event_type: str | None = None,
    team: str | None = None,
    subtype_contains: str | None = None,
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
    limit: int = DEFAULT_EVENT_LIST_LIMIT,
) -> list[dict[str, Any]]:
    if not isinstance(limit, int):
        raise TypeError("limit must be an integer.")

    if limit < 1:
        raise ValueError("limit must be 1 or greater.")

    _require_file(EVENTS_PARQUET_PATH, "Events parquet file")

    filters, params = _build_event_where_clause(
        event_type=event_type,
        team=team,
        subtype_contains=subtype_contains,
        relation=relation,
        anchor_frame=anchor_frame,
        period=period,
        pitch_zone=pitch_zone,
    )
    order_by_clause = _build_event_order_by_clause(relation=relation, order="first")
    if relation == "around":
        params.append(anchor_frame)

    where_clause = " AND ".join(filters) if filters else "1=1"
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
        WHERE {where_clause}
        ORDER BY {order_by_clause}
        LIMIT ?
    """

    connection = _connect()
    try:
        rows = connection.execute(
            query,
            [str(EVENTS_PARQUET_PATH), *params, limit],
        ).fetchall()
    finally:
        connection.close()

    events = [_build_event_dict(row) for row in rows]
    normalized_zone = _normalize_pitch_zone(pitch_zone)
    for event in events:
        event["period_filter"] = period
        event["pitch_zone"] = normalized_zone
    return events


def count_events(
    event_type: str | None = None,
    team: str | None = None,
    subtype_contains: str | None = None,
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
) -> int:
    _require_file(EVENTS_PARQUET_PATH, "Events parquet file")

    filters, params = _build_event_where_clause(
        event_type=event_type,
        team=team,
        subtype_contains=subtype_contains,
        relation=relation,
        anchor_frame=anchor_frame,
        period=period,
        pitch_zone=pitch_zone,
    )
    where_clause = " AND ".join(filters) if filters else "1=1"

    query = f"""
        SELECT COUNT(*)
        FROM read_parquet(?)
        WHERE {where_clause}
    """

    connection = _connect()
    try:
        row = connection.execute(
            query,
            [str(EVENTS_PARQUET_PATH), *params],
        ).fetchone()
    finally:
        connection.close()

    return int(row[0]) if row is not None else 0


def get_tracking_frame(frame: int) -> dict[str, dict[str, float | int | None]]:
    return get_player_coordinates_for_frame(target_frame=frame)


def get_tracking_window(
    start_frame: int,
    end_frame: int,
    frame_step: int = 1,
) -> list[dict[str, Any]]:
    if not isinstance(start_frame, int) or not isinstance(end_frame, int):
        raise TypeError("start_frame and end_frame must be integers.")

    if not isinstance(frame_step, int):
        raise TypeError("frame_step must be an integer.")

    if frame_step < 1:
        raise ValueError("frame_step must be 1 or greater.")

    _require_file(TRACKING_PARQUET_PATH, "Tracking parquet file")

    lower_frame = min(start_frame, end_frame)
    upper_frame = max(start_frame, end_frame)

    connection = _connect()
    try:
        coordinate_columns = _get_tracking_coordinate_columns(connection)
        select_clause = ", ".join(f'"{column_name}"' for column_name in coordinate_columns)
        query = f"""
            SELECT "Frame", {select_clause}
            FROM read_parquet(?)
            WHERE "Frame" BETWEEN ? AND ?
            ORDER BY "Frame" ASC
        """
        rows = connection.execute(
            query,
            [str(TRACKING_PARQUET_PATH), lower_frame, upper_frame],
        ).fetchall()

        window_frames: list[dict[str, Any]] = []
        for row in rows:
            frame = int(row[0])
            if (frame - lower_frame) % frame_step != 0:
                continue

            coordinates = _build_coordinate_map(coordinate_columns, row[1:])
            window_frames.append(
                {
                    "frame": frame,
                    "coordinates": coordinates,
                }
            )

        return window_frames
    finally:
        connection.close()


def get_event_tracking_window(
    event_frame: int,
    frames_before: int = FRAMES_PER_SECOND * 5,
    frames_after: int = FRAMES_PER_SECOND * 2,
    frame_step: int = 1,
) -> dict[str, Any]:
    if not isinstance(event_frame, int):
        raise TypeError("event_frame must be an integer.")

    if frames_before < 0 or frames_after < 0:
        raise ValueError("frames_before and frames_after must be 0 or greater.")

    start_frame = max(1, event_frame - frames_before)
    end_frame = max(start_frame, event_frame + frames_after)
    frames = get_tracking_window(start_frame=start_frame, end_frame=end_frame, frame_step=frame_step)
    events = get_events_in_window(start_frame=start_frame, end_frame=end_frame)

    return {
        "event_frame": event_frame,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_step": frame_step,
        "frames_per_second": FRAMES_PER_SECOND,
        "frames": frames,
        "events": events,
    }


def get_events_in_window(start_frame: int, end_frame: int, limit: int = 24) -> list[dict[str, Any]]:
    if not isinstance(start_frame, int) or not isinstance(end_frame, int):
        raise TypeError("start_frame and end_frame must be integers.")

    if not isinstance(limit, int):
        raise TypeError("limit must be an integer.")

    if limit < 1:
        raise ValueError("limit must be 1 or greater.")

    _require_file(EVENTS_PARQUET_PATH, "Events parquet file")

    lower_frame = min(start_frame, end_frame)
    upper_frame = max(start_frame, end_frame)

    query = """
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
        WHERE "Start Frame" BETWEEN ? AND ?
        ORDER BY "Start Frame" ASC
        LIMIT ?
    """

    connection = _connect()
    try:
        rows = connection.execute(
            query,
            [str(EVENTS_PARQUET_PATH), lower_frame, upper_frame, limit],
        ).fetchall()
    finally:
        connection.close()

    return [_build_event_dict(row) for row in rows]


def get_player_coordinates_for_frame(target_frame: int) -> CoordinateMap:
    if not isinstance(target_frame, int):
        raise TypeError("target_frame must be an integer.")

    _require_file(TRACKING_PARQUET_PATH, "Tracking parquet file")

    connection = _connect()
    try:
        coordinate_columns = _get_tracking_coordinate_columns(connection)
        select_clause = ", ".join(f'"{column_name}"' for column_name in coordinate_columns)
        query = f"""
            SELECT {select_clause}
            FROM read_parquet(?)
            WHERE "Frame" = ?
        """
        row = connection.execute(query, [str(TRACKING_PARQUET_PATH), target_frame]).fetchone()

        if row is None:
            return {}

        return _build_coordinate_map(coordinate_columns, row)
    finally:
        connection.close()


if __name__ == "__main__":
    start = time.perf_counter()
    first_away_shot = find_event(event_type="SHOT", team="Away", occurrence=1)
    coordinates = get_tracking_frame(first_away_shot["frame"])
    sequence = get_event_tracking_window(first_away_shot["frame"])
    elapsed = time.perf_counter() - start

    print(first_away_shot)
    print(coordinates)
    print(f"Sequence frames fetched: {len(sequence['frames'])}")
    print(f"Execution time: {elapsed:.6f} seconds")
