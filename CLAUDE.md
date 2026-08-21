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

**データ統合**:
```bash
python bin/consolidate_documents.py --inputdir data/jsons --output data/edinet.json
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

`.claude/rules/` は常時読み込まれるためここには列挙しない。以下は必要に応じて開くこと。

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
- 常時読み込まれる指示ファイル（`CLAUDE.md` / `.claude/rules/`）には、`ls` や manifest から導出できる情報（ディレクトリ構成・依存一覧・ファイル索引）と、実在しないコードの例示を書かないこと。前者は毎セッションの無駄なコストになり、後者は実装済み機能と誤読される。
