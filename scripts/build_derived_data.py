#!/usr/bin/env python3
"""YAML正本を検証し、Web用JSONと確認・印刷用CSVを全件再生成する。"""

from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "metadata" / "dataset.yaml"
TOC_DIRECTORY = PROJECT_ROOT / "data" / "toc"
SCHEMA_PATH = PROJECT_ROOT / "schema" / "toc.schema.json"
OUTPUT_DIRECTORY = PROJECT_ROOT / "docs" / "data"
JSON_OUTPUT_PATH = OUTPUT_DIRECTORY / "naka-city-publications.json"
CSV_OUTPUT_PATH = OUTPUT_DIRECTORY / "naka-city-publications.csv"
SCHEMA_OUTPUT_PATH = OUTPUT_DIRECTORY / "toc.schema.json"

CSV_HEADERS = [
    "No",
    "タイトル",
    "巻号",
    "章見出し",
    "節見出し",
    "項見出し",
    "開始ページ",
    "参照PDF URL",
    "備考",
]

SEMANTIC_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
ENTRY_ID = re.compile(r"^naka-toc-(new|0[1-9])-\d{4}$")
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFD]")
EXPECTED_PUBLICATION_NUMBERS = ["新刊", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


# ==========================================
# YAMLの読込み
# ==========================================

def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source_file:
        document = yaml.safe_load(source_file)
    if not isinstance(document, dict):
        raise ValueError(f"YAML文書の最上位はマッピングである必要があります: {path}")
    return document


def ordered_publication_paths() -> list[Path]:
    return [TOC_DIRECTORY / "no-new.yaml"] + [
        TOC_DIRECTORY / f"no-{number:02d}.yaml" for number in range(1, 10)
    ]


# ==========================================
# 正本データの検証
# ==========================================

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_text(value: Any, location: str, allow_none: bool = True) -> None:
    if value is None and allow_none:
        return
    require(isinstance(value, str), f"{location}: 文字列である必要があります。")
    require(not CONTROL_CHARACTERS.search(value), f"{location}: 不正な制御文字または置換文字があります。")


def validate_page_reference(entry: dict[str, Any], location: str) -> None:
    page_reference = entry.get("page_reference")
    require(isinstance(page_reference, dict), f"{location}.page_reference: マッピングが必要です。")
    status = page_reference.get("status")
    require(status in {"stated", "not_listed", "parent_only"}, f"{location}: ページ状態が不正です。")

    if status == "stated":
        require(isinstance(entry.get("start_page"), int), f"{location}: statedには開始ページが必要です。")
        require("parent_start_page" not in page_reference, f"{location}: 親ページは指定できません。")
    elif status == "not_listed":
        require(entry.get("start_page") is None, f"{location}: not_listedの開始ページはnullです。")
        require("parent_start_page" not in page_reference, f"{location}: 親ページは指定できません。")
    else:
        require(entry.get("start_page") is None, f"{location}: parent_onlyの開始ページはnullです。")
        require(
            isinstance(page_reference.get("parent_start_page"), int),
            f"{location}: parent_onlyには親見出しの開始ページが必要です。",
        )


def validate_heading(entry: dict[str, Any], location: str) -> None:
    level = entry.get("heading_level")
    require(level in {"chapter", "section", "item"}, f"{location}: heading_levelが不正です。")

    if level == "chapter":
        require(bool(entry.get("chapter")), f"{location}: chapter見出しが必要です。")
        require(entry.get("section") is None and entry.get("item") is None, f"{location}: 下位見出しはnullです。")
    elif level == "section":
        require(bool(entry.get("section")), f"{location}: section見出しが必要です。")
        require(entry.get("item") is None, f"{location}: itemはnullです。")
    else:
        require(bool(entry.get("item")), f"{location}: item見出しが必要です。")


def validate_verification(entry: dict[str, Any], location: str) -> None:
    verification = entry.get("verification")
    if verification is None:
        return
    require(isinstance(verification, dict), f"{location}.verification: マッピングが必要です。")
    require(verification.get("status") in {"uncertain", "normalized"}, f"{location}: 検証状態が不正です。")
    fields = verification.get("fields")
    require(isinstance(fields, list) and fields, f"{location}: 検証対象フィールドが必要です。")
    allowed_fields = {"volume", "chapter", "section", "item", "start_page"}
    require(set(fields) <= allowed_fields, f"{location}: 検証対象フィールドが不正です。")
    validate_text(verification.get("note"), f"{location}.verification.note", allow_none=False)


def validate_publication(document: dict[str, Any], expected_no: str, path: Path) -> None:
    require(set(document) == {"publication", "entries"}, f"{path}: 最上位キーが不正です。")
    publication = document.get("publication")
    entries = document.get("entries")
    require(isinstance(publication, dict), f"{path}: publicationが必要です。")
    require(publication.get("publication_number") == expected_no, f"{path}: Noがファイル名と一致しません。")
    validate_text(publication.get("title"), f"{path}.publication.title", allow_none=False)
    validate_text(publication.get("source_pdf_url"), f"{path}.publication.source_pdf_url", allow_none=False)
    require(str(publication["source_pdf_url"]).startswith("https://"), f"{path}: PDF URLはHTTPSで指定します。")
    require(isinstance(entries, list) and entries, f"{path}: entriesが空です。")

    seen_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        location = f"{path}.entries[{expected_sequence}]"
        require(isinstance(entry, dict), f"{location}: マッピングが必要です。")
        require(ENTRY_ID.fullmatch(str(entry.get("id", ""))) is not None, f"{location}: ID形式が不正です。")
        require(entry["id"] not in seen_ids, f"{location}: IDが重複しています。")
        seen_ids.add(entry["id"])
        require(entry.get("sequence") == expected_sequence, f"{location}: sequenceが連続していません。")
        for field in ["volume", "chapter", "section", "item"]:
            validate_text(entry.get(field), f"{location}.{field}")
        start_page = entry.get("start_page")
        require(start_page is None or (isinstance(start_page, int) and start_page >= 1), f"{location}: 開始ページが不正です。")
        validate_heading(entry, location)
        validate_page_reference(entry, location)
        validate_verification(entry, location)


def validate_dataset(dataset: dict[str, Any]) -> None:
    require(SEMANTIC_VERSION.fullmatch(str(dataset.get("schema_version", ""))) is not None, "schema_versionが不正です。")
    require(SEMANTIC_VERSION.fullmatch(str(dataset.get("dataset_version", ""))) is not None, "dataset_versionが不正です。")
    require(dataset.get("canonical_source", {}).get("format") == "YAML", "正本形式はYAMLである必要があります。")


# ==========================================
# 派生形式へのプロトコール変換
# ==========================================

def human_readable_note(entry: dict[str, Any]) -> str:
    verification = entry.get("verification")
    if verification:
        return str(verification["note"])

    page_reference = entry["page_reference"]
    if page_reference["status"] == "not_listed":
        return "目次に開始ページの記載なし"
    if page_reference["status"] == "parent_only":
        parent_page = page_reference["parent_start_page"]
        return f"目次に個別開始ページの記載なし（親見出しの開始ページは{parent_page}）"
    return ""


def csv_rows(publications: Iterable[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for document in publications:
        publication = document["publication"]
        for entry in document["entries"]:
            rows.append(
                [
                    publication["publication_number"],
                    publication["title"],
                    entry["volume"] or "",
                    entry["chapter"] or "",
                    entry["section"] or "",
                    entry["item"] or "",
                    str(entry["start_page"] or ""),
                    publication["source_pdf_url"],
                    human_readable_note(entry),
                ]
            )
    return rows


def write_json(dataset: dict[str, Any], publications: list[dict[str, Any]]) -> None:
    total_entries = sum(len(document["entries"]) for document in publications)
    uncertain_entries = sum(
        1
        for document in publications
        for entry in document["entries"]
        if entry.get("verification", {}).get("status") == "uncertain"
    )
    output = {
        "schema_version": dataset["schema_version"],
        "dataset_version": dataset["dataset_version"],
        "title": dataset["title"],
        "description": dataset["description"],
        "language": dataset["language"],
        "source_page_url": dataset["source_page_url"],
        "repository_url": dataset["repository_url"],
        "website_url": dataset["website_url"],
        "editor": dataset["editor"],
        "statistics": {
            "publication_count": len(publications),
            "entry_count": total_entries,
            "uncertain_entry_count": uncertain_entries,
        },
        "publications": publications,
    }
    JSON_OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(rows: list[list[str]]) -> None:
    with CSV_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.writer(output_file, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writerow(CSV_HEADERS)
        writer.writerows(rows)


# ==========================================
# 全件再生成
# ==========================================

def main() -> None:
    dataset = load_yaml(DATASET_PATH)
    validate_dataset(dataset)

    publication_paths = ordered_publication_paths()
    publications = [load_yaml(path) for path in publication_paths]
    for expected_no, document, path in zip(EXPECTED_PUBLICATION_NUMBERS, publications, publication_paths):
        validate_publication(document, expected_no, path)

    all_ids = [entry["id"] for document in publications for entry in document["entries"]]
    require(len(all_ids) == len(set(all_ids)), "刊行物をまたいでIDが重複しています。")

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    rows = csv_rows(publications)
    write_json(dataset, publications)
    write_csv(rows)
    shutil.copyfile(SCHEMA_PATH, SCHEMA_OUTPUT_PATH)

    counts = Counter(
        document["publication"]["publication_number"]
        for document in publications
        for _ in document["entries"]
    )
    print(
        json.dumps(
            {
                "dataset_version": dataset["dataset_version"],
                "publication_count": len(publications),
                "entry_count": len(rows),
                "counts_by_no": dict(counts),
                "json": str(JSON_OUTPUT_PATH.relative_to(PROJECT_ROOT)),
                "csv": str(CSV_OUTPUT_PATH.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
