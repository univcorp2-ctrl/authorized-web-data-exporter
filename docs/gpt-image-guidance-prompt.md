# GPT Image 最新モデル用 README先頭画像プロンプト

以下をGPT Image最新モデルに貼り付けると、README先頭に置く初心者向けアーキテクチャ画像を生成できます。

```text
Create a clean Japanese beginner-friendly architecture diagram for a GitHub README.
Title: Authorized Web Data Exporter
Subtitle: ログイン型サイトから、許可されたデータを安定して取得し、CSV / Excel / JSON / TXTへ保存する汎用アーキテクチャ

Use a horizontal flow with eight numbered steps:
1. 設定: YAMLプロファイル、Secrets、開始URL
2. robots.txt確認: Allow / Disallow、Crawl-delay、Sitemap、robots_report.txt
3. ログイン: Playwright Chromium、正規アカウント、セッション再利用
4. 低速巡回: 一覧ページ、ページネーション、待機時間、ジッター
5. 詳細URLキュー: 重複排除、再開可能
6. 抽出: セレクタ、テーブル、定義リスト、本文、画像、リンク
7. チェックポイント: 取得済みURL、エラー、途中再開
8. 出力: CSV、Excel、JSONL、TXT、errors.jsonl、robots_report.txt

Design style:
- 16:9 aspect ratio
- GitHub README friendly
- Japanese labels must be crisp and readable
- Soft blue/green theme
- Simple icons for settings, robots, browser, queue, parser, checkpoint, files
- Add footer note: 並列取得しない / robots.txtを確認する / CAPTCHAや制限は回避しない / 途中停止しても再開できる
```

生成した画像は `docs/assets/architecture-overview.png` として保存し、README先頭の画像リンクをPNGに差し替えてください。現在はGitHubで確実に表示できるSVG版を同梱しています。
