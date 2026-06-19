# 投資分析出力仕様

`web-export export` はスクレイピング後に `outputs/investment_analysis.xlsx` と `outputs/dashboard/index.html` を自動生成します。既存の `outputs/records.jsonl` から再分析する場合は次を実行します。

```bash
web-export analyze --input outputs/records.jsonl --output-dir outputs
```

API比較を使わずに計算だけ行う場合:

```bash
web-export analyze --input outputs/records.jsonl --output-dir outputs --skip-api-comparison
```

既存ExcelからWebダッシュボードだけ再生成する場合:

```bash
web-export dashboard --input outputs/investment_analysis.xlsx --output-dir outputs/dashboard
```

## 最終分析Excel

最終分析Excelは `investment_analysis.xlsx` です。このブックは必ず1シートだけです。

- シート名: `投資分析`
- 全物件を1シートに集約
- A判定・B判定を上に並べる
- DSCR、手残り比率、駅徒歩で並び替え
- 空白セルを残さず、未取得情報には未取得理由を入れる
- メールリンクと詳細URLは値がある場合にクリック可能なリンクにする
- APIキーはシート、ログ、summary、Webダッシュボードに出力しない

## Webダッシュボード

Webダッシュボードは `outputs/dashboard/index.html` です。追加サーバー不要で、ブラウザで直接開けます。

主な機能:

- KPIカード
- A/B/C/D判定件数
- 重要候補上位5件
- キーワード検索
- 仕入れ判定フィルター
- 重複判定フィルター
- 主要リスク表示
- 次アクション表示
- 詳細URLリンク
- 全カラム詳細モーダル

詳しくは `docs/dashboard.md` を参照してください。

## 追加されるメタ列

ユーザー指定の必須カラムに加えて、検証のために以下を先頭へ追加します。

- `受信日時`
- `メールリンク`
- `重複判定`

## 自動計算

- `価格（円） = 価格（万円） × 10,000`
- `想定年間家賃収入 = 価格（円） × 表面利回り%`
- `概算NOI = 想定年間家賃収入 × 80%`
- `概算NOI利回り% = 概算NOI ÷ 価格（円） × 100`
- `年間返済額 = PMT(金利2.8%、融資期間30年、全額借入) × 12`
- `DSCR = 年間家賃収入 ÷ 年間返済額`
- `手残り金額 = 年間家賃収入 − 年間返済額`
- `経費率考慮後手残り = 概算NOI − 年間返済額`
- `物件価格に対する手残り比率 = 経費率考慮後手残り ÷ 価格（円） × 100`

## 法定耐用年数

- 木造: 22年
- 軽量鉄骨造: 27年
- 鉄骨造: 34年
- RC造: 47年
- SRC造: 47年
- 不明: `要確認：構造不明`

## API補完

不動産情報ライブラリの `XIT001` を使って、市区町村内の類似取引を取得し、取引価格中央値を計算します。APIキーは次の順で読みます。

1. 環境変数 `REINFOLIB_API_KEY`
2. 環境変数 `REINFOLIB_API_KEY_XLSX_PATH` で指定されたExcel
3. 標準パス `G:\マイドライブ\AI_Agents\Private\API_AWS_DB.xlsx`

APIキーは出力ファイル、ログ、summary、Webダッシュボードに書きません。

API未取得時は空欄ではなく、以下のような理由を入れます。

- `API未取得：住所粒度不足`
- `API未取得：対象市区町村で類似取引なし`
- `API未取得：外部API実行不可`
- `API未取得：構造不明`
- `API未取得：面積不明`
- `API未取得：APIキー未設定またはキーファイル未検出`

## Web補完の扱い

スクレイピング済みの物件詳細ページ本文、テーブル、定義リスト、リンク、画像URLから補完します。外部検索APIを使わずに確定できない情報は、事実として断定せず `未取得：Webまたは物件詳細で...を確定できず` と記録します。

## 重複判定

以下を組み合わせて重複確認します。

- 所在地
- 物件名
- 価格
- 土地面積
- 建物面積
- 築年
- 構造

判定値:

- `新規`
- `既存更新`
- `重複`
- `要確認`

## 仕入れ判定

- A: 即打診
- B: 条件次第
- C: 保留
- D: 見送り

主な判断材料は、表面利回り、DSCR、手残り、駅距離、築年数、残存耐用年数、API比較価格、積算評価、ハザード未取得リスクです。

## Summary

分析後、以下も生成します。

- `outputs/analysis_summary.txt`
- `outputs/analysis_summary.json`
- `outputs/dashboard/index.html`

summaryには保存ファイル名、対象件数、新規件数、既存更新件数、重複件数、メールリンク欠損件数、空白セル件数、A/B/C/D判定件数、API取得件数、API未取得件数、未取得理由の内訳、重要候補上位5件を出します。APIキーの実値は出しません。
