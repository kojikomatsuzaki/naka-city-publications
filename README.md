# 那珂市刊行物目次データ

那珂市公式サイトで公開されている『那珂市史』、旧『那珂町史』、
『那珂町史の研究』、旧『瓜連町史』の目次を、章・節・項と開始ページの
階層を保って構造化したデータセットです。

## 目次

- [基本方針](#基本方針)
- [収録範囲](#収録範囲)
- [ディレクトリ構成](#ディレクトリ構成)
- [更新方法](#更新方法)
- [データ品質と表記](#データ品質と表記)
- [出典](#出典)
- [ライセンス](#ライセンス)

## 基本方針

本プロジェクトでは、`data/toc/*.yaml`を唯一の正本とします。

```text
YAML（正本）
  ├─ CSV（確認・参照・印刷用）
  ├─ JSON（機械利用・Web表示用）
  └─ GitHub Pages（人間向け閲覧）
```

CSVとJSONは直接編集しません。YAMLの更新とデータ版の更新を契機として、
全件を再生成します。差分は更新内容の確認に使い、派生データそのものは
毎回正本から作り直します。

## 収録範囲

- No新刊：『那珂市史』地誌編
- No1〜3：旧『那珂町史』
- No4：『那珂町の考古学』
- No5〜7：『那珂町史の研究』
- No8〜9：旧『瓜連町史』

目次項目は全2,459件です。

## ディレクトリ構成

```text
metadata/dataset.yaml        データセット全体のメタデータと版
data/toc/                    刊行物別のYAML正本
schema/toc.schema.json       YAML正本の構造を示すJSON Schema
scripts/                     検証・生成・初回移行プログラム
docs/                        GitHub Pagesと派生データ
migration/                   初回YAML移行に用いたCSV
```

各目次項目には、公開後に行を挿入しても変更しない安定IDを付与しています。
`sequence`は表示順を表し、安定IDとは役割を分けています。

## 更新方法

1. `data/toc/*.yaml`を修正する。
2. `metadata/dataset.yaml`の`dataset_version`を更新する。
3. 次のコマンドで検証し、JSONとCSVを再生成する。

```bash
python -m pip install -r requirements.txt
python scripts/build_derived_data.py
python scripts/check_generated_files.py
```

`main`ブランチへ反映すると、GitHub Actionsが同じ検証と全件再生成を行い、
生成物をリポジトリへ反映してGitHub Pagesを更新します。

バージョン番号はSemantic Versioningに準じます。

- パッチ：文字、ページ番号、OCR判読結果の訂正
- マイナー：刊行物またはメタデータ項目の追加
- メジャー：互換性を壊すデータ構造の変更

## データ品質と表記

- 旧字体・異体字・変体仮名は、Unicodeで表現できる範囲で原資料の表記を保持します。
- Unicode外の文字を新字体などへ変更した場合は、`verification.status: normalized`として記録します。
- OCRと画像目視でも判読が難しい箇所は、`verification.status: uncertain`として対象フィールドと備考を記録します。
- 目次に個別ページがない項目は、ページの欠損と親見出しのページ参照を区別します。

## 出典

- [那珂市「那珂市刊行物」](https://www.city.naka.lg.jp/sp/edu-board/bunkazai/rekishiminzoku/page010949.html)

各刊行物のYAMLには、参照した表題紙・目次PDFのURLを記録しています。

## ライセンス

データとプログラムのライセンスは、公開前に権利関係を確認して確定します。
明示的なライセンスを設定するまでは、無断での再配布・改変を許諾するものではありません。

