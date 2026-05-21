from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def normalize_tracking_columns(columns: pd.Index) -> list[str]:
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

        normalized.append(f"{last_entity}_{axis}")

    return normalized


def convert_csv_to_parquet(input_csv: Path, output_parquet: Path) -> None:
    df = pd.read_csv(input_csv, header=2)
    df.columns = normalize_tracking_columns(df.columns)

    # Keep row-level missing values because they can indicate unavailable tracking samples,
    # but drop columns that are completely empty for the whole file.
    df = df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

    if "Frame" not in df.columns:
        raise ValueError("Expected a 'Frame' column in the tracking CSV.")

    df["Frame"] = pd.to_numeric(df["Frame"], errors="raise").astype("int64")

    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(
        output_parquet,
        engine="pyarrow",
        compression="zstd",
        compression_level=19,
        index=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Metrica tracking CSV to a compressed Parquet file."
    )
    parser.add_argument("input_csv", type=Path, help="Path to the Metrica tracking CSV file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "parquet" / "metrica_tracking_single.parquet",
        help="Output Parquet path. Defaults to data/parquet/metrica_tracking_single.parquet",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convert_csv_to_parquet(args.input_csv, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
