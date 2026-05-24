"""Append new orientation + time-windowed primitives to db_engine.py."""
from pathlib import Path

NEW_CODE = '''

# ── ORIENTATION PRIMITIVES ────────────────────────────────────────────────────

def _infer_role(avg_x: float, avg_y: float) -> str:
    """Infers a rough role from average normalized x/y position."""
    if avg_x < 0.1 or avg_x > 0.9:
        return "GK"
    if avg_x < 0.35:
        return "FB" if (avg_y < 0.25 or avg_y > 0.75) else "CB"
    if avg_x < 0.6:
        if avg_y < 0.25 or avg_y > 0.75:
            return "WM"
        return "DM" if avg_x < 0.45 else "CM"
    if avg_y < 0.25 or avg_y > 0.75:
        return "W"
    return "ST" if avg_x > 0.75 else "AM"


def get_lineup_and_roles(team: str | None = None) -> dict[str, Any]:
    """
    Scans tracking data to find which player IDs were active,
    their average position, and inferred role labels.
    """
    _require_file(TRACKING_PARQUET_PATH, "Tracking parquet file")
    connection = _connect()
    try:
        cols = _get_tracking_coordinate_columns(connection)
        player_ids = list(set([c.rsplit("_", 1)[0] for c in cols if not c.startswith("Ball")]))

        lineup: dict[str, Any] = {}
        for player in player_ids:
            if team:
                normalized = team.strip().title()
                if not player.startswith(normalized):
                    continue

            x_col = f\'"{player}_x"\'
            y_col = f\'"{player}_y"\'

            row = connection.execute(f"""
                SELECT
                    AVG({x_col}) AS avg_x,
                    AVG({y_col}) AS avg_y,
                    COUNT(CASE WHEN period = 1 AND {x_col} IS NOT NULL THEN 1 END) AS frames_p1,
                    COUNT(CASE WHEN period = 2 AND {x_col} IS NOT NULL THEN 1 END) AS frames_p2,
                    MIN(CASE WHEN {x_col} IS NOT NULL THEN frame END) AS first_frame,
                    MAX(CASE WHEN {x_col} IS NOT NULL THEN frame END) AS last_frame
                FROM read_parquet(?)
            """, [str(TRACKING_PARQUET_PATH)]).fetchone()

            if not row or row[0] is None:
                continue

            avg_x, avg_y, frames_p1, frames_p2, first_frame, last_frame = row
            avg_x = float(avg_x)
            avg_y = float(avg_y)
            role = _infer_role(avg_x, avg_y)
            team_label = "Home" if player.startswith("Home") else "Away"

            lineup[player] = {
                "team": team_label,
                "role": role,
                "avg_x": round(avg_x, 4),
                "avg_y": round(avg_y, 4),
                "in_period_1": int(frames_p1) > 50,
                "in_period_2": int(frames_p2) > 50,
                "first_frame": int(first_frame) if first_frame else None,
                "last_frame": int(last_frame) if last_frame else None,
                "approx_start_min": round(int(first_frame) / FRAMES_PER_SECOND / 60, 1) if first_frame else None,
                "approx_end_min": round(int(last_frame) / FRAMES_PER_SECOND / 60, 1) if last_frame else None,
            }

        return {"team": team, "lineup": lineup}
    finally:
        connection.close()


def get_substitution_timeline() -> list[dict[str, Any]]:
    """Detects approximate substitution moments from tracking presence gaps."""
    lineup_data = get_lineup_and_roles()
    lineup = lineup_data["lineup"]

    all_first_frames = [p["first_frame"] for p in lineup.values() if p["first_frame"]]
    all_last_frames = [p["last_frame"] for p in lineup.values() if p["last_frame"]]
    if not all_first_frames or not all_last_frames:
        return []

    earliest_frame = min(all_first_frames)
    latest_frame = max(all_last_frames)
    p1_boundary = latest_frame * 0.52

    subs = []
    for player, info in lineup.items():
        if not info["first_frame"] or not info["last_frame"]:
            continue
        # Subbed on in period 2
        if info["in_period_2"] and not info["in_period_1"]:
            subs.append({
                "player": player, "team": info["team"], "role": info["role"],
                "event": "subbed_on", "approx_minute": info["approx_start_min"], "period": 2,
            })
        elif info["in_period_1"] and info["first_frame"] > earliest_frame + (FRAMES_PER_SECOND * 120):
            subs.append({
                "player": player, "team": info["team"], "role": info["role"],
                "event": "subbed_on", "approx_minute": info["approx_start_min"], "period": 1,
            })
        if info["in_period_1"] and not info["in_period_2"] and info["last_frame"] < p1_boundary - (FRAMES_PER_SECOND * 120):
            subs.append({
                "player": player, "team": info["team"], "role": info["role"],
                "event": "subbed_off", "approx_minute": info["approx_end_min"], "period": 1,
            })

    subs.sort(key=lambda s: s.get("approx_minute") or 0)
    return subs


def get_formation_estimate(team: str, period: int | None = None) -> dict[str, Any]:
    """Estimates a formation string (e.g. \'4-3-3\') from average player positions."""
    lineup_data = get_lineup_and_roles(team=team)
    lineup = lineup_data["lineup"]

    players = [
        info for info in lineup.values()
        if info["role"] != "GK" and (
            period is None
            or (period == 1 and info["in_period_1"])
            or (period == 2 and info["in_period_2"])
        )
    ]

    if len(players) < 7:
        return {"team": team, "period": period, "formation": "unknown", "avg_positions": []}

    players_sorted = sorted(players, key=lambda p: p["avg_x"])
    n = len(players_sorted)
    defense = players_sorted[: n // 3]
    midfield = players_sorted[n // 3 : 2 * n // 3]
    attack = players_sorted[2 * n // 3 :]
    formation = f"{len(defense)}-{len(midfield)}-{len(attack)}"

    avg_positions = [
        {"role": p["role"], "avg_x": p["avg_x"], "avg_y": p["avg_y"]}
        for p in players_sorted
    ]
    return {"team": team, "period": period, "formation": formation, "avg_positions": avg_positions}


# ── TIME-WINDOWED PASS NETWORK ────────────────────────────────────────────────

def get_pass_network_windowed(
    team: str,
    period: int | None = None,
    start_minute: float | None = None,
    end_minute: float | None = None,
) -> dict[str, Any]:
    """Pass network optionally filtered to a specific minute window."""
    normalized_team = _normalize_optional_team(team)
    if not normalized_team:
        raise ValueError("Team is required for pass network.")

    events = list_events(event_type="PASS", team=normalized_team, period=period, limit=5000)

    start_s = start_minute * 60 if start_minute is not None else None
    end_s = end_minute * 60 if end_minute is not None else None
    if start_s is not None:
        events = [e for e in events if (e.get("start_time_s") or 0) >= start_s]
    if end_s is not None:
        events = [e for e in events if (e.get("start_time_s") or 0) <= end_s]

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
            edges_map[(from_p, to_p)] = edges_map.get((from_p, to_p), 0) + 1

    final_nodes = {}
    for p, data in nodes.items():
        if data["passes_made"] > 0:
            final_nodes[p] = {
                "x": data["x_sum"] / data["passes_made"],
                "y": data["y_sum"] / data["passes_made"],
                "passes_made": data["passes_made"],
                "passes_received": data["passes_received"],
            }
        elif data["passes_received"] > 0:
            final_nodes[p] = {"x": None, "y": None, "passes_made": 0, "passes_received": data["passes_received"]}

    edges = [{"from": f, "to": t, "pass_count": c} for (f, t), c in edges_map.items()]
    return {
        "team": normalized_team,
        "period": period,
        "start_minute": start_minute,
        "end_minute": end_minute,
        "nodes": final_nodes,
        "edges": edges,
        "total_passes": sum(d["passes_made"] for d in final_nodes.values()),
    }
'''

path = Path("backend/tools/db_engine.py")
content = path.read_text(encoding="utf-8")

# Remove the existing __main__ block and append new code + fresh __main__
MAIN_MARKER = 'if __name__ == "__main__":'
idx = content.rfind(MAIN_MARKER)
if idx != -1:
    content = content[:idx].rstrip()

content += NEW_CODE

MAIN_BLOCK = '''

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
'''

content += MAIN_BLOCK
path.write_text(content, encoding="utf-8")
print("Done! Lines:", len(content.splitlines()))
