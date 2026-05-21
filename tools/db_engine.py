from __future__ import annotations

import time
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "parquet" / "metrica_tracking.parquet"


def get_player_coordinates_for_frame(target_frame: int) -> dict[str, dict[str, float | int | None]]:
    if not isinstance(target_frame, int):
        raise TypeError("target_frame must be an integer.")

    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Parquet file not found at {PARQUET_PATH}. "
            "This function expects the merged tracking file inside data/parquet."
        )

    connection = duckdb.connect(database=":memory:")
    try:
        columns_info = connection.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(PARQUET_PATH)],
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
        row = connection.execute(query, [str(PARQUET_PATH), target_frame]).fetchone()

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
    coordinates = get_player_coordinates_for_frame(1500)
    elapsed = time.perf_counter() - start

    print(coordinates)
    print(f"Execution time: {elapsed:.6f} seconds")
