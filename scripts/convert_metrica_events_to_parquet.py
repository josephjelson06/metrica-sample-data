from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def convert_csv_to_parquet(input_csv: Path, output_parquet: Path) -> None:
    df = pd.read_csv(input_csv)

    # Drop only columns that are empty for the full file. Keep row-level NaN values.
    df = df.dropna(axis=1, how="all")

    for column in ["Period", "Start Frame", "End Frame"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="raise").astype("int64")

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
        description="Convert a Metrica events CSV to a compressed Parquet file."
    )
    parser.add_argument("input_csv", type=Path, help="Path to the Metrica events CSV file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "parquet" / "metrica_events.parquet",
        help="Output Parquet path. Defaults to data/parquet/metrica_events.parquet",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convert_csv_to_parquet(args.input_csv, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
