#!/usr/bin/env python3
"""初回転記CSVを刊行物別YAMLへ一度だけ移行する。

このスクリプトは正本移行の来歴を残すためのもの。移行後の日常的な修正は、
CSVではなく data/toc/*.yaml に対して行う。
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


# ==========================================
# 刊行物とファイル名
# ==========================================

PUBLICATION_FILE_NAMES = {
    "新刊": "no-new.yaml",
    "1": "no-01.yaml",
    "2": "no-02.yaml",
    "3": "no-03.yaml",
    "4": "no-04.yaml",
    "5": "no-05.yaml",
    "6": "no-06.yaml",
    "7": "no-07.yaml",
    "8": "no-08.yaml",
    "9": "no-09.yaml",
}

PARENT_PAGE_NOTE = re.compile(
    r"^目次に個別開始ページの記載なし（親見出しの開始ページは(?P<page>\d+)）$"
)


class IndentedSafeDumper(yaml.SafeDumper):
    """配列にも字下げを付け、人が階層を追いやすいYAMLを出力する。"""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


# ==========================================
# CSVの値をYAMLの型へ変換
# ==========================================

def nullable_text(value: str) -> str | None:
    """空文字は欠損値として扱い、目次に書かれた文字列とは区別する。"""

    return value if value != "" else None


def heading_level(row: dict[str, str]) -> str:
    """CSVの3階層から、その行自身が表す見出し階層を判定する。"""

    if row["項見出し"]:
        return "item"
    if row["節見出し"]:
        return "section"
    if row["章見出し"]:
        return "chapter"
    raise ValueError(f"見出しが空の行を検出しました: {row}")


def uncertain_fields(note: str) -> list[str]:
    """人間向けの備考を、検証対象となるYAMLキーへ対応させる。"""

    fields: list[str] = []
    if "表題" in note or "綱衣" in note:
        fields.append("item")
    if "開始ページ" in note:
        fields.append("start_page")
    return fields


def page_information(row: dict[str, str]) -> tuple[int | None, dict[str, Any]]:
    """開始ページと、目次上でのページ記載状態を分離する。"""

    note = row["備考"]
    if note == "目次に開始ページの記載なし":
        return None, {"status": "not_listed"}

    parent_match = PARENT_PAGE_NOTE.fullmatch(note)
    if parent_match:
        return None, {
            "status": "parent_only",
            "parent_start_page": int(parent_match.group("page")),
        }

    start_page = int(row["開始ページ"]) if row["開始ページ"] else None
    if start_page is None:
        return None, {"status": "not_listed"}
    return start_page, {"status": "stated"}


def entry_from_row(row: dict[str, str], sequence: int) -> dict[str, Any]:
    """CSVの1行を、安定IDを持つ目次項目へ変換する。"""

    no_token = "new" if row["No"] == "新刊" else f"{int(row['No']):02d}"
    start_page, page_reference = page_information(row)

    entry: dict[str, Any] = {
        "id": f"naka-toc-{no_token}-{sequence:04d}",
        "sequence": sequence,
        "heading_level": heading_level(row),
        "volume": nullable_text(row["巻号"]),
        "chapter": nullable_text(row["章見出し"]),
        "section": nullable_text(row["節見出し"]),
        "item": nullable_text(row["項見出し"]),
        "start_page": start_page,
        "page_reference": page_reference,
    }

    if "不確実性あり" in row["備考"]:
        entry["verification"] = {
            "status": "uncertain",
            "fields": uncertain_fields(row["備考"]),
            "note": row["備考"],
        }

    return entry


# ==========================================
# 刊行物別YAMLの生成
# ==========================================

def migrate(source_csv: Path, output_directory: Path) -> None:
    with source_csv.open("r", encoding="utf-8-sig", newline="") as source_file:
        rows = list(csv.DictReader(source_file))

    grouped_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped_rows[row["No"]].append(row)

    output_directory.mkdir(parents=True, exist_ok=True)
    for publication_no, file_name in PUBLICATION_FILE_NAMES.items():
        publication_rows = grouped_rows[publication_no]
        if not publication_rows:
            raise ValueError(f"No{publication_no} の行がありません。")

        first_row = publication_rows[0]
        document = {
            "publication": {
                "publication_number": publication_no,
                "title": first_row["タイトル"],
                "source_pdf_url": first_row["参照PDF URL"],
            },
            "entries": [
                entry_from_row(row, sequence)
                for sequence, row in enumerate(publication_rows, start=1)
            ],
        }

        output_path = output_directory / file_name
        output_path.write_text(
            yaml.dump(
                document,
                Dumper=IndentedSafeDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                width=120,
            ),
            encoding="utf-8",
            newline="\n",
        )

    print(f"{len(rows):,}件を{len(PUBLICATION_FILE_NAMES)}ファイルへ移行しました。")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_csv", type=Path)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    migrate(arguments.source_csv, arguments.output_directory)


if __name__ == "__main__":
    main()
