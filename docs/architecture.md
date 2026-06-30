# Architecture
<!-- spec-synced-through: 802f64de4b6e4769d0821841496ba26f9ac98f6a -->

## Development Architecture

### Modular Structure
The system uses a modular architecture with shared utilities:

- **lib/edinet_common.py**: Core utilities including API configuration, XBRL namespaces, logging setup, and data validation functions
- **lib/xbrl_parser.py**: Specialized XBRL document extraction and financial metrics parsing
- **Main scripts**: Import from lib module for shared functionality

### Key Shared Components
- EDINET API configuration and rate limiting
- XBRL namespace mappings resolved per document from the filing's declared taxonomy edition (`detect_taxonomy_namespaces`), with the EDINET 2024-11-01 mappings as fallback defaults  
- Common logging and error handling
- Data validation and formatting utilities

### Module Dependencies
```
bin/fetch_edinet_financial_documents.py
├── lib/edinet_common.py
│   ├── API configuration (API_BASE_URL, RETRY_DELAYS)
│   ├── XBRL namespaces (NAMESPACES)
│   ├── Logging setup (setup_logging)
│   └── Utility functions (fetch_document_list, format_date)
├── lib/xbrl_parser.py
│   ├── XBRLParser class
│   ├── extract_financial_metrics()
│   └── Dynamic search algorithms
└── lib/data_scraper.py (2025-07 追加)
    ├── get_financial_data() - メインエントリポイント
    ├── extract_profile_data() - 企業概要データ取得
    ├── extract_performance_data() - 業績データ取得
    └── extract_financial_data() - 財務データ取得

bin/consolidate_documents.py
└── lib/edinet_common.py
    ├── Logging setup (setup_logging)
    └── Utility functions (load_json_file)
```

### Design Principles

#### Separation of Concerns
- **Presentation Layer**: Command-line scripts in bin/
- **Business Logic**: Core functionality in lib/
- **Data Layer**: JSON file I/O operations

#### Error Handling Strategy
- **Fail-Safe Operation**: Individual document failures don't stop the entire process
- **Comprehensive Logging**: All errors are logged with context
- **Graceful Degradation**: Missing data fields are set to null rather than causing exceptions

#### Performance Considerations
- **Memory Efficiency**: Process documents one at a time to avoid memory issues
- **I/O Optimization**: Batch file operations where possible
- **API Rate Limiting**: Built-in delays to comply with EDINET restrictions

### Extension Points
- **New Data Sources**: Add new parser modules in lib/
- **Additional Metrics**: Extend XBRLParser.extract_financial_metrics()
- **Output Formats**: Add formatters alongside JSON output
- **Storage Backends**: Replace file I/O with database operations

### XBRL Data Extraction Strategy

#### Consolidated vs Non-Consolidated Financial Statements
- **Priority**: Always prefer consolidated financial data when available
- **Fallback**: Use non-consolidated data only when consolidated data doesn't exist
- **Implementation**:
  - `_has_consolidated_data()` method checks for presence of consolidated contexts
  - All extraction methods conditionally include/exclude NonConsolidatedMember
  - Historical data (PriorYear contexts) is always excluded for non-consolidated data
  
#### Context Priority System (2025-07 Update)
- **Highest Priority**: BusinessResultsOfGroup contexts (+50~80 points)
- **High Priority**: ConsolidatedMember contexts (+30~55 points)
- **Standard Priority**: CurrentYear contexts (+15 points)
- **Penalties**: 
  - ReportingCompany contexts: -30 points (individual data)
  - NonConsolidatedMember: -20 points

#### Context Filtering Logic
```python
# Pseudo-code for context filtering
if has_consolidated_data:
    # Traditional behavior - exclude NonConsolidatedMember
    valid_contexts = [c for c in contexts if 'NonConsolidatedMember' not in c]
    # NEW: Also skip ReportingCompany contexts when consolidated data exists
    valid_contexts = [c for c in valid_contexts if 'ReportingCompany' not in c]
else:
    # New behavior - include NonConsolidatedMember for current year only
    valid_contexts = [c for c in contexts if 'CurrentYear' in c]
```

#### Key XBRL Context Patterns
- **BusinessResultsOfGroup**: Most reliable indicator of consolidated data
- **ReportingCompany**: Indicates individual/non-consolidated data
- **ConsolidatedMember**: Explicit consolidated data marker
- **NonConsolidatedMember**: Explicit non-consolidated data marker

#### Affected Methods
- `extract_numeric_value_with_context`: Core extraction method with conditional logic
- `_dynamic_search_*`: All dynamic search methods check consolidated data availability
- Priority calculation methods: `_calculate_*_priority()` for consistent scoring
- Pattern matching maintains backward compatibility for companies with consolidated data

### Per-Document Taxonomy & XBRL Hardening (2026-06 Update)

#### Per-Document Namespace Resolution
- EDINET taxonomy editions coexist by fiscal period (e.g. 2024-11-01 and 2025-11-01), so a hardcoded namespace map silently returns null for filings on a newer edition.
- `detect_taxonomy_namespaces()` (lib/edinet_common.py) reads the `jpcrp_cor`/`jppfs_cor`/`jpigp_cor`/`jpdei_cor` xmlns URIs actually declared by each document and merges them over the static defaults; it is fail-safe and logs a WARNING when no known taxonomy resolves.
- `parse_financial_data()` assigns the resolved map to the (reused) extractor instance per document. Detected URIs are used only as `findall` dict values, never dereferenced.

#### Equity Concept Selection
- `equity` prioritizes NetAssets (純資産合計) over ShareholdersEquity (株主資本); intentional value changes are tracked in the `EXPECTED_EQUITY_CHANGES` allowlist.

#### XML Hardening
- The XBRL parse path uses `defusedxml.ElementTree.fromstring` to reject XML entity-expansion ("billion laughs") payloads.

### Yahoo Finance Integration Architecture (2025-07)

#### データ取得フロー
1. **EDINET API経由でXBRLドキュメントを取得**
   - 有価証券報告書のメタデータとXBRLファイルをダウンロード
   - APIレート制限: 1リクエスト/秒を遵守

2. **Yahoo Financeから補完データを取得**
   - 証券コードをYahooティッカーシンボルに変換（lib/ticker_generator.py）
   - Playwright（ヘッドレスブラウザ）を使用してデータ取得
   - 3つのページから情報収集:
     - `/profile` - 企業概要（特色、従業員数）
     - `/performance` - 業績データ（売上高、利益等）
     - `/finance` - 財務データ（EPS、BPS、負債等）

3. **データの統合と計算**
   - Yahoo Financeデータが利用可能な場合は優先使用
   - equity と cash は常にXBRLから取得（財務諸表の正式値）
   - 各種財務指標を計算（PER、PBR、EV/EBITDA等）

#### 技術スタック
- **Playwright**: ヘッドレスブラウザ自動化フレームワーク
  - 動的JavaScriptコンテンツの取得に対応
  - Chromiumブラウザをバックグラウンドで実行
  - User-Agent設定でアクセス制限を回避

- **データ抽出戦略**:
  - PRELOADED_STATEからJSONデータを優先的に抽出
  - フォールバック: HTMLテーブルからのパーシング
  - ハードコードされたカラムインデックス使用（要改善）

#### データソース分割（2026-06 更新, PR2 / issue #183）

財務諸表項目はEDINET XBRLを正本として無条件に取得する。市場データのみ market fetcher（現状Yahoo、PR4で差し替え予定）から取得する。

**市場データ（market fetcher）から取得するフィールド**:
- stockPrice（株価）
- ordinaryIncome（経常利益）※PR3 (issue #184) でXBRL化予定
- debt（有利子負債）※PR3 (issue #184) でXBRL化予定

**EDINET XBRLから取得するフィールド**:
- characteristic（企業特色）
- netSales（売上高）
- employees（従業員数）
- operatingIncome（営業利益）
- depreciation（減価償却費）
- bps（1株当たり純資産）
- outstandingShares（発行済株式数）
- netIncome（当期純利益）
- eps（1株当たり利益）
- equity（純資産合計）
- cash（現金及び現金同等物）

#### エラーハンドリング
- 市場データ取得失敗時もXBRL処理を継続
- 失敗したフィールドはnullを設定（捏造しない）
- 財務諸表項目はXBRLの `_extract_*` から取得する。EPSは `_extract_eps` を正本とし、operatingIncome×0.7 の近似は廃止（捏造EPSが自己計算PERを汚染するため）

#### パフォーマンス考慮事項
- 現在: 企業ごとに新規ブラウザインスタンスを起動
- 課題: 100社で100回のブラウザ起動（最適化が必要）
- レート制限: Yahoo Financeへのアクセス制限は未実装