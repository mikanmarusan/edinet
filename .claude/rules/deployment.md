# Deployment

GitHub Actions による自動実行のみ。環境は本番の1つだけで、環境別の設定分岐は持たない。

ワークフローの中身は `.github/workflows/` を直接読むこと。ここには YAML から読み取れない運用上の判断と、3つのワークフローの関係のみを記す。

## ワークフロー一覧

### EDINET Fetcher（`.github/workflows/edinet-fetcher.yml`）

- スケジュール: `cron: '0 3 * * *'`（UTC 03:00 = **12:00 JST**）。加えて `workflow_dispatch` による手動実行も可能。
- `concurrency: group: edinet-fetcher, cancel-in-progress: false` — 上場廃止検出結果の更新とコミットが並行実行で競合しないよう直列化している。
- Python は 3.11 に固定。依存関係は `make install`（内部で `uv sync`）でインストールする。
- 使用するシークレット: `EDINET_API_KEY`、`GITHUB_TOKEN`。
- ステップ順序: 取得（`fetch_edinet_financial_documents.py --no-market-data`） → `update_delisted_companies.py`（上場廃止検出） → `consolidate_documents.py --delisted`（統合） → コミット → プッシュ。
- 最終ステップは `git push origin main` を実行するが、これは `github-actions[bot]` アイデンティティによるワークフロー内の自動コミット・プッシュであり、人間・エージェントによる作業がブランチとPRを経由するという方針（`CLAUDE.md`・`.claude/rules/git-workflow.md` に既出）を変えるものではない。

### Deploy Pages（`.github/workflows/deploy-pages.yml`）

- トリガー: EDINET Fetcher の成功を受けた `workflow_run`、および手動公開用の `workflow_dispatch`。
- `concurrency: group: deploy-pages, cancel-in-progress: false` で直列化している。
- 公開内容: `web/` 一式 + `data/edinet.json` を `data.json` にリネームしたもの。公開先は `gh-pages` ブランチ、`force_orphan: true`（日次 `data.json` が約4.7MBあるため履歴肥大を防ぐ。詳細は本ファイル末尾「運用上の注意」も参照 — 意図的な重複記載）。
- **CNAME禁止（意図的な重複記載）**: `edinet` は独自ドメインを持たないプロジェクトサイトで、apexドメイン `mikanmarusan.net` はユーザーサイト側が保有する。このリポジトリに `CNAME` ファイルを置いてはならない（apexドメインと衝突するため）。この一文は `CLAUDE.md` にも記載があるが、本番障害（apexドメイン衝突）に直結する内容のため、ここでも意図的に重複させている。

### tests（`.github/workflows/tests.yml`）

- トリガー: `push` と `pull_request`。
- Python 3.11 / 3.12 / 3.13 のマトリクスで pytest スイートを実行する。

## 必要なシークレット

- `EDINET_API_KEY` — リポジトリのSecretsに登録。**コード・ログ・設定ファイルに平文で書かないこと。**
- `GITHUB_TOKEN` — 登録不要・自動発行。EDINET Fetcher のチェックアウト・コミット・プッシュ、Deploy Pages の `gh-pages` へのプッシュに使われる、GitHub Actionsが自動発行するトークン。

## 障害時の扱い

- 日次取得が失敗しても前日までのデータは `data/jsons/` に残るため、統合結果は前日分で継続する。復旧は該当日を指定した手動再実行でよい。
- 個別文書の失敗で全体を止めない（フェイルセーフ原則）。失敗は集計してログ末尾に報告される。
- 上場廃止検出（`update_delisted_companies.py`）はJPXデータ取得の失敗回数に応じて段階的にエスカレーションする: 1回連続失敗で警告、2回連続失敗で `$GITHUB_STEP_SUMMARY` にも警告を追記、3回連続失敗で `exit 1` によりステップが失敗する。

## デプロイ前の確認

- 依存関係の正本は `pyproject.toml` / `uv.lock`（`make install` が実行する `uv sync` が参照する）。`tests.yml` が使う `requirements.txt` は旧経路であり、`pyproject.toml` を変更した際は両者の内容が食い違っていないか確認すること。

## 運用上の注意

- EDINET APIのレート制限（1リクエスト/秒）を必ず守る。並列化しない。
- ログは `fetch_edinet_financial_documents_YYYYMMDD.log` としてリポジトリルートに出力される。定期的に整理すること。
- 日次 `data.json` が約4.7MB あるため、Pages公開は `force_orphan: true` で履歴を切り捨てている。
