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

## 最近の重要な修正

### 市場時価総額計算の修正
- **問題**: 自己株式数のみを使用して市場時価総額を計算していた
- **原因**: EDINETのXBRLパターンの理解不足により、誤ったデータ要素を抽出
- **解決**: 正しいEDINETパターン `NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc` を最優先に設定
- **重要な学習**: 
  - 市場時価総額 = 株価 × 発行済株式総数（自己株式を含む）
  - EDINETタクソノミーの正確な理解が必要
  - 存在しないパターン名を使用しないこと

### 非連結財務諸表の条件付き処理
- **問題**: 連結財務諸表を持たない企業のデータが取得できない
- **原因**: NonConsolidatedMemberコンテキストのデータを一律除外していた
- **解決**: 連結財務諸表が存在しない場合のみ非連結データを使用
- **実装仕様**:
  - `_has_consolidated_data`メソッドで連結データの有無を判定
  - 連結データがある場合：従来通り連結データを優先（NonConsolidatedMember除外）
  - 連結データがない場合：NonConsolidatedMemberデータを使用
  - 過去データは除外（CurrentYearコンテキストのみ使用）
- **対象メソッド**: 
  - `extract_numeric_value_with_context`および全動的検索メソッド

### 連結・個別データの優先順位改善（2025年7月）
- **問題**: 連結財務諸表を持つ企業でも個別（提出会社）データを取得してしまうバグ
- **原因**: コンテキスト優先度の判定ロジックが不十分
- **解決**: 
  - BusinessResultsOfGroupコンテキストを最優先に設定（+50〜80ポイント）
  - ReportingCompanyコンテキストにペナルティ付与（-30ポイント）
  - 連結データ検出ロジックの強化
- **学習ポイント**:
  - XBRLのコンテキスト構造を正確に理解することが重要
  - BusinessResultsOfGroup = 連結データの最も確実な指標
  - ReportingCompany = 個別データの指標
  - 優先度スコアリングによる柔軟な判定が有効

### issuedDateフィールドの追加（2025年7月）
- **概要**: 有価証券報告書の提出日をJSONに記録
- **フィールド仕様**:
  - フィールド名: `issuedDate`
  - データ型: 文字列
  - フォーマット: `YYYY-MM-DD`（ISO 8601形式）
  - データソース: `--date`パラメータ（コマンドライン引数）
  - JSON内位置: `cash`の後、`retrievedDate`の前
- **実装詳細**:
  - `XBRLParser.parse_financial_data()`に`issued_date`パラメータ追加
  - `XBRLParser._build_financial_data_structure()`に`issued_date`パラメータ追加
  - `fetch_edinet_financial_documents.py`から`args.date`を渡す
- **目的**: 
  - 有価証券報告書の提出日を記録し、時系列分析を可能にする
  - `retrievedDate`（データ取得日）と区別して実際の報告書提出日を保持

### Yahoo Finance統合の実装（2025年7月）
- **概要**: EDINETデータをYahoo Financeのリアルタイム市場データで補完
- **新規ライブラリ**:
  - `lib/ticker_generator.py`: 証券コードからYahooティッカーシンボルへの変換
  - `lib/url_generator.py`: Yahoo Finance URLの生成
  - `lib/data_scraper.py`: Playwrightを使用したWebスクレイピング
- **技術的変更**:
  - Headless Browser (Playwright) を使用したデータ取得
  - EDINETデータ取得後にYahoo Financeから補完データを取得
  - 失敗時はEDINETデータのみで処理を継続（フェイルセーフ）
- **データソース詳細**:
  - **Yahoo Financeから取得**: characteristic, stockPrice, netSales, employees, operatingIncome, ordinaryIncome（新規）, depreciation, bps, debt, outstandingShares, netIncome, eps
  - **EDINETから取得**: equity, cash（財務諸表の正式な値が必要なため）
  - **計算値**: operatingIncomeRate, ordinaryIncomeRate（新規）, ebitda, ebitdaMargin, marketCapitalization, per, ev, evPerEbitda, pbr
- **注意事項**:
  - レート制限未実装（Issue #91）
  - ブラウザインスタンスの最適化が必要（Issue #92）
  - デバッグprint文の削除が必要（Issue #90）
