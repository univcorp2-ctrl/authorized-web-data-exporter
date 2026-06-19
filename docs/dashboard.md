# 投資分析Webダッシュボード

`web-export export` または `web-export analyze` を実行すると、投資分析Excelに加えて次のWebダッシュボードを生成します。

```text
outputs/dashboard/index.html
```

このファイルは静的HTMLです。追加のWebサーバーは不要で、ブラウザで開くだけで表示できます。GitHub Actions artifactから `outputs/` をダウンロードした場合も、`dashboard/index.html` を開けば確認できます。

## ダッシュボードの目的

Excelは最終保存・集計用、Webダッシュボードは閲覧・比較・優先順位付け用です。

- A判定・B判定の重要候補をすぐ見つける
- DSCR、手残り、利回り、駅徒歩、リスクを横断比較する
- 物件名・所在地・リスク・コメントで検索する
- 仕入れ判定と重複判定で絞り込む
- 詳細URLをクリックして元ページを開く
- 各物件の全カラムを詳細モーダルで確認する

## 自動生成されるタイミング

### スクレイピングから実行する場合

```bash
web-export export --profile profiles/kenbiya.yml --output-dir outputs --acknowledge-authorization
```

生成物:

- `outputs/investment_analysis.xlsx`
- `outputs/analysis_summary.txt`
- `outputs/analysis_summary.json`
- `outputs/dashboard/index.html`

### 既存JSONLから再分析する場合

```bash
web-export analyze --input outputs/records.jsonl --output-dir outputs
```

### 既存Excelからダッシュボードだけ再生成する場合

```bash
web-export dashboard --input outputs/investment_analysis.xlsx --output-dir outputs/dashboard
```

## 画面構成

### 1. KPIカード

上部に以下を表示します。

- 対象件数
- A判定件数
- B判定件数
- C判定件数
- D判定件数
- 新規件数
- API取得件数
- 平均DSCR

### 2. フィルター

以下の条件で絞り込みできます。

- キーワード検索
- 仕入れ判定 A / B / C / D
- 重複判定 新規 / 既存更新 / 重複 / 要確認

### 3. 重要候補 上位5件

分析結果の並び順に従って、上位5件をカード表示します。

並び順は次の通りです。

1. 仕入れ判定 A
2. 仕入れ判定 B
3. DSCRが高い順
4. 手残り比率が高い順
5. 駅徒歩が短い順

### 4. 全件一覧テーブル

全物件を1テーブルで表示します。主な表示列は以下です。

- 仕入れ判定
- 物件名
- 種別
- 都道府県
- 市区町村
- 価格（万円）
- 表面利回り%
- DSCR
- 経費率考慮後手残り
- 手残り比率
- 駅徒歩分数
- 築年数
- 構造
- 割安/割高判定
- 重複判定
- 主要リスク
- 次アクション
- 詳細URL

### 5. 詳細モーダル

各行の「詳細」ボタンを押すと、その物件の全カラムを一覧表示します。

## セキュリティ

- APIキーはHTMLへ埋め込みません。
- 内部計算用の `_` 始まりのキーもHTMLには出しません。
- ダッシュボードはローカル完結の静的HTMLです。
- 外部CDNや外部JavaScriptは使っていません。

## Excelとの関係

ユーザー指定の「最終アウトプットは全件を1シートにまとめる」という条件は、`investment_analysis.xlsx` で維持しています。

Webダッシュボードは閲覧補助の追加成果物です。Excelのシート数や元データは変更しません。
