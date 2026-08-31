#!/usr/bin/env python3
"""正本YAMLまたはスキーマ変更時にデータ版が上がっていることを確認する。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "metadata" / "dataset.yaml"


def semantic_version_tuple(value: str) -> tuple[int, int, int]:
    try:
        parts = tuple(int(part) for part in value.split("."))
    except ValueError as error:
        raise SystemExit(f"Semantic Versioning形式ではありません: {value}") from error
    if len(parts) != 3:
        raise SystemExit(f"Semantic Versioning形式ではありません: {value}")
    return parts


def git_output(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
    )


def main() -> None:
    try:
        previous_dataset_text = git_output("show", "HEAD^:metadata/dataset.yaml")
    except subprocess.CalledProcessError:
        print("初回コミットのため、バージョン比較を省略します。")
        return

    changed_paths = set(git_output("diff", "--name-only", "HEAD^").splitlines())
    canonical_paths_changed = any(
        path == "metadata/dataset.yaml"
        or path.startswith("data/toc/")
        or path.startswith("schema/")
        for path in changed_paths
    )
    if not canonical_paths_changed:
        print("正本YAMLとスキーマに変更はありません。")
        return

    previous_dataset = yaml.safe_load(previous_dataset_text)
    current_dataset = yaml.safe_load(DATASET_PATH.read_text(encoding="utf-8"))
    previous_version = str(previous_dataset["dataset_version"])
    current_version = str(current_dataset["dataset_version"])

    if semantic_version_tuple(current_version) <= semantic_version_tuple(previous_version):
        raise SystemExit(
            "正本YAMLまたはスキーマを変更したため、"
            f"dataset_versionを{previous_version}より大きくしてください。"
        )
    print(f"データ版の更新を確認しました: {previous_version} → {current_version}")


if __name__ == "__main__":
    main()

