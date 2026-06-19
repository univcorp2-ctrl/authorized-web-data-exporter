# 初期設定ガイド

## ローカルで動かす

```bash
git clone https://github.com/YOUR_OWNER/authorized-web-data-exporter.git
cd authorized-web-data-exporter
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

`.env` に対象サイトの認証情報を入れます。

```bash
KENBIYA_EMAIL="your-email@example.com"
KENBIYA_PASSWORD="your-password"
WEB_EXPORT_ACKNOWLEDGE_AUTHORIZED="true"
```

`profiles/kenbiya.yml` の `start_urls` を実際の検索結果URLに変更します。

```bash
web-export robots --profile profiles/kenbiya.yml --url https://www.kenbiya.com/app/exe/login
web-export export --profile profiles/kenbiya.yml --output-dir outputs --acknowledge-authorization
```

## GitHub Actionsで動かす

1. GitHubリポジトリを開きます。
2. `Settings` を開きます。
3. `Secrets and variables` → `Actions` を開きます。
4. `New repository secret` から以下を追加します。
   - `KENBIYA_EMAIL`
   - `KENBIYA_PASSWORD`
   - `WEB_EXPORT_ACKNOWLEDGE_AUTHORIZED` = `true`
5. `Actions` → `Authorized Web Export` → `Run workflow` を開きます。
6. `start_urls` に検索結果URLを1行ずつ貼ります。
7. 実行完了後、artifact `authorized-web-export-outputs` をダウンロードします。

## 本番運用前チェック

- 対象サイトの利用規約で自動取得が許可されているか
- robots_report.txtで対象URLが許可されているか
- `request_delay_seconds` が十分に長いか
- `max_pages` / `max_items` が安全な上限になっているか
- `errors.jsonl` に失敗が残っていないか
