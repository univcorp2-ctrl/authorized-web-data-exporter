# robots.txt確認仕様

このプロジェクトは、対象ドメインごとに `/robots.txt` を取得して解析します。

## 確認する項目

- robots.txt URL
- 取得ステータス
- User-agent
- Allow
- Disallow
- Crawl-delay
- Sitemap
- 指定URLごとの許可判定

## 標準動作

`profiles/*.yml` の `robots.enforce` が `true` の場合、robots.txtで拒否されたURLは取得しません。拒否されたURLは `errors.jsonl` と `robots_report.txt` に残ります。

```yaml
robots:
  enabled: true
  user_agent: "AuthorizedWebDataExporter"
  check_login_url: true
  enforce: true
  fail_closed_on_error: false
  report_path: "robots_report.txt"
```

## 注意

robots.txtは検索エンジンや自動クローラー向けのアクセス方針を伝えるファイルです。正規アカウントでログインできる場合でも、robots.txt、利用規約、契約、サイト運営者からの許可を必ず確認してください。
