# Deployment

GitHub Actions による自動実行のみ。環境は本番の1つだけで、環境別の設定分岐は持たない。

ワークフローの中身は基本的に `.github/workflows/` を直接読むこと。ただし以下の項目（スケジュールの生cron値・ステップ順・secrets）は、プロースのみの記述が一年間気づかれない9時間ずれを生んだ実例（#204）を踏まえ、YAMLと意図的に二重化してここに残す。**この二重化は意図的なものであり、YAML側を変更したときは同じPRでこのファイルも更新すること。**それ以外の運用上の判断や依存関係（実行順・トリガー連鎖）は引き続きここに記す。

## ワークフロー一覧と依存関係

3つのワークフローが存在し、`edinet-fetcher.yml` → `deploy-pages.yml` の順で連鎖する。`tests.yml` は独立している。

### `edinet-fetcher.yml`

- スケジュール: `cron: '0 3 * * *'`（UTC 03:00 = **12:00 JST**）で毎日実行される。`workflow_dispatch` による手動実行も可能。
- Python 3.11 を使用し、`make install`（内部で `uv sync`）が依存関係をインストールする。
- secrets: `EDINET_API_KEY`（EDINET API呼び出し用、リポジトリSecretsへの登録が必要）、`GITHUB_TOKEN`（コミット・プッシュ用、Actionsが自動付与）。
- `concurrency: { group: edinet-fetcher, cancel-in-progress: false }` — 上場廃止銘柄の更新とコミットが並行実行で競合しないよう直列化している。
- ステップ順: `fetch_edinet_financial_documents.py --no-market-data` → `update_delisted_companies.py` → `consolidate_documents.py --delisted` → コミット → プッシュ。
- 最後の2ステップでは `github-actions[bot]` アイデンティティが生成物（`data/jsons/` 等）を `main` へ直接コミット・プッシュする。これは `github-actions[bot]` 専用の自動化であり、人間・エージェントの作業に対する例外ではない。人間・エージェントの作業は引き続き `git-workflow.md` の通りブランチとPR経由で行うこと。

### `deploy-pages.yml`

- `edinet-fetcher.yml` の成功を `workflow_run` で検知して自動実行される（`workflow_dispatch` による手動実行も可）。
- `web/` と `data/edinet.json`（`data.json` にリネーム）を `gh-pages` ブランチへ `force_orphan: true` で公開する（履歴を切り捨てて日次 `data.json`（約4.7MB）によるリポジトリ肥大を防ぐ）。
- `concurrency: { group: deploy-pages, cancel-in-progress: false }`。
- **CNAME禁止**: このリポジトリに `CNAME` ファイルを置いてはならない。`edinet` は独自ドメインを持たないプロジェクトサイトで、apexドメインはユーザーサイト側が保有するため、置くとapexドメインと衝突する。この事実は `CLAUDE.md` にも記載されているが、apex衝突という本番障害に直結するため意図的に二重化している。

### `tests.yml`

- `push` と `pull_request` をトリガーに、Python 3.11 / 3.12 / 3.13 のマトリクスでテストスイートを実行する。

## 必要なシークレット

- `EDINET_API_KEY` — リポジトリのSecretsに登録。**コード・ログ・設定ファイルに平文で書かないこと。**

## デプロイ前の確認

- 依存関係の正は `pyproject.toml` / `uv.lock`（`make install` が実行する `uv sync` が参照する）。`requirements.txt` は `install-legacy` 用の互換パスだが、`tests.yml` がCIで直接 `pip install -r requirements.txt` するため、`pyproject.toml` 変更時は必ず追従させること（放置するとCIが古い依存関係で走る）。
- APIキーの扱いは `security.md` を参照。

## 障害時の扱い

- 日次取得が失敗しても前日までのデータは `data/jsons/` に残るため、統合結果は前日分で継続する。復旧は該当日を指定した手動再実行でよい。
- 個別文書の失敗で全体を止めない（フェイルセーフ原則）。失敗は集計してログ末尾に報告される。

## 監視・ログ

- ログは `fetch_edinet_financial_documents_YYYYMMDD.log` としてリポジトリルートに出力される。定期的に整理すること。
- 上場廃止銘柄検出（`update_delisted_companies.py`）の失敗は段階的にエスカレーションする: 1回連続失敗 → 警告、2回 → `$GITHUB_STEP_SUMMARY` に記録、3回 → `exit 1` でステップを失敗させる。

## 運用上の注意

- EDINET APIのレート制限（1リクエスト/秒）を必ず守る。並列化しない。
