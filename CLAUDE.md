# CLAUDE.md

このファイルはClaude Code (claude.ai/code)がこのリポジトリで作業する際のガイダンスです。
**WHY（なぜ） / WHAT（なにを） / HOW（どうやって）** の3部構成で記述します。

---

## WHY — 目的と背景

**edinet** は、EDINET（日本の企業情報電子開示システム）から上場企業の開示情報を取得・処理するツールです。

- **目的**: 上場企業の財務データを日次で自動取得し、構造化されたJSONとして保管・公開する。
- **背景**: EDINETは有価証券報告書等を提供するが、機械可読な統合データセットは提供しない。本ツールはXBRLを解析し、Yahoo Financeの市場データで補完して、横断分析可能なデータセットを生成する。
- **公開**: 生成データはWebビューア（`web/`）とともにGitHub Pages（`gh-pages`ブランチ）で `https://mikanmarusan.net/edinet/` に公開される。
- **技術スタック**: Python 3.x + requests / lxml / argparse / playwright

---

## WHAT — アーキテクチャと設計判断

### ディレクトリ構成

```
edinet/
├── bin/                     # 実行可能スクリプト
├── lib/                     # 共有ライブラリ
│   ├── edinet_common.py     # EDINET API共通処理
│   ├── xbrl_parser.py       # XBRL解析処理
│   ├── ticker_generator.py  # Yahoo Finance用ティッカー生成
│   ├── url_generator.py     # Yahoo Finance URL生成
│   └── data_scraper.py      # Yahoo Financeスクレイピング
├── data/jsons/              # 出力データ（日次JSON）
├── data/edinet.json         # 統合データ
├── web/                     # 公開Webビューアのソース（gh-pagesへ配信）
├── docs/                    # 内部ドキュメント（GitHub Pages非公開）
│   ├── architecture.md      # アーキテクチャ設計
│   ├── context/             # プロダクト要件・XBRL知見・変更履歴
│   └── examples/            # 実装パターン例
├── .github/                 # ワークフロー・Issue/PRテンプレート
└── .claude/                 # Claude Code用ルール・スキル・設定
    ├── rules/               # 開発ルール・ガイドライン
    ├── skills/              # スキル（例: update-stock-exchange-mapping）
    ├── agents/              # エージェント定義
    └── settings.json
```

> **ボイラープレートからの意図的な逸脱**: 本プロジェクトはPythonプロジェクトとして `src/` を導入せず、既存の `bin/`（実行可能スクリプト）+ `lib/`（共有モジュール）構成を維持する。これは確立された慣習に基づく意図的な設計判断である。

### ドキュメント・ファイル配置の方針

それぞれの配置先は「役割」で決める。新たにドキュメントやファイルを追加する際の指針：

- **`docs/`（プロジェクトの背景・仕様・知識 = What/Why）**: このプロジェクトを理解するための背景情報。プロダクト要件、アーキテクチャ、ドメイン知識、変更履歴など。
- **`docs/examples/`（コード例・実装パターン）**: 具体的なコードやその解説。実装パターン、データ抽出例、エラーハンドリング例など。
- **`.claude/rules/`（手順書・ガイドライン・ルール = How）**: 何かを実行するための手順やルール。開発手順、コーディング規約、デプロイ手順、テスト方法など。
- **`.claude/skills/`（スキル）**: Claude Codeが実行する自動化スキル（`SKILL.md` 形式）。
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

### 最近の重要な更新

**Yahoo Finance統合の完了（2025年7月）**: Yahoo Financeデータとの統合により、新たに以下のフィールドが追加された。

- **ordinaryIncome**: 経常利益
- **ordinaryIncomeRate**: 経常利益率
- **issuedDate**: 有価証券報告書の提出日

詳細な変更履歴と技術的な学習事項は `docs/context/changelog.md` を参照。

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
```

**データ統合**:
```bash
python bin/consolidate_documents.py --inputdir data/jsons --output data/edinet.json
```

### Issue対応時の必須事項

#### 開発手順（必ず順番通りに実行）
1. **ブランチ作成**: `git checkout -b fix/issue-{番号}-{簡潔な説明}`
2. **実装**: コード変更を実施
3. **テスト実行**: `python -m pytest tests/ -v`
4. **コミット**: 適切なコミットメッセージで変更を記録
   - 形式: `<type>: <description>`
   - 例: `fix: improve company characteristic extraction logic`
5. **PR作成**: 必要に応じてPull Requestを作成

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

新機能追加やバグ修正の際は、必ず以下の関連ドキュメントを参照すること。

**プロジェクトコンテキスト（`docs/`）**
- `docs/architecture.md` - アーキテクチャ設計
- `docs/context/product-requirements.md` - プロダクト要件
- `docs/context/xbrl-taxonomy-notes.md` - XBRL構造の理解と学習事項
- `docs/context/changelog.md` - 変更履歴・学習事項

**開発ルール（`.claude/rules/`）**
- `coding-standards.md` - コーディング規約
- `git-workflow.md` - Git運用ルール
- `security.md` - セキュリティ指針
- `documentation.md` - ドキュメント作成
- `debugging-guide.md` - デバッグ手法
- `deployment.md` - デプロイ設定
- `performance-guidelines.md` - パフォーマンス最適化
- `testing-guidelines.md` - テスト戦略
- `web-viewer-guide.md` - Webビューア実装

**実装例（`docs/examples/`）**
- `development-patterns.md` - 開発パターン
- `xbrl-extraction-patterns.md` - XBRL抽出パターン例

**スキル（`.claude/skills/`）**
- `update-stock-exchange-mapping/` - 地方取引所マッピングの四半期更新

**テンプレート（`.github/`）**
- `.github/ISSUE_TEMPLATE/issue-template.md` - Issueテンプレート
- `.github/PULL_REQUEST_TEMPLATE.md` - PRテンプレート

---

## Lessons

- 新しいモジュールレベルの定数やデータテーブル（許可リスト等）を追加するときは、その定数が記述する振る舞いを検証するテストから必ず参照すること。参照されない定数はデッドコードとして扱われる。
- 外部のXML/テキストを正規表現で解析するときは、よくあるケースだけでなく有効な入力のすべての異形（例: XML属性値のシングルクォートとダブルクォートの両方）を受け付けること。
- フィールドの取得元を切り替える（例: Yahoo→XBRL）際は、対象フィールドを実際に含むフィクスチャで非null抽出を検証する正例テストを必ず追加すること。対象タグを省いたフィクスチャのテストは、抽出が壊れても緑のままになり回帰を見逃す。
