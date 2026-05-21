from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOME_CSV = PROJECT_ROOT / "data" / "Sample_Game_2" / "Sample_Game_2_RawTrackingData_Home_Team.csv"
DEFAULT_AWAY_CSV = PROJECT_ROOT / "data" / "Sample_Game_2" / "Sample_Game_2_RawTrackingData_Away_Team.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "parquet" / "metrica_tracking.parquet"


def normalize_tracking_columns(columns: pd.Index, team_prefix: str) -> list[str]:
    normalized: list[str] = []
    last_entity = ""

    for idx, name in enumerate(columns):
        text = str(name).strip()

        if idx < 3:
            normalized.append(text)
            continue

        is_x_column = (idx - 3) % 2 == 0
        axis = "x" if is_x_column else "y"

        if text and not text.startswith("Unnamed:"):
            last_entity = text

        if not last_entity:
            last_entity = f"col_{idx}"

        if last_entity == "Ball":
            normalized.append(f"Ball_{axis}")
        else:
            normalized.append(f"{team_prefix}_{last_entity}_{axis}")

    return normalized


def load_tracking_csv(csv_path: Path, team_prefix: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, header=2)
    df.columns = normalize_tracking_columns(df.columns, team_prefix=team_prefix)

    # Keep row-level missing values, but remove columns that are empty for the whole file.
    df = df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

    for column in ["Period", "Frame"]:
        if column not in df.columns:
            raise ValueError(f"Expected '{column}' column in {csv_path}.")
        df[column] = pd.to_numeric(df[column], errors="raise").astype("int64")

    if "Time [s]" in df.columns:
        df["Time [s]"] = pd.to_numeric(df["Time [s]"], errors="coerce")

    return df


def coalesce_duplicate_column(df: pd.DataFrame, base_column: str, duplicate_column: str) -> pd.DataFrame:
    if base_column in df.columns and duplicate_column in df.columns:
        df[base_column] = df[base_column].where(df[base_column].notna(), df[duplicate_column])
        df = df.drop(columns=[duplicate_column])
    return df


def merge_tracking_data(home_df: pd.DataFrame, away_df: pd.DataFrame) -> pd.DataFrame:
    merged = home_df.merge(
        away_df,
        on=["Period", "Frame"],
        how="inner",
        suffixes=("", "_awaydup"),
    )

    for column in ["Time [s]", "Ball_x", "Ball_y"]:
        merged = coalesce_duplicate_column(merged, column, f"{column}_awaydup")

    # Drop any leftover duplicate columns created by the merge.
    duplicate_columns = [column for column in merged.columns if column.endswith("_awaydup")]
    if duplicate_columns:
        merged = merged.drop(columns=duplicate_columns)

    merged = merged.dropna(axis=1, how="all")

    return merged


def convert_tracking_to_parquet(home_csv: Path, away_csv: Path, output_parquet: Path) -> None:
    home_df = load_tracking_csv(home_csv, team_prefix="Home")
    away_df = load_tracking_csv(away_csv, team_prefix="Away")
    merged_df = merge_tracking_data(home_df, away_df)

    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_parquet(
        output_parquet,
        engine="pyarrow",
        compression="zstd",
        compression_level=19,
        index=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge Metrica home and away tracking CSVs into one compressed Parquet file."
    )
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME_CSV, help="Home tracking CSV path.")
    parser.add_argument("--away", type=Path, default=DEFAULT_AWAY_CSV, help="Away tracking CSV path.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output Parquet path. Defaults to data/parquet/metrica_tracking.parquet",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convert_tracking_to_parquet(args.home, args.away, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
