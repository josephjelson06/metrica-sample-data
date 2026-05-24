from __future__ import annotations

from collections import Counter
import time
from math import hypot
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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
ComparableMetricValue = float | int | None


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


def _average(values: list[float]) -> float:
    return sum(values) / len(values)


def _average_nearest_teammate_distance(points: list[CoordinatePoint]) -> float:
    if len(points) < 2:
        return 0.0

    total_distance = 0.0
    for index, point in enumerate(points):
        other_points = [other_point for other_index, other_point in enumerate(points) if other_index != index]
        nearest_distance = min(hypot(point[0] - other_point[0], point[1] - other_point[1]) for other_point in other_points)
        total_distance += nearest_distance

    return total_distance / len(points)


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
            "line_height_proxy": None,
            "deep_unit_x": None,
            "middle_unit_x": None,
            "high_unit_x": None,
            "team_length_proxy": None,
            "deep_to_mid_spacing": None,
            "mid_to_high_spacing": None,
            "largest_x_gap": None,
            "average_nearest_teammate_distance": None,
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
    sorted_x_values = sorted(x_values)
    deep_unit_values = sorted_x_values[:3]
    middle_unit_values = sorted_x_values[3:8]
    high_unit_values = sorted_x_values[8:]
    deep_unit_x = _average(deep_unit_values)
    middle_unit_x = _average(middle_unit_values)
    high_unit_x = _average(high_unit_values)
    deep_to_mid_spacing = middle_unit_x - deep_unit_x
    mid_to_high_spacing = high_unit_x - middle_unit_x
    largest_x_gap = max(
        sorted_x_values[index + 1] - sorted_x_values[index]
        for index in range(len(sorted_x_values) - 1)
    )
    average_nearest_distance = _average_nearest_teammate_distance(points)

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
        "line_height_proxy": deep_unit_x,
        "deep_unit_x": deep_unit_x,
        "middle_unit_x": middle_unit_x,
        "high_unit_x": high_unit_x,
        "team_length_proxy": high_unit_x - deep_unit_x,
        "deep_to_mid_spacing": deep_to_mid_spacing,
        "mid_to_high_spacing": mid_to_high_spacing,
        "largest_x_gap": largest_x_gap,
        "average_nearest_teammate_distance": average_nearest_distance,
    }


def calculate_spatial_danger_grid(frame: int) -> dict[str, Any]:
    coordinates = get_tracking_frame(frame)
    if not coordinates:
        return {}

    home_points = []
    away_points = []
    for k, pt in coordinates.items():
        if pt.get("x") is not None and pt.get("y") is not None:
            if k.startswith("Home_"):
                home_points.append((float(pt["x"]), float(pt["y"])))
            elif k.startswith("Away_"):
                away_points.append((float(pt["x"]), float(pt["y"])))

    grid = []
    rows, cols = 15, 20
    for r in range(rows):
        y_center = (r + 0.5) / rows
        for c in range(cols):
            x_center = (c + 0.5) / cols
            
            home_dist = min([hypot(x_center - hx, y_center - hy) for hx, hy in home_points]) if home_points else 999.0
            away_dist = min([hypot(x_center - ax, y_center - ay) for ax, ay in away_points]) if away_points else 999.0
            
            control = "Home" if home_dist < away_dist else "Away"
            
            home_threat = max(0, 1 - hypot(x_center - 1.0, y_center - 0.5) * 1.5)
            away_threat = max(0, 1 - hypot(x_center - 0.0, y_center - 0.5) * 1.5)
            
            score = float(home_threat if control == "Home" else away_threat)
            
            grid.append({
                "x": c,
                "y": r,
                "control": control,
                "score": score
            })
            
    return {
        "frame": frame,
        "grid": grid,
        "rows": rows,
        "cols": cols
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


def compare_team_metrics_between_frames(start_frame: int, end_frame: int, team: str) -> dict[str, Any]:
    start_metrics = get_frame_team_metrics(start_frame, team)
    end_metrics = get_frame_team_metrics(end_frame, team)
    if not start_metrics or not end_metrics:
        return {}

    comparable_metrics = [
        "width",
        "depth",
        "centroid_x",
        "centroid_y",
        "bounding_box_area",
        "hull_area",
        "average_distance_to_centroid",
        "compactness_area",
        "line_height_proxy",
        "deep_unit_x",
        "middle_unit_x",
        "high_unit_x",
        "team_length_proxy",
        "deep_to_mid_spacing",
        "mid_to_high_spacing",
        "largest_x_gap",
        "average_nearest_teammate_distance",
    ]

    deltas: dict[str, ComparableMetricValue] = {}
    for metric_name in comparable_metrics:
        start_value = start_metrics.get(metric_name)
        end_value = end_metrics.get(metric_name)
        if start_value is None or end_value is None:
            deltas[metric_name] = None
            continue
        deltas[metric_name] = float(end_value) - float(start_value)

    return {
        "team": team.title(),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "start_metrics": start_metrics,
        "end_metrics": end_metrics,
        "deltas": deltas,
    }


def compare_frame_structures(start_frame: int, end_frame: int, team: str | None = None) -> dict[str, Any]:
    if team is not None:
        return compare_team_metrics_between_frames(start_frame=start_frame, end_frame=end_frame, team=team)

    return {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "Home": compare_team_metrics_between_frames(start_frame=start_frame, end_frame=end_frame, team="Home"),
        "Away": compare_team_metrics_between_frames(start_frame=start_frame, end_frame=end_frame, team="Away"),
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


def _enrich_with_kinematics(window_frames: list[dict[str, Any]]) -> None:
    pitch_length = 105.0
    pitch_width = 68.0

    for i in range(1, len(window_frames)):
        prev_frame_data = window_frames[i - 1]
        curr_frame_data = window_frames[i]
        
        time_delta = (curr_frame_data["frame"] - prev_frame_data["frame"]) / FRAMES_PER_SECOND
        if time_delta <= 0:
            continue
            
        prev_coords = prev_frame_data["coordinates"]
        for player_name, point in curr_frame_data["coordinates"].items():
            prev_point = prev_coords.get(player_name)
            if not prev_point:
                continue
                
            curr_x, curr_y = point.get("x"), point.get("y")
            prev_x, prev_y = prev_point.get("x"), prev_point.get("y")
            
            if curr_x is None or curr_y is None or prev_x is None or prev_y is None:
                continue
                
            vx_normalized = (float(curr_x) - float(prev_x)) / time_delta
            vy_normalized = (float(curr_y) - float(prev_y)) / time_delta
            
            vx_meters = vx_normalized * pitch_length
            vy_meters = vy_normalized * pitch_width
            speed = hypot(vx_meters, vy_meters)
            
            point["vx"] = vx_meters
            point["vy"] = vy_meters
            point["speed"] = speed


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

        _enrich_with_kinematics(window_frames)
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
        "sequence_type": "event",
        "frame_step": frame_step,
        "frames_per_second": FRAMES_PER_SECOND,
        "frames": frames,
        "events": events,
    }


def get_buildup_tracking_window(
    event_frame: int,
    frames_before: int = FRAMES_PER_SECOND * 12,
    frames_after: int = FRAMES_PER_SECOND * 2,
    frame_step: int = 1,
) -> dict[str, Any]:
    window = get_event_tracking_window(
        event_frame=event_frame,
        frames_before=frames_before,
        frames_after=frames_after,
        frame_step=frame_step,
    )
    window["sequence_type"] = "buildup"
    return window


def get_transition_tracking_window(
    event_frame: int,
    frames_before: int = FRAMES_PER_SECOND * 1,
    frames_after: int = FRAMES_PER_SECOND * 8,
    frame_step: int = 1,
) -> dict[str, Any]:
    window = get_event_tracking_window(
        event_frame=event_frame,
        frames_before=frames_before,
        frames_after=frames_after,
        frame_step=frame_step,
    )
    window["sequence_type"] = "transition"
    return window


def _normalize_optional_team(team: str | None) -> str | None:
    if team is None:
        return None

    normalized_team = str(team).strip().title()
    if normalized_team not in {"Home", "Away"}:
        raise ValueError("team must be either 'Home' or 'Away'.")
    return normalized_team


def _summarize_counts_by_type(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(event.get("type", "EVENT")).upper() for event in events)
    return dict(counts)


def _compact_event_summary(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None

    return {
        "team": event.get("team"),
        "type": event.get("type"),
        "subtype": event.get("subtype"),
        "frame": int(event.get("start_frame", event.get("frame", 0))),
        "time_s": event.get("start_time_s"),
        "phase": event.get("phase"),
    }


def segment_sequence_events(
    events: list[dict[str, Any]],
    anchor_frame: int,
    team: str | None = None,
) -> dict[str, Any]:
    if not isinstance(anchor_frame, int):
        raise TypeError("anchor_frame must be an integer.")

    normalized_team = _normalize_optional_team(team)
    ordered_events = sorted(events, key=lambda event: int(event.get("start_frame", event.get("frame", 0))))
    before_events = [
        event for event in ordered_events if int(event.get("start_frame", event.get("frame", 0))) < anchor_frame
    ]
    anchor_events = [
        event for event in ordered_events if int(event.get("start_frame", event.get("frame", 0))) == anchor_frame
    ]
    after_events = [
        event for event in ordered_events if int(event.get("start_frame", event.get("frame", 0))) > anchor_frame
    ]

    result: dict[str, Any] = {
        "anchor_frame": anchor_frame,
        "team": normalized_team,
        "before_events_count": len(before_events),
        "anchor_events_count": len(anchor_events),
        "after_events_count": len(after_events),
        "before_counts_by_type": _summarize_counts_by_type(before_events),
        "anchor_counts_by_type": _summarize_counts_by_type(anchor_events),
        "after_counts_by_type": _summarize_counts_by_type(after_events),
        "immediate_pre_event": _compact_event_summary(before_events[-1] if before_events else None),
        "immediate_post_event": _compact_event_summary(after_events[0] if after_events else None),
    }

    if normalized_team is None:
        return result

    same_team_before = [event for event in before_events if event.get("team") == normalized_team]
    same_team_anchor = [event for event in anchor_events if event.get("team") == normalized_team]
    same_team_after = [event for event in after_events if event.get("team") == normalized_team]
    opponent_before = [event for event in before_events if event.get("team") not in {None, normalized_team}]
    opponent_after = [event for event in after_events if event.get("team") not in {None, normalized_team}]

    first_same_team_shot_after = next(
        (event for event in same_team_after if str(event.get("type", "")).upper() == "SHOT"),
        None,
    )
    first_same_team_shot_before = next(
        (event for event in reversed(same_team_before) if str(event.get("type", "")).upper() == "SHOT"),
        None,
    )
    first_opponent_after = opponent_after[0] if opponent_after else None

    continuation_events = same_team_after
    if first_opponent_after is not None:
        first_opponent_after_frame = int(first_opponent_after.get("start_frame", first_opponent_after.get("frame", 0)))
        continuation_events = [
            event
            for event in same_team_after
            if int(event.get("start_frame", event.get("frame", 0))) < first_opponent_after_frame
        ]

    result.update(
        {
            "same_team_before_count": len(same_team_before),
            "same_team_anchor_count": len(same_team_anchor),
            "same_team_after_count": len(same_team_after),
            "opponent_before_count": len(opponent_before),
            "opponent_after_count": len(opponent_after),
            "same_team_before_counts_by_type": _summarize_counts_by_type(same_team_before),
            "same_team_after_counts_by_type": _summarize_counts_by_type(same_team_after),
            "continuation_count_before_opponent": len(continuation_events),
            "continuation_counts_by_type": _summarize_counts_by_type(continuation_events),
            "last_same_team_before_event": _compact_event_summary(same_team_before[-1] if same_team_before else None),
            "first_same_team_after_event": _compact_event_summary(same_team_after[0] if same_team_after else None),
            "first_opponent_after_event": _compact_event_summary(first_opponent_after),
            "first_same_team_shot_after": _compact_event_summary(first_same_team_shot_after),
            "last_same_team_shot_before": _compact_event_summary(first_same_team_shot_before),
        }
    )
    return result


def summarize_team_event_chain(events: list[dict[str, Any]], team: str, anchor_frame: int) -> dict[str, Any]:
    normalized_team = _normalize_optional_team(team)
    if normalized_team is None:
        raise ValueError("team must be either 'Home' or 'Away'.")

    team_events = [
        event
        for event in events
        if event.get("team") == normalized_team and int(event.get("start_frame", event.get("frame", 0))) >= anchor_frame
    ]
    if not team_events:
        return {
            "team": normalized_team,
            "anchor_frame": anchor_frame,
            "event_count": 0,
            "counts_by_type": {},
            "window_seconds": 0.0,
            "first_shot_seconds_from_anchor": None,
            "last_event_type": None,
        }

    counts_by_type = Counter(str(event.get("type", "EVENT")).upper() for event in team_events)
    first_shot = next((event for event in team_events if str(event.get("type", "")).upper() == "SHOT"), None)
    first_shot_seconds_from_anchor = None
    if first_shot is not None:
        first_shot_seconds_from_anchor = (
            int(first_shot["start_frame"]) - anchor_frame
        ) / FRAMES_PER_SECOND

    last_event = team_events[-1]
    return {
        "team": normalized_team,
        "anchor_frame": anchor_frame,
        "event_count": len(team_events),
        "counts_by_type": dict(counts_by_type),
        "window_seconds": (int(last_event["start_frame"]) - anchor_frame) / FRAMES_PER_SECOND,
        "first_shot_seconds_from_anchor": first_shot_seconds_from_anchor,
        "last_event_type": str(last_event.get("type", "")).upper() or None,
    }


def compare_sequence_segments(
    left_segments: dict[str, Any],
    right_segments: dict[str, Any],
) -> dict[str, Any]:
    comparable_counts = [
        "before_events_count",
        "after_events_count",
        "same_team_before_count",
        "same_team_after_count",
        "opponent_before_count",
        "opponent_after_count",
        "continuation_count_before_opponent",
    ]

    deltas: dict[str, int | None] = {}
    for metric_name in comparable_counts:
        left_value = left_segments.get(metric_name)
        right_value = right_segments.get(metric_name)
        if left_value is None or right_value is None:
            deltas[metric_name] = None
            continue
        deltas[metric_name] = int(right_value) - int(left_value)

    return {
        "left_segments": left_segments,
        "right_segments": right_segments,
        "deltas": deltas,
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

    window = get_tracking_window(start_frame=target_frame - 1, end_frame=target_frame, frame_step=1)
    for frame_data in window:
        if frame_data["frame"] == target_frame:
            return frame_data["coordinates"]
    return {}


def get_physicality_summary(period: int, team: str) -> dict[str, Any]:
    normalized_team = team.strip().title()
    connection = _connect()
    try:
        cols = _get_tracking_coordinate_columns(connection)
        team_cols = [c for c in cols if c.startswith(normalized_team)]
        players = set([c.rsplit("_", 1)[0] for c in team_cols])
        
        stats = {}
        for player in players:
            x_col = f'"{player}_x"'
            y_col = f'"{player}_y"'
            
            query = f"""
            WITH frame_data AS (
                SELECT 
                    "Frame", 
                    "Time [s]" as t,
                    {x_col} as x, 
                    {y_col} as y
                FROM read_parquet(?)
                WHERE "Period" = ? AND {x_col} IS NOT NULL
                ORDER BY "Frame" ASC
            ),
            kinematics AS (
                SELECT
                    "Frame",
                    x, y,
                    t,
                    (x - LAG(x) OVER (ORDER BY "Frame")) * 105.0 as dx,
                    (y - LAG(y) OVER (ORDER BY "Frame")) * 68.0 as dy,
                    (t - LAG(t) OVER (ORDER BY "Frame")) as dt
                FROM frame_data
            ),
            speeds AS (
                SELECT
                    SQRT(dx*dx + dy*dy) as dist,
                    SQRT(dx*dx + dy*dy) / dt as speed
                FROM kinematics
                WHERE dt > 0 AND dist IS NOT NULL
            )
            SELECT
                SUM(dist) as total_distance,
                SUM(CASE WHEN speed > 5.5 THEN dist ELSE 0 END) as hsr_distance,
                SUM(CASE WHEN speed > 7.0 THEN dist ELSE 0 END) as sprint_distance
            FROM speeds
            """
            row = connection.execute(query, [str(TRACKING_PARQUET_PATH), period]).fetchone()
            if row and row[0] is not None:
                stats[player] = {
                    "total_distance": float(row[0]),
                    "hsr_distance": float(row[1]),
                    "sprint_distance": float(row[2])
                }
                
        return {
            "period": period,
            "team": normalized_team,
            "players": stats
        }
    finally:
        connection.close()


def get_pass_network(team: str, period: int | None = None) -> dict[str, Any]:
    normalized_team = _normalize_optional_team(team)
    if not normalized_team:
        raise ValueError("Team is required for pass network.")

    events = list_events(event_type="PASS", team=normalized_team, period=period, limit=1000)
    
    nodes: dict[str, dict[str, Any]] = {}
    edges_map: dict[tuple[str, str], int] = {}
    
    for event in events:
        from_p = event.get("from_player")
        to_p = event.get("to_player")
        x = event.get("start_x")
        y = event.get("start_y")
        
        if not from_p or not x or not y:
            continue
            
        if from_p not in nodes:
            nodes[from_p] = {"x_sum": 0.0, "y_sum": 0.0, "passes_made": 0, "passes_received": 0}
            
        nodes[from_p]["x_sum"] += float(x)
        nodes[from_p]["y_sum"] += float(y)
        nodes[from_p]["passes_made"] += 1
        
        if to_p:
            if to_p not in nodes:
                nodes[to_p] = {"x_sum": 0.0, "y_sum": 0.0, "passes_made": 0, "passes_received": 0}
            nodes[to_p]["passes_received"] += 1
            
            edge = (from_p, to_p)
            edges_map[edge] = edges_map.get(edge, 0) + 1
            
    final_nodes = {}
    for p, data in nodes.items():
        if data["passes_made"] > 0:
            final_nodes[p] = {
                "x": data["x_sum"] / data["passes_made"],
                "y": data["y_sum"] / data["passes_made"],
                "passes_made": data["passes_made"],
                "passes_received": data["passes_received"]
            }
        else:
            final_nodes[p] = {
                "x": None,
                "y": None,
                "passes_made": 0,
                "passes_received": data["passes_received"]
            }
            
    edges = [{"from": f, "to": t, "pass_count": c} for (f, t), c in edges_map.items()]
    
    return {
        "team": normalized_team,
        "period": period,
        "nodes": final_nodes,
        "edges": edges,
    }


def get_pass_sonars(team: str, period: int | None = None) -> dict[str, Any]:
    import math
    normalized_team = _normalize_optional_team(team)
    if not normalized_team:
        raise ValueError("Team is required for pass sonars.")

    events = list_events(event_type="PASS", team=normalized_team, period=period, limit=1000)
    
    sonars: dict[str, Any] = {}
    for event in events:
        from_p = event.get("from_player")
        x1 = event.get("start_x")
        y1 = event.get("start_y")
        x2 = event.get("end_x")
        y2 = event.get("end_y")
        
        if not from_p or x1 is None or y1 is None or x2 is None or y2 is None:
            continue
            
        dx = float(x2) - float(x1)
        dy = float(y2) - float(y1)
        
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360
            
        bucket = int((angle_deg + 22.5) // 45) % 8
        dist = math.hypot(dx, dy)
        
        if from_p not in sonars:
            sonars[from_p] = {"x_sum": 0.0, "y_sum": 0.0, "passes": 0, "buckets": [0] * 8, "bucket_dist": [0.0] * 8}
            
        sonars[from_p]["x_sum"] += float(x1)
        sonars[from_p]["y_sum"] += float(y1)
        sonars[from_p]["passes"] += 1
        sonars[from_p]["buckets"][bucket] += 1
        sonars[from_p]["bucket_dist"][bucket] += dist

    for p in sonars:
        sonars[p]["x"] = sonars[p]["x_sum"] / sonars[p]["passes"]
        sonars[p]["y"] = sonars[p]["y_sum"] / sonars[p]["passes"]
        for b in range(8):
            if sonars[p]["buckets"][b] > 0:
                sonars[p]["bucket_dist"][b] /= sonars[p]["buckets"][b]
            
    return {"team": normalized_team, "period": period, "sonars": sonars}


def find_dangerous_transitions(team: str) -> list[dict[str, Any]]:
    # This heuristic engine scans the tracking parquet to find moments where:
    # 1. The team has players sprinting (speed > 6.0 m/s)
    # 2. It happens quickly over a short window
    # 3. We return the timestamp and frame.
    normalized_team = _normalize_optional_team(team)
    if not normalized_team:
        raise ValueError("Team is required for pattern recognition.")
        
    connection = _connect()
    try:
        cols = _get_tracking_coordinate_columns(connection)
        team_cols = [c for c in cols if c.startswith(normalized_team)]
        players = set([c.rsplit("_", 1)[0] for c in team_cols])
        
        # Build an efficient duckdb query to find high velocity frames for the team
        query = f"""
        WITH player_data AS (
            SELECT 
                "Frame", "Period", "Time [s]" as t,
        """
        for i, player in enumerate(players):
            query += f' "{player}_x" as x{i}, "{player}_y" as y{i},'
        query = query.rstrip(",") + """
            FROM read_parquet(?)
        ),
        velocities AS (
            SELECT "Frame", "Period", t,
        """
        for i in range(len(players)):
            query += f"""
                SQRT(POWER((x{i} - LAG(x{i}) OVER (ORDER BY "Frame")) * 105.0, 2) + 
                     POWER((y{i} - LAG(y{i}) OVER (ORDER BY "Frame")) * 68.0, 2)) / 
                NULLIF((t - LAG(t) OVER (ORDER BY "Frame")), 0) as v{i},
            """
        query = query.rstrip(",\n ") + """
            FROM player_data
        )
        SELECT "Frame", "Period", t
        FROM velocities
        WHERE (
        """
        conditions = [f"(v{i} > 6.5)" for i in range(len(players))]
        query += " OR ".join(conditions) + """)
        ORDER BY "Frame" ASC
        """
        
        rows = connection.execute(query, [str(TRACKING_PARQUET_PATH)]).fetchall()
        
        # Group contiguous frames into transition events
        transitions = []
        current_transition = None
        
        for row in rows:
            frame = int(row[0])
            period = int(row[1])
            time_s = float(row[2])
            
            if current_transition is None:
                current_transition = {"start_frame": frame, "end_frame": frame, "period": period, "start_time": time_s, "end_time": time_s}
            else:
                if frame - current_transition["end_frame"] < 25: # Within 1 second (at 25 fps)
                    current_transition["end_frame"] = frame
                    current_transition["end_time"] = time_s
                else:
                    if current_transition["end_frame"] - current_transition["start_frame"] > 25: # Lasted more than 1 sec
                        transitions.append(current_transition)
                    current_transition = {"start_frame": frame, "end_frame": frame, "period": period, "start_time": time_s, "end_time": time_s}
                    
        if current_transition and current_transition["end_frame"] - current_transition["start_frame"] > 25:
            transitions.append(current_transition)
            
        # Return top 10 longest/most intense transitions
        transitions.sort(key=lambda t: t["end_frame"] - t["start_frame"], reverse=True)
        return transitions[:10]
    finally:
        connection.close()


def analyze_set_piece(event: dict[str, Any]) -> dict[str, Any]:
    if not event:
        raise ValueError("Event is required for set piece analysis.")
        
    frame = int(event.get("frame", 0))
    tracking_data = get_tracking_frame(frame)
    
    attacking_team = event.get("team", "Home")
    defending_team = "Away" if attacking_team == "Home" else "Home"
    
    attackers = []
    defenders = []
    
    for player, coords in tracking_data.items():
        if player.startswith(attacking_team):
            attackers.append({"name": player, "x": coords["x"], "y": coords["y"]})
        elif player.startswith(defending_team):
            defenders.append({"name": player, "x": coords["x"], "y": coords["y"]})
            
    # Calculate pairwise distances to find marking pairs
    import math
    marking_pairs = []
    
    for attacker in attackers:
        if attacker["x"] is None or attacker["y"] is None:
            continue
            
        closest_defender = None
        min_dist = float('inf')
        
        for defender in defenders:
            if defender["x"] is None or defender["y"] is None:
                continue
                
            dist = math.hypot(defender["x"] - attacker["x"], defender["y"] - attacker["y"])
            if dist < min_dist:
                min_dist = dist
                closest_defender = defender
                
        if closest_defender and min_dist < 5.0: # Only count if within 5 meters (marking range)
            marking_pairs.append({
                "attacker": attacker["name"],
                "defender": closest_defender["name"],
                "distance": min_dist
            })
            
    return {
        "event": event,
        "frame": frame,
        "marking_pairs": marking_pairs,
        "coordinates": tracking_data
    }


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
