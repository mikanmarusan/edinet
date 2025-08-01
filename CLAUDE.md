# CLAUDE.md

このファイルはClaude Code (claude.ai/code)がこのリポジトリで作業する際のガイダンスです。

## プロジェクト概要

**edinet** - EDINETから上場企業の開示情報を取得・処理するツール
- EDINET: 日本の企業情報電子開示システム
- 日次で財務データを自動取得し、構造化されたJSONとして保管
- Python 3.x + requests/lxml/argparse/playwright

## アーキテクチャ

```
edinet/
├── bin/                    # 実行可能スクリプト
├── lib/                    # 共有ライブラリ
│   ├── edinet_common.py   # EDINET API共通処理
│   ├── xbrl_parser.py     # XBRL解析処理
│   ├── ticker_generator.py # Yahoo Finance用ティッカー生成
│   ├── url_generator.py   # Yahoo Finance URL生成
│   └── data_scraper.py    # Yahoo Financeスクレイピング
├── data/jsons/            # 出力データ
└── .claude/               # Claude Code用の詳細ルール
```

## 重要な設計原則

1. **DRY**: lib/モジュールで共通処理を集約
2. **フェイルセーフ**: 個別エラーで全体停止を避ける
3. **明示的 > 暗黙的**: 必須パラメータにデフォルト値なし
4. **API制限遵守**: 1リクエスト/秒

## 開発規約

### 基本ルール
- Python PEP 8準拠
- 関数名: snake_case、定数: UPPER_SNAKE_CASE
- エラーは個別処理しログ記録

### データ形式
- 証券コード: 4桁（末尾0削除）
- 決算期: YYYY年M月期（先頭0なし）
- 財務データ優先: 連結 > 個別、当期 > 過去

## .claude/ディレクトリ構造の定義

### context/ - プロジェクトの背景・仕様・知識
- **役割**: プロジェクトの「What」と「Why」を説明
- **配置基準**: このプロジェクトを理解するために必要な背景情報
- **内容例**: プロダクト要件、アーキテクチャ、ドメイン知識、変更履歴

### instructions/ - 手順書・ガイドライン・ルール  
- **役割**: 作業の「How」を説明
- **配置基準**: 何かを実行するための手順やルール
- **内容例**: 開発手順、コーディング規約、デプロイ手順、テスト方法

### examples/ - コード例・実装パターン
- **役割**: 「実際のコード」を示す
- **配置基準**: 具体的なコードやその解説
- **内容例**: 実装パターン、データ抽出例、エラーハンドリング例

### templates/ - 雛形・テンプレート
- **役割**: 「コピーして使う」ファイル
- **配置基準**: そのままコピーして使うことを想定したファイル
- **内容例**: Issue/PRテンプレート、設定ファイルの雛形

## 詳細ルールへの参照

詳細は`.claude/`ディレクトリ内のドキュメントを参照：

### context/ - プロジェクトコンテキスト
- `product-requirements.md` - プロダクト要件
- `architecture.md` - アーキテクチャ設計
- `xbrl-taxonomy-notes.md` - XBRL構造の理解と学習事項
- `changelog.md` - 変更履歴・学習事項

### instructions/ - 開発指示
- `coding-standards.md` - コーディング規約
- `git-workflow.md` - Git運用ルール
- `security.md` - セキュリティ指針
- `documentation.md` - ドキュメント作成
- `debugging-guide.md` - デバッグ手法
- `deployment.md` - デプロイ設定
- `performance-guidelines.md` - パフォーマンス最適化
- `testing-guidelines.md` - テスト戦略
- `web-viewer-guide.md` - Webビューア実装

### examples/ - 実装例とガイド
- `development-patterns.md` - 開発パターン
- `xbrl-extraction-patterns.md` - XBRL抽出パターン例

## クイックリファレンス

**日次データ取得**:
```bash
python bin/fetch_edinet_financial_documents.py --date YYYY-MM-DD --outputdir data/jsons --api-key YOUR_KEY
# 特定企業のみ: --sec-codes 7203,9984,4755
```

**データ統合**:
```bash
python bin/consolidate_documents.py --inputdir data/jsons --output data/edinet.json
```

## Issue対応時の必須事項

### 開発手順（必ず順番通りに実行）
1. **ブランチ作成**: `git checkout -b fix/issue-{番号}-{簡潔な説明}`
2. **実装**: コード変更を実施
3. **テスト実行**: `python -m pytest tests/ -v`
4. **コミット**: 適切なコミットメッセージで変更を記録
   - 形式: `<type>: <description>`
   - 例: `fix: improve company characteristic extraction logic`
5. **PR作成**: 必要に応じてPull Requestを作成

### Issueフォーマット
- Goal: 達成したい目的
- Return Format: 期待される成果物
- Warnings: 注意点（なければ「なし」）
- Additional Context: 関連情報（なければ「なし」）

### 重要な注意事項
- **mainブランチでの直接作業は厳禁**
- 必ず機能ブランチを作成してから作業を開始すること
- テストが通ることを確認してからコミットすること

## 開発時の注意

新機能追加やバグ修正の際は、必ず`.claude/`配下の関連ドキュメントを参照してください。

## 最近の重要な更新

### Yahoo Finance統合の完了（2025年7月）
Yahoo Financeデータとの統合により、新たに以下のフィールドが追加されました：
- **ordinaryIncome**: 経常利益
- **ordinaryIncomeRate**: 経常利益率
- **issuedDate**: 有価証券報告書の提出日

詳細な変更履歴と技術的な学習事項は `.claude/context/changelog.md` を参照してください。
