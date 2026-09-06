# CLAUDE.md

このファイルはClaude Code (claude.ai/code)がこのリポジトリで作業する際のガイダンスです。
**WHY（なぜ） / WHAT（なにを） / HOW（どうやって）** の3部構成で記述します。

---

## WHY — 目的と背景

**edinet** は、EDINET（日本の企業情報電子開示システム）から上場企業の開示情報を取得・処理するツールです。

- **目的**: 上場企業の財務データを日次で自動取得し、構造化されたJSONとして保管・公開する。
- **背景**: EDINETは有価証券報告書等を提供するが、機械可読な統合データセットは提供しない。本ツールはXBRLを解析し、Yahoo Financeの市場データで補完して、横断分析可能なデータセットを生成する。
- **公開**: 生成データはWebビューア（`web/`）とともにGitHub Pages（`gh-pages`ブランチ）で `https://mikanmarusan.net/edinet/` に公開される。

---

## WHAT — アーキテクチャと設計判断

### ボイラープレートからの意図的な逸脱

本プロジェクトはPythonプロジェクトとして `src/` を導入せず、`bin/`（実行可能スクリプト）+ `lib/`（共有モジュール）構成を維持する。これは確立された慣習に基づく意図的な設計判断であり、`src/` レイアウトへ移行してはならない。

### ディレクトリ構成

役割ごとの主要ディレクトリ（ファイル単位の網羅列挙はしない。個々のファイル名は、名前自体が構造的な意味を持つ場合のみ挙げる）:

- `bin/` — 実行可能スクリプト（パイプラインの各段）: `fetch_edinet_financial_documents.py`（日次取得）、`update_delisted_companies.py`（上場廃止検出）、`consolidate_documents.py`（統合）
- `lib/` — 共有モジュール（`delisted_detector.py` を含む6モジュール）。モジュール間の依存関係は `docs/architecture.md` の「Module Dependencies」が正本
- `config/` — 証券取引所マッピング（`stock_exchange_mapping.yml`）
- `data/` — 出力データ（`jsons/` に日次JSON、`edinet.json` に統合データ、`delisted_companies.yml` に上場廃止検知結果）
- `tests/` — pytestスイート
- `web/` — 公開Webビューアのソース（`web/CLAUDE.md` を参照）
- `docs/` — 内部ドキュメント（本ファイル下部の「詳細ドキュメントへの参照」を参照）
- `.claude/agents/` — サブエージェント定義の配置先。現時点では `.gitkeep` のみで未使用だが、配置ルールとして維持する
- `Makefile` — `make install` で依存インストール（`uv sync`）を実行
- `pyproject.toml` / `uv.lock` — 依存関係定義（uv管理）

### ドキュメント・ファイル配置の方針

それぞれの配置先は「役割」で決める。新たにドキュメントやファイルを追加する際の指針：

- **`docs/`（プロジェクトの背景・仕様・知識 = What/Why）**: このプロジェクトを理解するための背景情報。プロダクト要件、アーキテクチャ、ドメイン知識、変更履歴など。
- **`docs/examples/`（コード例・実装パターン）**: 具体的なコードやその解説。実装パターン、データ抽出例、エラーハンドリング例など。
- **`.claude/rules/`（手順書・ガイドライン・ルール = How）**: 常時読み込まれるため、**セッションを問わず必要な短いルールのみ**を置く。特定タスクでしか使わない手順は `.claude/skills/` に置くこと。
- **`.claude/skills/`（スキル）**: Claude Codeが実行する自動化スキル（`SKILL.md` 形式）。呼び出し時のみ本文が読み込まれる。
- **`.claude/agents/`（エージェント定義）**: サブエージェント定義。
- **`.github/`（雛形・テンプレート）**: そのままコピーして使うことを想定したファイル。Issue/PRテンプレートなど。

### 公開（GitHub Pages）

- 公開ソースは `gh-pages` ブランチ。`.github/workflows/deploy-pages.yml` が `web/*` と `data/edinet.json`（`data.json` にリネーム）を公開する。
- `edinet` は独自ドメインを持たない**プロジェクトサイト**で、apexドメイン `mikanmarusan.net` はユーザーサイト側が保有する。**このリポジトリに `CNAME` ファイルを置いてはならない**（apexドメインと衝突するため）。

### 重要な設計原則

1. **DRY**: lib/モジュールで共通処理を集約
2. **フェイルセーフ**: 個別エラーで全体停止を避ける
3. **明示的 > 暗黙的**: 必須パラメータにデフォルト値なし
4. **API制限遵守**: 1リクエスト/秒

### データ形式

- 証券コード: 4桁（末尾0削除）
- 決算期: YYYY年M月期（先頭0なし）
- 財務データ優先: 連結 > 個別、当期 > 過去

変更履歴と技術的な学習事項は `docs/context/changelog.md` を参照。

---

## HOW — 開発ワークフロー

### コーディング規約（基本ルール）

- Python PEP 8準拠
- 関数名: snake_case、定数: UPPER_SNAKE_CASE
- エラーは個別処理しログ記録

### クイックリファレンス

**日次データ取得**:
```bash
python bin/fetch_edinet_financial_documents.py --date YYYY-MM-DD --outputdir data/jsons --api-key YOUR_KEY
# 特定企業のみ: --sec-codes 7203,9984,4755
# 市場データ取得をスキップ（Yahooにアクセスせず stockPrice/marketCapitalization と派生指標 per/pbr/ev/evPerEbitda を null にする）: --no-market-data
```

**上場廃止検出**（`edinet-fetcher.yml` では取得の直後・統合の直前に実行）:
```bash
python bin/update_delisted_companies.py --jsonsdir data/jsons --mapping config/stock_exchange_mapping.yml --output data/delisted_companies.yml
```

**データ統合**:
```bash
python bin/consolidate_documents.py --inputdir data/jsons --output data/edinet.json --delisted data/delisted_companies.yml
```

### テスト（要点のみ）

```bash
uv run python -m pytest tests/ -v
```

- **`tests/golden/golden_baseline.json` を手で編集してはならない。** 必ず `REGEN_GOLDEN=1 python -m pytest tests/test_golden_regression.py` で再生成する。
- 抽出ロジックを意図的に変更したときは、先に `tests/test_golden_regression.py` の `EXPECTED_CHANGES` に追記する（さもないとCIが `REGRESSION` で落ちる）。
- CIは `tests/test_stock_exchange_mapping.py` の地方取引所3テストを既知失敗として `--deselect` している。

フィクスチャの追加、ゴールデン再生成、Webビューアのテスト実行など詳細な手順は `.claude/skills/running-tests/` を参照（呼び出し時に読み込まれる）。

### Issue対応時の必須事項

#### 開発手順（必ず順番通りに実行）
1. **ブランチ作成**: `git checkout -b <type>/<issue番号>-<kebab-case-description>`（例: `fix/123-null-pointer`）
2. **実装**: コード変更を実施
3. **テスト実行**: `python -m pytest tests/ -v`
4. **コミット**: Conventional Commits 形式で変更を記録
   - 形式: `<type>(<scope>): <short summary>`（72文字以内、命令形、末尾ピリオドなし）
   - 例: `fix(xbrl): improve company characteristic extraction logic`
5. **PR作成**: 必要に応じてPull Requestを作成（タイトルはコミット1行目と同形式）

#### Issueフォーマット
- Goal: 達成したい目的
- Return Format: 期待される成果物
- Warnings: 注意点（なければ「なし」）
- Additional Context: 関連情報（なければ「なし」）

#### 重要な注意事項
- **mainブランチでの直接作業は厳禁**
- 必ず機能ブランチを作成してから作業を開始すること
- テストが通ることを確認してからコミットすること

### 詳細ドキュメントへの参照

**ルール（`.claude/rules/`、常時読み込み。索引がないルールは見つけられないため一覧化する）**
- `coding-standards.md` - コーディング規約・フェイルセーフ原則・欠損値の扱い
- `debugging-guide.md` - XBRL抽出の典型的な不具合と切り分け手順
- `deployment.md` - GitHub Actionsによるデプロイと障害時の扱い
- `documentation.md` - コード内ドキュメント・変更履歴の記録方法
- `git-workflow.md` - ブランチ・コミット・PRの運用
- `performance-guidelines.md` - APIレート制限とボトルネック
- `security.md` - APIキーの扱いと外部データの検証

**プロジェクトコンテキスト（`docs/`）**
- `docs/architecture.md` - アーキテクチャ設計
- `docs/context/product-requirements.md` - プロダクト要件
- `docs/context/xbrl-taxonomy-notes.md` - XBRL構造の理解と学習事項
- `docs/context/changelog.md` - 変更履歴・学習事項
- `docs/examples/development-patterns.md` - 開発パターン
- `docs/examples/xbrl-extraction-patterns.md` - XBRL抽出パターン例

**スキル（`.claude/skills/`、呼び出し時のみ読み込み）**
- `update-stock-exchange-mapping/` - 地方取引所マッピングの四半期更新
- `running-tests/` - テスト実行・フィクスチャ追加・ゴールデン再生成の手順

**サブディレクトリ固有のガイダンス**
- `web/CLAUDE.md` - Webビューアの実装ガイド（`web/` 配下の作業時に読み込まれる）

---

## Lessons

- 新しいモジュールレベルの定数やデータテーブル（許可リスト等）を追加するときは、その定数が記述する振る舞いを検証するテストから必ず参照すること。参照されない定数はデッドコードとして扱われる。
- 外部のXML/テキストを正規表現で解析するときは、よくあるケースだけでなく有効な入力のすべての異形（例: XML属性値のシングルクォートとダブルクォートの両方）を受け付けること。
- フィールドの取得元を切り替える（例: Yahoo→XBRL）際は、対象フィールドを実際に含むフィクスチャで非null抽出を検証する正例テストを必ず追加すること。対象タグを省いたフィクスチャのテストは、抽出が壊れても緑のままになり回帰を見逃す。
- 複数のXBRLタグ群を合算する財務指標（有利子負債等）では、二重計上リスク（例: 社債と1年内償還社債）とコンテキストのスコープ整合（連結/個別、現金との差引）を前提条件としてコメントで明示すること。また、置き換えで不要化した旧ロジック（パターン定義・メソッド）は可能な限り同じPRで撤去し、分岐した二重定義を残さないこと。
- スクレイピングしたHTMLから値を抽出する際は、「ラベル以降の最初の数値」のような位置依存ヒューリスティックではなく、値が属する意味的コンテナ（BEMブロック/データ要素）にスコープを限定すること。隣接指標・兄弟要素・ツールチップの数値混入や、ハッシュ化クラス名の変更による誤抽出を防ぐ。
- 同じ入力（例: docID）から派生する複数フィールドにバリデーションを追加する際は、片方だけでなく兄弟フィールドにも一貫して適用すること。検証の非対称性は、片方だけ壊れた値を残す。
- Webビューアに列を追加する際は、`ColumnVisibilityManager.columns` の index 登録・`<th>`・行 `<td>` の3者を必ず同数に揃えること（`applyVisibility` は index→nth-child で表示制御するため、ズレると別列を誤って表示/非表示にする）。
- 候補選択ロジックに決定的タイブレーク（二次ソートキー等）を追加するときは、その分岐が実際に効く条件（＝同点）を満たすフィクスチャを必ず添えて勝者をピン留めすること。同点が発生しないフィクスチャだけでは、タイブレークを外しても緑のままで挙動変化を検出できない。あわせて「本当に同点である」ことをアサート（例: 優先度計算が両候補で等しい）してフィクスチャ自体を守る。
- 常時読み込まれる指示ファイル（`CLAUDE.md` / `.claude/rules/`）に構造情報を書く場合は、ディレクトリ単位＋役割の要約と `.claude/rules/*.md` の索引に留めること。ファイル単位の網羅的なツリーやモジュール依存グラフ（正本は `docs/architecture.md`）、実在しないコードの例示は書かないこと。前者は正本を二重化して次の `mkdir`/`touch` で再び drift し、後者は実装済み機能と誤読される。
- When adding or editing a canonical listing of directories or artifacts, check it against every other section in the same document that already names those artifacts (for example, a command example showing an output file the listing should also mention), not only for internal self-consistency. A listing that only checks itself can still omit an artifact the document's own examples already require.
- When a new sentence in an always-loaded rules file restates a policy established elsewhere, cite only the file(s) that stated that policy before this change. Never cite the file being edited as a prior source of a policy it is stating for the first time here.
- 外部APIのレスポンスは、HTTPステータスだけでなく**それがAPI出力であること自体**（content type・3xxでないこと）を検証してから解析すること。`raise_for_status()` はどちらでも例外を投げないため、失敗はずっと後段のデコードエラーとして手掛かりなく現れる。検証で送出する例外は、その呼び出しを囲む `except` 節の型（例: `requests.exceptions.RequestException`）の外に置き、再ラップで情報が失われないようにする。
- 認証情報がURLのクエリパラメータに乗るAPIでは、**URLを含みうる値をログや例外メッセージへ渡す経路をすべて**塞ぐこと。自前で組み立てるメッセージだけでなく、`str(requests例外)` のように外部ライブラリがURLを埋め込む文字列も対象になる。伏字処理は正規表現ではなく `urllib.parse` で構造的に行い、リダイレクトは自動追従させない（認証情報が意図しないホストへ転送され、レート制限も `session.get()` 1回につき1度しか効かない）。
- When introducing a "this value must never appear in output X" guarantee, first enumerate every producer that can put the value into X - the newly written path, the pre-existing handlers already on that same call path, and third-party emitters at every severity - then place the guard at the point where all of those converge rather than at each producer. A guard that only filters by severity, or that only covers the path being added, leaves the siblings open and the guarantee is false the day one of them fires.
- A test asserting that some string is absent from output is not evidence until it has been shown to fail: build the input in the exact shape the real producer emits (the real exception class and its real message shape, not a hand-written approximation), pin the positive expected output alongside the absence check, and disable the guard once to confirm the test goes red. Negative-only assertions over hand-authored inputs stay green against code that never had the property.
- When migrating a file-format library, audit every other place in the codebase that names, writes, or labels files in that format (temp-file suffixes, filenames, download helpers), not only the parsing function's own body. Many format libraries validate a file by its extension rather than its bytes, so a stale extension elsewhere on the same call path breaks at runtime even while unit tests that mock the library call stay green.
- When a docstring or comment states a fact that changes (for example a file extension or format name), update every sibling docstring/comment in the same file and every mirrored mention in other project docs in the same change, not only the docstring of the function being rewritten.
- When deriving a filename suffix or extension from a URL, parse the URL first and take the extension from its path component alone, never from the raw URL string — reading the extension off the whole string lets a query string or fragment leak into the suffix and misreads a bare-domain URL's host as an extension. Pin the fix with a regression test built from a URL shape that actually carries the corrupting piece, verified to fail without the fix, not only a plain happy-path URL.
