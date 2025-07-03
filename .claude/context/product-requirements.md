# EDINETファイナンシャルデータ分析ソフトウェア要件仕様書

## 1. プロジェクト概要

### 目的
EDINET APIを通じて上場企業の有価証券報告書から財務データを取得・分析するシステム。XBRLデータから財務情報を抽出し、企業財務部門やM&A部門での分析用JSONフォーマットにコンパイルする。

### ターゲットユーザー
- 企業財務部門
- M&Aチームメンバー
- 上場企業情報を調査する財務アナリスト

### システム構成
1. **fetch_edinet_financial_documents.py**: 日次データ抽出ツール
2. **consolidate_documents.py**: データ統合ツール

## 2. 機能要件

### 2.1 日次データ抽出ツール

#### 基本機能
- 指定日のEDINET API経由で有価証券報告書を取得
- XBRLデータから財務メトリクスを抽出
- JSON形式で出力

#### コマンドライン仕様
```bash
python fetch_edinet_financial_documents.py --date YYYY-MM-DD --outputdir data/jsons --api-key YOUR_KEY
# 特定企業のみ: --sec-codes 7203,9984,4755
```

#### 抽出データ項目
| フィールド | 説明 | 例 |
|------------|------|-----|
| secCode | 4桁証券コード | 4384 |
| periodEnd | 決算期末 | 2024年7月期 |
| netSales | 売上高 | 15000000000 |
| operatingIncome | 営業利益 | 1200000000 |
| ebitda | EBITDA | 1500000000 |
| marketCapitalization | 時価総額 | 50000000000 |
| per | PER | 25.5 |
| ev | 企業価値 | 52000000000 |
| equity | 純資産 | 15000000000 |
| debt | ネット有利子負債 | 2000000000 |
| （他多数） | | |

### 2.2 データ統合ツール

#### 基本機能
- 複数のJSONファイルを統合
- 重複企業は最新データを保持
- 統合データをJSON形式で出力

#### コマンドライン仕様
```bash
python consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json
```

## 3. 技術要件

### 3.1 開発環境
- **言語**: Python 3.x
- **外部依存**: EDINET API、XBRLパースライブラリ

### 3.2 API統合
- **エンドポイント**: EDINET API
- **レート制限**: 最大1リクエスト/秒
- **認証**: APIキー必須

### 3.3 XBRL処理

#### 高度な抽出機能
**動的検索アルゴリズム:**
- PER、EPS、発行済株式数の動的タグ検索
- 優先度スコアリングによる最適データ選択
- コンテキスト認識処理（連結優先、当期優先）

**発行済株式数の抽出仕様:**
優先順位：
1. `TotalNumberOfIssuedSharesSummaryOfBusinessResults`
2. `TotalNumberOfIssuedShares`系タグ
3. 動的検索（スコアリング付き）

**証券取引所コード決定:**
- `config/stock_exchange_mapping.yml`から取引所マッピング
- Yahoo Finance URL生成用（T:東証、N:名証、F:福証、S:札証）

## 4. 非機能要件

### 4.1 パフォーマンス
- APIレート制限遵守（1秒間隔）
- 約3,000社の処理能力

### 4.2 エラーハンドリング
- 欠損データはスキップして処理継続
- ネットワークエラーは適切な遅延でリトライ

### 4.3 ロギング
- コンソール出力 + ファイルログ
- ログファイル名: `{script_name}_{YYYYMMDD}.log`

## 5. Webビューア機能

### 5.1 概要
`/docs`配下のWebビューアは、財務データを閲覧・検索・エクスポートするツール。

### 5.2 主要機能
- データ表示（約4,000社）
- 証券コード検索
- 固定ヘッダー・固定列
- 事業内容省略表示
- トップへ戻るボタン

### 5.3 Excelエクスポート
- ファイル形式: .xlsx
- ファイル名: `edinet_data_YYYYMMDD.xlsx`
- 全20カラムをエクスポート
- SheetJSでクライアントサイド処理

## 6. システム統合

### 6.1 ファイル構成
```
project/
├── bin/
│   ├── fetch_edinet_financial_documents.py
│   └── consolidate_documents.py
├── lib/
│   ├── edinet_common.py
│   └── xbrl_parser.py
├── config/
│   └── stock_exchange_mapping.yml
└── data/
    ├── jsons/
    └── edinet.json
```

### 6.2 データフロー
```
EDINET API → XBRL → fetch_edinet → 日次JSON → consolidate → 統合JSON
```

## 7. 制約事項

### 7.1 外部依存
- EDINET APIの可用性
- XBRL形式の一貫性
- ネットワーク接続

### 7.2 データ制限
- 企業の報告スケジュールに依存
- XBRLタグの企業間差異
- 一部フィールドは利用不可の場合あり

## 8. 受入基準

### 8.1 日次抽出ツール
- 指定日の有価証券報告書を正常取得
- 利用可能な財務メトリクスを全て抽出
- 適切にフォーマットされたJSON出力

### 8.2 統合ツール
- 入力ディレクトリの全JSONファイルを処理
- 重複企業の適切な処理
- データ整合性の維持

### 8.3 システム全体
- 両ツールがエラーなく実行
- 生成JSONファイルの妥当性
- 財務データの精度要件を満たす