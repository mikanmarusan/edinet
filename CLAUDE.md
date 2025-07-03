# CLAUDE.md

このファイルはClaude Code (claude.ai/code)がこのリポジトリで作業する際のガイダンスです。

## プロジェクト概要

**edinet** - EDINETから上場企業の開示情報を取得・処理するツール
- EDINET: 日本の企業情報電子開示システム
- 日次で財務データを自動取得し、構造化されたJSONとして保管
- Python 3.x + requests/lxml/argparse

## アーキテクチャ

```
edinet/
├── bin/                    # 実行可能スクリプト
├── lib/                    # 共有ライブラリ（edinet_common.py, xbrl_parser.py）
├── data/jsons/            # 出力データ
└── .ai-rules/             # 詳細な開発ルール
```

## 重要な設計原則

1. **DRY**: lib/モジュールで共通処理を集約
2. **フェイルセーフ**: 個別エラーで全体停止を避ける
3. **明示的 > 暗黙的**: 必須パラメータにデフォルト値なし
4. **API制限遵守**: 1リクエスト/秒

## 開発規約

### 基本ルール
- Python PEP 8準拠
- 関数名: snake_case
- 定数: UPPER_SNAKE_CASE
- エラーは個別に処理し、ログ記録

### データ形式
- 証券コード: 4桁（末尾0削除）
- 決算期: YYYY年M月期（先頭0なし）
- 財務データ優先: 連結 > 個別、当期 > 過去

### プロジェクト固有の用語
- **docID**: EDINET文書ID
- **secCode**: 証券コード
- **periodEnd**: 決算期末
- **XBRL**: 財務情報標準フォーマット

## 詳細ルールへの参照

以下のドキュメントで詳細を確認：

### 必須参照
- `.ai-rules/product_requirement_document.md` - プロダクト要件
- `.ai-rules/coding-standards.md` - コーディング規約詳細
- `.ai-rules/security.md` - セキュリティ指針
- `.ai-rules/performance.md` - パフォーマンス最適化

### 開発プロセス
- `.ai-rules/git-workflow.md` - Git運用ルール
- `.ai-rules/development-patterns.md` - 開発パターン
- `.ai-rules/testing.md` - テスト戦略
- `.ai-rules/deployment.md` - デプロイ設定

### その他
- `.ai-rules/documentation.md` - ドキュメント作成
- `.ai-rules/dependencies.md` - 依存関係管理
- `.ai-rules/api-design.md` - API設計（将来用）
- `.ai-rules/database.md` - DB設計（将来用）

## クイックリファレンス

**日次データ取得**:
```bash
python bin/fetch_edinet_financial_documents.py --date YYYY-MM-DD --outputdir data/jsons --api-key YOUR_KEY
# 特定企業のみ取得（--sec-codes オプション）
python bin/fetch_edinet_financial_documents.py --date YYYY-MM-DD --outputdir data/jsons --api-key YOUR_KEY --sec-codes 7203,9984,4755
```

**データ統合**:
```bash
python bin/consolidate_documents.py --inputdir data/jsons --output data/edinet.json
```

## Webビューア（/docs）

**概要**: data/edinet.jsonを可視化するWebツール（GitHub Pages用）

### 実装済み機能
- 固定ヘッダー（タイトル＋テーブル列名）
- 証券コード検索（部分一致、自動スクロール＋ハイライト）
- 事業内容の省略表示（20文字＋ホバーで全文）
- トップへ戻るボタン（左下、300px以上で表示）
- 金額は百万円単位、null値は「-」表示

### 技術ポイント
- ヘッダー固定: `position: fixed !important`（インライン）
- テーブルヘッダー: `position: sticky`＋コンテナ内スクロール
- 詳細は`.ai-rules/web-viewer.md`参照

## 開発時の注意
新機能追加やバグ修正の際は、必ず`.ai-rules/`配下の関連ドキュメントを参照してください。

## Issue対応時のブランチ作成ルール

### 必須：開発用ブランチの作成
Issueを解決する作業を行う場合は、**必ず開発用のブランチを作成**してから作業を開始してください：

```bash
# ブランチ名の形式: fix/issue-{番号}-{簡潔な説明}
# 例：Issue #40（マジックナンバーの修正）の場合
git checkout -b fix/issue-40-magic-numbers

# 例：Issue #32（ドキュメント更新）の場合
git checkout -b fix/issue-32-update-docs
```

### ブランチ命名規則
- **fix/**: バグ修正や問題解決
- **feat/**: 新機能追加
- **docs/**: ドキュメントのみの変更
- **refactor/**: コードのリファクタリング
- **test/**: テストコードの追加・修正

### ワークフロー
1. mainブランチから最新の状態を取得
2. 開発用ブランチを作成
3. 作業実施とコミット
4. テスト実行と確認
5. Pull Requestを作成してmainブランチにマージ

## コミット前の必須事項

### テスト実行
コードを変更した場合、**必ずテストを実行してから**コミットしてください：

```bash
# 全てのテストを実行
python -m pytest tests/ -v

# 特定のテストファイルを実行
python -m pytest tests/test_stock_exchange_mapping.py -v
```

### テスト実行の確認ポイント
1. 全てのテストが合格（PASSED）していること
2. 新機能を追加した場合は、対応するテストコードも作成すること
3. 既存のテストが壊れていないことを確認すること

### 推奨される開発フロー
1. 機能の実装/バグ修正
2. テストコードの作成/更新
3. **テストの実行と合格確認**
4. コミットメッセージの作成
5. git commit

この手順を守ることで、コードの品質と安定性を保つことができます。

## Issueフォーマット

### 必須：Issue作成時のフォーマット
すべてのIssueは以下のフォーマットに従って作成してください。Agentic Coding Tool（Claude Code等）がIssueを作成する際も**必ずこのフォーマットを使用**すること：

```markdown
#### Goal
[このIssueで達成したい目的を明確に記載]

#### Return Format
[期待される成果物の形式（コード修正、ドキュメント更新、新機能実装など）]

#### Warnings
[作業時の注意点、既知の制約事項、影響範囲など。なければ「なし」と記載]

#### Additional Context
[関連するIssue番号、参考資料、背景情報など。なければ「なし」と記載]
```

### フォーマット各項目の説明

- **Goal**: Issueの目的を簡潔に説明。何を解決したいのか、何を実現したいのかを明確にする
- **Return Format**: 完了条件を明確にするため、期待される成果物を具体的に記載
- **Warnings**: 作業時に注意すべき点、他の機能への影響、パフォーマンスへの考慮事項など
- **Additional Context**: 関連Issue、参考URL、スクリーンショット、技術的背景など補足情報

### 例

```markdown
#### Goal
EDINETデータ取得時のレート制限エラーを適切にハンドリングし、リトライ機能を実装する

#### Return Format
- lib/edinet_common.pyにリトライロジックを追加
- エラーログの改善
- テストコードの追加

#### Warnings
- EDINET APIの1秒1リクエスト制限を厳守すること
- 既存の処理フローを崩さないよう注意

#### Additional Context
- 関連: Issue #15（API制限に関する議論）
- 参考: EDINET API仕様書のレート制限セクション
```

### Agentic Coding Toolへの指示
Claude CodeやGitHub Copilot等のAIツールでIssueを作成する場合：
1. 必ず上記のフォーマットを使用すること
2. 各項目は省略せず、該当なしの場合も「なし」と明記すること
3. Goalは具体的かつ測定可能な内容にすること