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

## 詳細ルールへの参照

詳細は`.claude/`ディレクトリ内のドキュメントを参照：

### instructions/ - 開発指示
- `coding-standards.md` - コーディング規約
- `git-workflow.md` - Git運用ルール
- `security.md` - セキュリティ指針
- `documentation.md` - ドキュメント作成

### context/ - プロジェクトコンテキスト
- `product-requirements.md` - プロダクト要件
- `architecture.md` - アーキテクチャ設計
- `deployment.md` - デプロイ設定
- `performance-guidelines.md` - パフォーマンス最適化

### examples/ - 実装例とガイド
- `development-patterns.md` - 開発パターン
- `testing-guidelines.md` - テスト戦略
- `web-viewer-guide.md` - Webビューア実装

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

1. **ブランチ作成**: `fix/issue-{番号}-{簡潔な説明}`
2. **テスト実行**: `python -m pytest tests/ -v`
3. **Issueフォーマット**:
   - Goal: 達成したい目的
   - Return Format: 期待される成果物
   - Warnings: 注意点（なければ「なし」）
   - Additional Context: 関連情報（なければ「なし」）

## 開発時の注意

新機能追加やバグ修正の際は、必ず`.claude/`配下の関連ドキュメントを参照してください。