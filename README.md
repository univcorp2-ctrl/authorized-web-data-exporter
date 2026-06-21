# Authorized Web Data Exporter

![全体アーキテクチャ: ログイン型サイトから許可されたデータを安定して取得し、CSV/Excel/JSON/TXTへ保存する流れ](docs/assets/architecture-overview.svg)

## はじめに: このリポジトリが何をするか

このリポジトリは、**日本の不動産投資に役立つ情報を、投資物件ポータル・一般売買/賃貸ポータル・大手仲介・地場業者・公的API・競売/公売・ハザード/地価情報から横断収集し、投資分析ExcelとWebダッシュボードまで自動生成する汎用基盤**です。

最初のサイトプロファイルとして、健美家（Kenbiya）のログインURL `https://www.kenbiya.com/app/exe/login` を使う設定例を `profiles/kenbiya.yml` に同梱しています。さらに、`profiles/sources/` にSUUMO、Yahoo!不動産、楽待、不動産投資連合隊、LIFULL HOME'S、at home、Nifty不動産、大手仲介各社、競売/公売、賃貸相場補完サイトなどの公開サイト用プロファイルを追加しています。

> 重要: このツールは、アカウント所有者自身が閲覧できる情報や公開情報を保存・分析するための補助ツールです。CAPTCHA回避、認証回避、IPローテーション、プロキシ悪用、bot検知のすり抜け、アクセス制限突破は実装していません。情報収集の安定性は、低速アクセス、再開可能設計、重複排除、リトライ、robots.txt確認、エラー保存により高めます。

---

## 最初に見るべき全体像

READMEを開いたときに最初に目に入る上の画像は、GPT Image最新モデルで説明画像を作ることを想定した構成に合わせています。リポジトリには、GitHubでそのまま表示できるSVG版を `docs/assets/architecture-overview.svg` として同梱し、GPT Imageで差し替え用の説明画像を作るための詳細プロンプトを `docs/gpt-image-guidance-prompt.md` に入れています。

処理の流れは次の通りです。

1. **取得元カタログを管理する**  
   `data/source_catalog.yml` に、日本の不動産投資で使う取得元をリストアップします。

2. **サイト別プロファイルを読み込む**  
   `profiles/sources/*.yml` に、各サイトの開始URL、ドメイン、詳細ページURL抽出ルール、抽出項目を定義します。

3. **単一サイトまたは複数サイトを実行する**  
   単一サイトは `web-export export`、複数サイトは `web-export batch` で実行します。

4. **一覧ページを巡回する**  
   各サイトの開始URLを開き、詳細ページURLと次ページURLを抽出します。

5. **詳細ページを取得する**  
   詳細ページを1件ずつ取得し、テーブル、定義リスト、本文、画像URL、リンクURLを保存します。

6. **ソース別に保存する**  
   各サイトごとに `records.jsonl`、CSV、Excel、TXT、errors、robots_reportを保存します。

7. **全ソースを統合する**  
   バッチ実行では、全ソースの `records.jsonl` をURL重複除外して `outputs/batch/_combined/records.jsonl` に統合します。

8. **投資分析Excelを生成する**  
   `investment_analysis.xlsx` を1シートだけで生成します。必須カラム、収益・融資分析、単価分析、API比較価格、重複判定、仕入れ判定、未取得理由、重要候補並び替えを自動で行います。

9. **Webダッシュボードを生成する**  
   `outputs/batch/_combined/dashboard/index.html` を生成します。ブラウザで開くだけで、A/B候補、KPI、検索、絞り込み、リスク、次アクション、詳細URLを見やすく確認できます。

---

## 対応している情報源

対応ソースの正本は以下です。

- `data/source_catalog.yml`
- `docs/source_catalog.md`
- `profiles/sources/`

大分類:

- 公的API・公的情報: 国交省 不動産情報ライブラリ、国税庁 路線価図、ハザードマップポータル、地理院地図、e-Stat、RESAS
- 投資物件ポータル: 健美家、楽待、LIFULL HOME'S 不動産投資、投資アットホーム、不動産投資連合隊、RALS/CBIZ、ノムコム・プロなど
- 一般売買/賃貸ポータル: SUUMO、Yahoo!不動産、LIFULL HOME'S、at home、Nifty不動産、goo住宅・不動産など
- 大手仲介: 三井のリハウス、住友不動産販売/ステップ、東急リバブル、ノムコム、三菱UFJ不動産販売、三菱地所の住まいリレー、みずほ不動産販売など
- 地場・団体系: センチュリー21、ピタットハウス、ハトマークサイト、不動産ジャパン
- 競売/公売/商業用: BIT、KSI官公庁オークション、981.jp、CBRE、JLL物件情報
- 賃料相場補完: いい部屋ネット、CHINTAI、アパマンショップ、スモッカなど

---

## 一括収集コマンド

全ソースを順番に実行します。

```bash
web-export batch \
  --profile-dir profiles/sources \
  --output-root outputs/batch \
  --acknowledge-authorization
```

一部だけ実行する場合:

```bash
web-export batch \
  --profile-dir profiles/sources \
  --include suumo \
  --include yahoo-realestate \
  --include rakumachi \
  --include rals-invest \
  --output-root outputs/batch \
  --acknowledge-authorization
```

統合出力:

```text
outputs/batch/_combined/records.jsonl
outputs/batch/_combined/investment_analysis.xlsx
outputs/batch/_combined/dashboard/index.html
outputs/batch/batch_summary.json
```

詳しくは `docs/batch_collection.md` を見てください。

---

## 投資分析ExcelとWebダッシュボード

最終分析ファイルは `investment_analysis.xlsx` です。

- 1シートだけ: `投資分析`
- 全件を1シートに集約
- A判定・B判定を上に並べる
- 並び順は `A → B → DSCR高い順 → 手残り比率高い順 → 駅徒歩短い順`
- 必須カラムをすべて作成
- 空白セルを残さず、未取得情報には理由を記載
- `受信日時`、`メールリンク`、`重複判定` も追加
- メールリンクと詳細URLは値がある場合にクリック可能
- APIキーはExcel、ログ、summary、Webダッシュボードに出力しない

Webで見たい場合は、以下を開きます。

```text
outputs/batch/_combined/dashboard/index.html
```

---

## すぐ使う方法: ローカル

```bash
git clone https://github.com/YOUR_OWNER/authorized-web-data-exporter.git
cd authorized-web-data-exporter
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

`.env` を編集します。

```bash
WEB_EXPORT_ACKNOWLEDGE_AUTHORIZED="true"
REINFOLIB_API_KEY_XLSX_PATH="G:\\マイドライブ\\AI_Agents\\Private\\API_AWS_DB.xlsx"
```

Kenbiyaログイン取得も使う場合:

```bash
KENBIYA_EMAIL="your-email@example.com"
KENBIYA_PASSWORD="your-password"
```

全ソース収集:

```bash
web-export batch --profile-dir profiles/sources --output-root outputs/batch --acknowledge-authorization
```

単一サイトだけ:

```bash
web-export export --profile profiles/sources/rakumachi.yml --output-dir outputs/rakumachi --acknowledge-authorization
```

既存データだけ再分析:

```bash
web-export analyze --input outputs/batch/_combined/records.jsonl --output-dir outputs/batch/_combined
```

---

## GitHub Actionsについて

このリポジトリには、CI用とエクスポート用のworkflowテンプレートを以下に保存しています。

- `docs/workflows/ci.yml`
- `docs/workflows/export.yml`

今回の自動コミット環境では、`.github/workflows/` へのファイル作成だけがGitHub API 404で拒否されました。これはアプリ本体・テスト・ドキュメントのpushとは別で、workflowファイルを書き込む権限がないGitHub tokenやGitHub Appで起きる典型的な制限です。

---

## テスト

```bash
pytest
ruff check .
```

---

## 注意事項

このツールは、アカウント所有者自身が閲覧できる情報や公開情報を保存・分析するための補助ツールです。サイトのアクセス制御、レート制限、CAPTCHA、ログイン制限を回避する用途には使いません。
