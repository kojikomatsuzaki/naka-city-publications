# データモデル

## 1. 正本の単位

`data/toc/`には刊行物ごとに1つのYAMLファイルを置きます。刊行物の題名と
参照PDF URLは`publication`にまとめ、目次の各項目では繰り返しません。

```yaml
publication:
  publication_number: 新刊
  title: 那珂市史
  source_pdf_url: https://example.jp/table-of-contents.pdf
entries:
  - id: naka-toc-new-0001
    sequence: 1
    heading_level: item
    volume: 地誌編
    chapter: null
    section: null
    item: 発刊にあたって
    start_page: 1
    page_reference:
      status: stated
```

## 2. 階層

`heading_level`は、そのレコード自身が表す見出しの階層です。

| 値 | 使用する見出し | 下位見出し |
| --- | --- | --- |
| `chapter` | `chapter` | `section`と`item`は`null` |
| `section` | `section` | `item`は`null` |
| `item` | `item` | なし |

項見出しのレコードにも親となる章・節を記録します。これにより、1項1レコードの
CSVへ情報を失わずプロトコール変換できます。

## 3. ページ記載状態

`start_page`と`page_reference`を分け、数字がない理由を明示します。

| `status` | 意味 |
| --- | --- |
| `stated` | その見出しに開始ページが記載されている |
| `not_listed` | 目次に開始ページの記載がない |
| `parent_only` | 個別ページはなく、親見出しにのみ開始ページがある |

`parent_only`の場合は、`parent_start_page`に親見出しの開始ページを記録します。

## 4. 検証情報

判読上の注意が必要な項目だけに`verification`を置きます。

```yaml
verification:
  status: uncertain
  fields:
    - item
    - start_page
  note: 表題及び開始ページはOCR及び画像目視で判読に不確実性あり
```

- `uncertain`：OCRと画像目視を行っても判読に不確実性が残る
- `normalized`：Unicode外の文字などを代替表記へ変更した

## 5. 安定IDと表示順

`id`は各目次項目を識別する安定IDです。公開後は項目を挿入・並べ替えしても
既存IDを変更しません。`sequence`は刊行物内の表示順であり、必要に応じて
振り直すことができます。
