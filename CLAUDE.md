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