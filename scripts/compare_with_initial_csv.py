#!/usr/bin/env python3
"""YAMLから生成したCSVと初回転記CSVを、全セル単位で照合する。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source_file:
        return list(csv.reader(source_file))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("initial_csv", type=Path)
    parser.add_argument("generated_csv", type=Path)
    arguments = parser.parse_args()

    initial_rows = read_csv(arguments.initial_csv)
    generated_rows = read_csv(arguments.generated_csv)

    if len(initial_rows) != len(generated_rows):
        raise SystemExit(
            f"行数不一致: 初回CSV={len(initial_rows):,}、生成CSV={len(generated_rows):,}"
        )

    differences: list[str] = []
    for row_number, (initial_row, generated_row) in enumerate(
        zip(initial_rows, generated_rows), start=1
    ):
        if initial_row == generated_row:
            continue
        for column_number, (initial_cell, generated_cell) in enumerate(
            zip(initial_row, generated_row), start=1
        ):
            if initial_cell != generated_cell:
                differences.append(
                    f"行{row_number} 列{column_number}: {initial_cell!r} != {generated_cell!r}"
                )
        if len(initial_row) != len(generated_row):
            differences.append(
                f"行{row_number}: 列数 {len(initial_row)} != {len(generated_row)}"
            )

    if differences:
        preview = "\n".join(differences[:20])
        raise SystemExit(f"{len(differences):,}セルの差異を検出しました。\n{preview}")

    print(f"全{len(initial_rows) - 1:,}件・{len(initial_rows[0])}列が一致しました。")


if __name__ == "__main__":
    main()

