#!/usr/bin/env python3
"""生成したJSONとCSVの内容・文字コード・改行を検査する。"""

from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = PROJECT_ROOT / "docs" / "data" / "naka-city-publications.json"
CSV_PATH = PROJECT_ROOT / "docs" / "data" / "naka-city-publications.csv"


def main() -> None:
    csv_bytes = CSV_PATH.read_bytes()
    if not csv_bytes.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("CSVにUTF-8 BOMがありません。")

    body = csv_bytes[3:]
    if body.count(b"\r\n") != 2460:
        raise SystemExit("CSVのCRLF改行数が2,460ではありません。")
    if body.replace(b"\r\n", b"").find(b"\n") != -1:
        raise SystemExit("CSVに単独LFがあります。")
    if body.replace(b"\r\n", b"").find(b"\r") != -1:
        raise SystemExit("CSVに単独CRがあります。")

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        csv_rows = list(csv.DictReader(csv_file))
    json_document = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    json_entries = [
        entry
        for publication in json_document["publications"]
        for entry in publication["entries"]
    ]

    if len(csv_rows) != 2459 or len(json_entries) != 2459:
        raise SystemExit("CSVまたはJSONの目次項目数が2,459ではありません。")
    if json_document["statistics"]["uncertain_entry_count"] != 11:
        raise SystemExit("要確認項目数が11ではありません。")

    print("CSV: UTF-8 BOM・CRLF・2,459件を確認しました。")
    print("JSON: 2,459件・要確認11件を確認しました。")


if __name__ == "__main__":
    main()

