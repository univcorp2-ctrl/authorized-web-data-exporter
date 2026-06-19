# Authorized Web Data Exporter

![全体アーキテクチャ: ログイン型サイトから許可されたデータを安定して取得し、CSV/Excel/JSON/TXTへ保存する流れ](docs/assets/architecture-overview.svg)

## はじめに: このリポジトリが何をするか

このリポジトリは、**ログインが必要なWebサイトから、あなたが正規に閲覧・保存できるデータを、安定してCSV / Excel / JSONL / TXTへエクスポートし、投資分析ExcelとWebダッシュボードまで自動生成する汎用基盤**です。

最初のサイトプロファイルとして、健美家（Kenbiya）のログインURL `https://www.kenbiya.com/app/exe/login` を使う設定例を `profiles/kenbiya.yml` に同梱しています。ただし、設計はKenbiya専用ではありません。別サイトでも、YAMLのサイトプロファイルを追加・変更するだけで使い回せるようにしています。

> 重要: このツールは、利用規約・robots.txt・サイト運営者の許諾・アカウント契約で許可される範囲でのみ使う前提です。CAPTCHA回避、認証回避、IPローテーション、プロキシ悪用、bot検知のすり抜け、アクセス制限突破は実装していません。安定性は、低速アクセス、再開可能設計、重複排除、リトライ、robots.txt確認、エラー保存により高めます。

---

## 最初に見るべき全体像

READMEを開いたときに最初に目に入る上の画像は、GPT Image最新モデルで説明画像を作ることを想定した構成に合わせています。リポジトリには、GitHubでそのまま表示できるSVG版を `docs/assets/architecture-overview.svg` として同梱し、GPT Imageで差し替え用の説明画像を作るための詳細プロンプトを `docs/gpt-image-guidance-prompt.md` に入れています。

上の画像の流れを、初心者向けに文章で丁寧に分解すると次の通りです。

1. **ユーザーが設定するもの**  
   対象サイトのログイン情報、検索結果URL、どのリンクを詳細ページとして扱うか、どの項目を抜き出すかを設定します。GitHub Actionsで動かす場合、ログイン情報はGitHub Secretsに保存します。

2. **robots.txtを最初に確認する**  
   対象ドメインの `/robots.txt` を取得し、User-agent、Allow、Disallow、Crawl-delay、Sitemapを解析します。開始URL、ログインURL、巡回中に見つけたURLがrobots.txt上で許可されるかを判定し、`outputs/robots_report.txt` に保存します。

3. **サイトプロファイルを読み込む**  
   `profiles/kenbiya.yml` のようなYAMLファイルを読み込みます。ここにはログインURL、ログインフォームの候補セレクタ、ログイン成功を判定するセレクタ、検索結果から詳細ページURLを見つけるルール、ページ送りルール、詳細ページで抽出する項目が書かれています。

4. **Playwrightでブラウザを起動する**  
   実ブラウザに近い形でページを開きます。ログイン済みセッションが保存されていれば再利用し、なければ正規のID・パスワードでログインします。

5. **検索結果ページを低速に巡回する**  
   検索結果URLを開き、詳細ページURLと次ページURLを抽出します。並列で一気にアクセスせず、標準では1ページごとに待機時間とランダムなジッターを入れます。

6. **詳細ページを1件ずつ取得する**  
   発見した詳細ページURLをキューに入れ、重複を除外しながら1件ずつ取得します。途中で失敗してもURL・理由・フェーズを保存します。

7. **抽出エンジンがデータ化する**  
   YAMLで指定した項目、ページ内のテーブル、定義リスト、本文、画像URL、リンクURLをまとめて構造化します。未知の項目も `key_values` と `raw_text` に残すため、取りこぼしを減らします。

8. **投資分析Excelを生成する**  
   `investment_analysis.xlsx` を1シートだけで生成します。必須カラム、収益・融資分析、単価分析、API比較価格、重複判定、仕入れ判定、未取得理由、重要候補並び替えを自動で行います。

9. **Webダッシュボードを生成する**  
   `outputs/dashboard/index.html` を生成します。ブラウザで開くだけで、A/B候補、KPI、検索、絞り込み、リスク、次アクション、詳細URLを見やすく確認できます。

10. **成果物を書き出す**  
   `outputs/` に `investment_analysis.xlsx`、`dashboard/index.html`、`analysis_summary.txt`、`records.csv`、`records.xlsx`、`records.jsonl`、`records.txt`、`errors.jsonl`、`robots_report.txt` を生成します。

---

## 投資分析ExcelとWebダッシュボード

最終分析ファイルは `outputs/investment_analysis.xlsx` です。

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
outputs/dashboard/index.html
```

Webダッシュボードの主な機能:

- KPIカード
- 重要候補 上位5件
- キーワード検索
- 仕入れ判定フィルター
- 重複判定フィルター
- 全件一覧テーブル
- 詳細モーダル
- 詳細URLリンク

詳しくは `docs/analysis.md` と `docs/dashboard.md` を見てください。

---

## この基盤の設計思想

### 1. 安定性を最重要視

このツールは、速さよりも安定性を優先します。

- 直列実行でサーバー負荷を抑える
- 各リクエストに待機時間とジッターを入れる
- 失敗時に指数バックオフでリトライする
- チェックポイントで途中再開できる
- 同じURLを二重取得しない
- robots.txtを取得・解析・保存する
- robots.txtで許可されないURLは標準では取得しない
- エラーを消さずに `errors.jsonl` へ残す
- 生HTML保存オプションで後から再解析できる

### 2. 他サイトへ使い回せる汎用アーキテクチャ

Kenbiya固有の処理をコードに埋め込まず、サイト差分はYAMLプロファイルに寄せています。

```mermaid
flowchart TD
    A[Site Profile YAML] --> B[Generic CLI]
    B --> R[robots.txt Inspector]
    R --> C[Browser Session Manager]
    C --> D[Login Adapter]
    D --> E[Search Page Collector]
    E --> F[URL Discovery Engine]
    F --> G[Detail Page Queue]
    G --> H[Detail Extractor]
    H --> I[Checkpoint Store]
    H --> J[Export Writers]
    J --> K[Investment Analysis Workbook]
    J --> W[Static Web Dashboard]
    J --> L[CSV / Excel / JSONL / TXT]
    R --> M[robots_report.txt]
```

### 3. “ブロック回避”ではなく“ブロックされにくい健全運用”

このリポジトリでは、検知回避や制限突破ではなく、以下で安定性を高めます。

- アクセス間隔を十分に空ける
- 並列取得しない
- セッションを再利用して不要なログインを減らす
- リトライ回数を制限する
- CAPTCHAや追加認証が出た場合は停止する
- robots.txtを毎回レポートとして残す
- User-agentを偽装しない
- プロキシローテーションを使わない

---

## リポジトリ構成

```text
.
├── profiles/
│   ├── kenbiya.yml
│   └── example-site.yml
├── src/authorized_web_exporter/
│   ├── cli.py
│   ├── config.py
│   ├── crawler.py
│   ├── dashboard.py
│   ├── investment_analysis.py
│   ├── parser.py
│   ├── robots.py
│   ├── checkpoint.py
│   ├── storage.py
│   └── models.py
├── scripts/build_runtime_profile.py
├── docs/
│   ├── analysis.md
│   ├── dashboard.md
│   ├── architecture.md
│   ├── setup.md
│   ├── robots.md
│   ├── gpt-image-guidance-prompt.md
│   ├── github-actions-permission-note.md
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── export.yml
│   └── assets/architecture-overview.svg
├── tests/
└── .devcontainer/
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
KENBIYA_EMAIL="your-email@example.com"
KENBIYA_PASSWORD="your-password"
WEB_EXPORT_ACKNOWLEDGE_AUTHORIZED="true"
REINFOLIB_API_KEY_XLSX_PATH="G:\\マイドライブ\\AI_Agents\\Private\\API_AWS_DB.xlsx"
```

`profiles/kenbiya.yml` の `start_urls` に、ブラウザでログイン後に表示できる検索結果URLを貼ります。

```yaml
start_urls:
  - "https://www.kenbiya.com/...検索結果URL..."
```

実行します。

```bash
web-export export --profile profiles/kenbiya.yml --output-dir outputs --acknowledge-authorization
```

既存データだけ再分析する場合:

```bash
web-export analyze --input outputs/records.jsonl --output-dir outputs
```

既存Excelからダッシュボードだけ再生成する場合:

```bash
web-export dashboard --input outputs/investment_analysis.xlsx --output-dir outputs/dashboard
```

robots.txtだけ確認する場合:

```bash
web-export robots --profile profiles/kenbiya.yml --url https://www.kenbiya.com/app/exe/login
```

---

## GitHub Actionsについて

このリポジトリには、CI用とエクスポート用のworkflowテンプレートを以下に保存しています。

- `docs/workflows/ci.yml`
- `docs/workflows/export.yml`

今回の自動コミット環境では、`.github/workflows/` へのファイル作成だけがGitHub API 404で拒否されました。これはアプリ本体・テスト・ドキュメントのpushとは別で、workflowファイルを書き込む権限がないGitHub tokenやGitHub Appで起きる典型的な制限です。

workflow作成権限がある環境では、同じ内容を `.github/workflows/ci.yml` と `.github/workflows/export.yml` に置くと、以下が有効になります。

- push / pull_request / workflow_dispatchでのlint・test CI
- `workflow_dispatch` からの手動エクスポート
- `authorized-web-export-outputs` artifactへのCSV/Excel/JSON/TXT/robots_report/投資分析Excel/Webダッシュボード保存

GitHub Actionsで不動産情報ライブラリAPI比較を使う場合は、ExcelファイルではなくRepository Secret `REINFOLIB_API_KEY` を使ってください。APIキーはログや出力には書きません。

---

## robots.txt確認について

実行時には必ず対象ドメインの `/robots.txt` を確認し、次を `outputs/robots_report.txt` に保存します。

- robots.txt URL
- 取得ステータス
- User-agentごとのAllow/Disallow
- Crawl-delay
- Sitemap
- 開始URL・ログインURL・巡回URLごとの許可判定
- robotsで拒否されたためスキップしたURL

Kenbiyaのログインページについては、ChatGPTの確認環境ではページ本文取得がrobots.txtにより拒否されました。そのため、このリポジトリではKenbiyaを含むすべてのサイトで、実行時にrobots.txtを必ず取得し、結果をレポート化する設計にしています。

---

## 本番運用に必要なもの

- 対象サイトの正規アカウント
- 対象データの取得・保存が利用規約・契約・権限上許可されていること
- GitHub Actionsで動かす場合はRepository Secrets
- 不動産情報ライブラリAPIを使う場合は `REINFOLIB_API_KEY` またはローカルExcelパス
- 検索結果URLまたは一覧URL
- 対象サイトに合わせたYAMLプロファイル
- 大量取得する場合は十分な低速設定

---

## テスト

```bash
pytest
ruff check .
```

---

## 注意事項

このツールは、アカウント所有者自身が閲覧できる情報を保存するための補助ツールです。サイトのアクセス制御、レート制限、CAPTCHA、ログイン制限、robots.txt、利用規約を回避する用途には使わないでください。
