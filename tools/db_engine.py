from __future__ import annotations

import time
from math import hypot
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKING_PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_tracking.parquet"
EVENTS_PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_events.parquet"
FRAMES_PER_SECOND = 25
DEFAULT_EVENT_LIST_LIMIT = 25
TRANSITION_WINDOW_SECONDS = 5.0

PITCH_ZONE_SQL = {
    "attacking_third": "start_x >= 0.6666666667",
    "middle_third": "start_x >= 0.3333333333 AND start_x < 0.6666666667",
    "defensive_third": "start_x < 0.3333333333",
    "left_wing": "start_y < 0.22",
    "right_wing": "start_y > 0.78",
    "central_channel": "start_y >= 0.33 AND start_y <= 0.67",
    "penalty_box": "((start_x <= 0.1571428571 OR start_x >= 0.8428571429) AND start_y >= 0.2058823529 AND start_y <= 0.7941176471)",
}

PHASE_LABELS = {
    "set_piece",
    "in_possession",
    "out_of_possession",
    "attacking_transition",
    "defensive_transition",
}

CoordinateValue = float | int | None
CoordinateMap = dict[str, dict[str, CoordinateValue]]
CoordinatePoint = tuple[float, float]


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
    if len(row) == len(columns) + 1:
        columns.append("phase")
    event = dict(zip(columns, row))
    event["frame"] = int(event["start_frame"])
    return event


def _event_source_sql() -> str:
    return f"""
        SELECT
            "Team" AS team,
            "Type" AS type,
            "Subtype" AS subtype,
            "Period" AS period,
            "Start Frame" AS start_frame,
            "Start Time [s]" AS start_time_s,
            "End Frame" AS end_frame,
            "End Time [s]" AS end_time_s,
            "From" AS from_player,
            "To" AS to_player,
            "Start X" AS start_x,
            "Start Y" AS start_y,
            "End X" AS end_x,
            "End Y" AS end_y,
            CASE
                WHEN "Type" = 'SET PIECE' THEN 'set_piece'
                WHEN "Type" IN ('BALL LOST', 'BALL OUT') THEN 'defensive_transition'
                WHEN "Type" = 'RECOVERY' THEN 'attacking_transition'
                WHEN "Type" IN ('PASS', 'SHOT')
                    AND (
                        ("Team" = prev_team AND prev_type = 'RECOVERY')
                        OR ("Team" <> prev_team AND prev_type IN ('BALL LOST', 'BALL OUT'))
                    )
                    AND ("Start Time [s]" - COALESCE(prev_start_time_s, "Start Time [s]")) <= {TRANSITION_WINDOW_SECONDS}
                    THEN 'attacking_transition'
                WHEN "Type" IN ('CHALLENGE', 'FAULT RECEIVED', 'CARD') THEN 'out_of_possession'
                ELSE 'in_possession'
            END AS phase
        FROM (
            SELECT
                *,
                LAG("Team") OVER (ORDER BY "Period", "Start Frame") AS prev_team,
                LAG("Type") OVER (ORDER BY "Period", "Start Frame") AS prev_type,
                LAG("Start Time [s]") OVER (ORDER BY "Period", "Start Frame") AS prev_start_time_s
            FROM read_parquet(?)
        ) event_rows
    """


def _extract_team_points(coordinates: CoordinateMap, team: str) -> list[CoordinatePoint]:
    normalized_team = str(team).strip().lower()
    if normalized_team not in {"home", "away"}:
        raise ValueError("team must be either 'Home' or 'Away'.")

    team_prefix = "Home_" if normalized_team == "home" else "Away_"
    points: list[CoordinatePoint] = []
    for player_name, point in coordinates.items():
        if not player_name.startswith(team_prefix):
            continue
        x_value = point.get("x")
        y_value = point.get("y")
        if x_value is None or y_value is None:
            continue
        points.append((float(x_value), float(y_value)))

    return points


def _cross_product(origin: CoordinatePoint, left: CoordinatePoint, right: CoordinatePoint) -> float:
    return ((left[0] - origin[0]) * (right[1] - origin[1])) - ((left[1] - origin[1]) * (right[0] - origin[0]))


def _convex_hull(points: list[CoordinatePoint]) -> list[CoordinatePoint]:
    if len(points) < 3:
        return points

    sorted_points = sorted(points)
    lower_hull: list[CoordinatePoint] = []
    for point in sorted_points:
        while len(lower_hull) >= 2 and _cross_product(lower_hull[-2], lower_hull[-1], point) <= 0:
            lower_hull.pop()
        lower_hull.append(point)

    upper_hull: list[CoordinatePoint] = []
    for point in reversed(sorted_points):
        while len(upper_hull) >= 2 and _cross_product(upper_hull[-2], upper_hull[-1], point) <= 0:
            upper_hull.pop()
        upper_hull.append(point)

    lower_hull.pop()
    upper_hull.pop()
    return lower_hull + upper_hull


def _polygon_area(points: list[CoordinatePoint]) -> float:
    if len(points) < 3:
        return 0.0

    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += (point[0] * next_point[1]) - (next_point[0] * point[1])

    return abs(area) / 2.0


def get_team_shape_metrics_for_coordinates(coordinates: CoordinateMap, team: str) -> dict[str, Any]:
    points = _extract_team_points(coordinates, team)
    if not points:
        return {
            "team": team.title(),
            "player_count": 0,
            "width": None,
            "depth": None,
            "centroid_x": None,
            "centroid_y": None,
            "bounding_box_area": None,
            "hull_area": None,
            "average_distance_to_centroid": None,
            "compactness_area": None,
        }

    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    centroid_x = sum(x_values) / len(points)
    centroid_y = sum(y_values) / len(points)
    width = max(y_values) - min(y_values)
    depth = max(x_values) - min(x_values)
    hull = _convex_hull(points)
    hull_area = _polygon_area(hull)
    average_distance = sum(hypot(point[0] - centroid_x, point[1] - centroid_y) for point in points) / len(points)

    return {
        "team": team.title(),
        "player_count": len(points),
        "width": width,
        "depth": depth,
        "centroid_x": centroid_x,
        "centroid_y": centroid_y,
        "bounding_box_area": width * depth,
        "hull_area": hull_area,
        "average_distance_to_centroid": average_distance,
        "compactness_area": hull_area,
    }


def get_frame_team_metrics(frame: int, team: str | None = None) -> dict[str, Any]:
    coordinates = get_tracking_frame(frame)
    if not coordinates:
        return {}

    if team is not None:
        metrics = get_team_shape_metrics_for_coordinates(coordinates, team)
        metrics["frame"] = frame
        return metrics

    return {
        "frame": frame,
        "Home": get_team_shape_metrics_for_coordinates(coordinates, "Home"),
        "Away": get_team_shape_metrics_for_coordinates(coordinates, "Away"),
    }


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


def _normalize_phase_label(phase: str | None) -> str | None:
    if phase is None:
        return None

    normalized_phase = str(phase).strip().lower().replace(" ", "_")
    if not normalized_phase:
        return None

    if normalized_phase not in PHASE_LABELS:
        valid_phases = ", ".join(sorted(PHASE_LABELS))
        raise ValueError(f"phase must be one of: {valid_phases}.")

    return normalized_phase


def _build_event_where_clause(
    *,
    event_type: str | None = None,
    team: str | None = None,
    subtype_contains: str | None = None,
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
    phase: str | None = None,
) -> tuple[list[str], list[Any]]:
    relation = str(relation).strip().lower()
    if relation not in {"exact", "before", "after", "around"}:
        raise ValueError("relation must be one of: exact, before, after, around.")

    if relation != "exact" and anchor_frame is None:
        raise ValueError("anchor_frame is required for before/after/around event lookups.")

    filters: list[str] = []
    params: list[Any] = []

    if event_type and str(event_type).strip():
        filters.append("UPPER(type) = UPPER(?)")
        params.append(str(event_type).strip())

    if team and str(team).strip():
        filters.append("UPPER(team) = UPPER(?)")
        params.append(str(team).strip())

    if subtype_contains and str(subtype_contains).strip():
        filters.append("UPPER(COALESCE(subtype, '')) LIKE UPPER(?)")
        params.append(f"%{str(subtype_contains).strip()}%")

    if period is not None:
        if not isinstance(period, int):
            raise TypeError("period must be an integer when provided.")
        filters.append("period = ?")
        params.append(period)

    normalized_zone = _normalize_pitch_zone(pitch_zone)
    if normalized_zone is not None:
        filters.append(PITCH_ZONE_SQL[normalized_zone])

    normalized_phase = _normalize_phase_label(phase)
    if normalized_phase is not None:
        filters.append("phase = ?")
        params.append(normalized_phase)

    if relation == "before":
        filters.append("start_frame < ?")
        params.append(anchor_frame)
    elif relation == "after":
        filters.append("start_frame > ?")
        params.append(anchor_frame)

    return filters, params


def _build_event_order_by_clause(relation: str, order: str) -> str:
    if relation == "around":
        return "ABS(start_frame - ?) ASC, period ASC, start_frame ASC"
    if relation == "before" or order == "last":
        return "period DESC, start_frame DESC"
    return "period ASC, start_frame ASC"


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
    phase: str | None = None,
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
        phase=phase,
    )
    order_by_clause = _build_event_order_by_clause(relation=relation, order=order)
    if relation == "around":
        params.append(anchor_frame)

    query = f"""
        SELECT
            team,
            type,
            subtype,
            period,
            start_frame,
            start_time_s,
            end_frame,
            end_time_s,
            from_player,
            to_player,
            start_x,
            start_y,
            end_x,
            end_y,
            phase
        FROM ({_event_source_sql()}) AS event_rows
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
            "phase": phase,
        }
        raise ValueError(f"No matching event found for {filters_used}.")

    event = _build_event_dict(row)
    event["occurrence"] = occurrence
    event["order"] = order
    event["relation"] = relation
    event["anchor_frame"] = anchor_frame
    event["period_filter"] = period
    event["pitch_zone"] = _normalize_pitch_zone(pitch_zone)
    event["phase_filter"] = _normalize_phase_label(phase)
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
    phase: str | None = None,
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
        phase=phase,
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
    phase: str | None = None,
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
        phase=phase,
    )
    order_by_clause = _build_event_order_by_clause(relation=relation, order="first")
    if relation == "around":
        params.append(anchor_frame)

    where_clause = " AND ".join(filters) if filters else "1=1"
    query = f"""
        SELECT
            team,
            type,
            subtype,
            period,
            start_frame,
            start_time_s,
            end_frame,
            end_time_s,
            from_player,
            to_player,
            start_x,
            start_y,
            end_x,
            end_y,
            phase
        FROM ({_event_source_sql()}) AS event_rows
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
    normalized_phase = _normalize_phase_label(phase)
    for event in events:
        event["period_filter"] = period
        event["pitch_zone"] = normalized_zone
        event["phase_filter"] = normalized_phase
    return events


def count_events(
    event_type: str | None = None,
    team: str | None = None,
    subtype_contains: str | None = None,
    relation: str = "exact",
    anchor_frame: int | None = None,
    period: int | None = None,
    pitch_zone: str | None = None,
    phase: str | None = None,
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
        phase=phase,
    )
    where_clause = " AND ".join(filters) if filters else "1=1"

    query = f"""
        SELECT COUNT(*)
        FROM ({_event_source_sql()}) AS event_rows
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
            team,
            type,
            subtype,
            period,
            start_frame,
            start_time_s,
            end_frame,
            end_time_s,
            from_player,
            to_player,
            start_x,
            start_y,
            end_x,
            end_y,
            phase
        FROM ({event_source_sql}) AS event_rows
        WHERE start_frame BETWEEN ? AND ?
        ORDER BY start_frame ASC
        LIMIT ?
    """.format(event_source_sql=_event_source_sql())

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
