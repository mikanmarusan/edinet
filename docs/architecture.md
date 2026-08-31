# Architecture
<!-- spec-synced-through: 32e4bd34d8af5e82006a769315e6fe44da31aadd -->

## Development Architecture

### Modular Structure
The system uses a modular architecture with shared utilities:

- **lib/edinet_common.py**: Core utilities including API configuration, XBRL namespaces, logging setup, and data validation functions
- **lib/xbrl_parser.py**: Specialized XBRL document extraction and financial metrics parsing
- **Main scripts**: Import from lib module for shared functionality

### Key Shared Components
- EDINET API configuration and rate limiting. The base URL (`EDINET_BASE_URL` in `lib/edinet_common.py`) is `https://api.edinet-fsa.go.jp/api/v2`, the host documented in the official EDINET API 仕様書 (Version 2). The former host `disclosure.edinet-fsa.go.jp` must not be used: it redirects API calls to the browsing site's HTML error page and answers HTTP 200 `text/html`, which passes `raise_for_status()` and only fails later at `response.json()`. `validate_edinet_response` (`lib/edinet_common.py`) now rejects that response shape, and any 3xx, at the call site; both `session.get()` calls use `allow_redirects=False` so the `Subscription-Key` is never forwarded to another host and one rate-limit slot never covers several HTTP hops.
- XBRL namespace mappings resolved per document from the filing's declared taxonomy edition (`detect_taxonomy_namespaces`), with the EDINET 2024-11-01 mappings as fallback defaults  
- Common logging and error handling. `setup_logging()` attaches `_SubscriptionKeyRedactingFilter` to the console **and** file handlers — handler-side rather than logger-side, so records propagated up from third-party loggers (notably `urllib3.connectionpool`, which writes the full request target at DEBUG for every request and at WARNING on a header-parse failure) are covered too — and clamps the `urllib3` logger to INFO as defence in depth. The `Subscription-Key` query parameter therefore never reaches a log line.
- Data validation and formatting utilities

### EDINET API Response Validation (2026-08 Update, issue #219)

- **Where it runs**: `bin/fetch_edinet_financial_documents.py` calls `validate_edinet_response()` immediately after `raise_for_status()` in both `get_documents()` and `download_document()`. `EdinetAPIError` derives from `EdinetError(Exception)` and is *not* a `requests.exceptions.RequestException`, so it passes through each method's `except RequestException` clause without being rewrapped into the opaque message this validation exists to replace.
- **Content-type policy differs per endpoint**: the document list passes `expected_content_type="application/json"` (allowlist), because that endpoint's contract is known. The ZIP download passes no expected type and only rejects `text/html` (blocklist): the success-case content type of the download is not established, and allowlisting an unverified value would reject legitimate downloads — the same class of failure this validation fixes.
- **JSON decoding is explicit**: `get_documents()` wraps `response.json()` in its own `except ValueError` and additionally rejects a non-`dict` body. `requests.exceptions.JSONDecodeError` is a `RequestException` subclass (so the outer clause would rewrap it), and a JSON array body would otherwise fail as an `AttributeError` at `data.get()`.
- **The API key never reaches an exception message**: it travels as the `Subscription-Key` query parameter, so every URL is passed through `_redact_subscription_key()` — a structural `urllib.parse` round trip rather than a regex, so parameter order, percent-encoded values, repeated keys and blank-valued parameters all survive — and requests exceptions are reduced by `summarize_request_error()` to `HTTP <status> <reason>` (or the exception class name when the error carries no response), because `str()` of a requests exception embeds the full request URL.
- **Tests**: `tests/test_edinet_response_validation.py` covers redaction variants, both content-type policies, 3xx detection, the JSON-decode and non-object bodies, the handler-side log filter, and the client wiring (including that `allow_redirects=False` is actually passed). HTTP mocking uses stdlib `unittest.mock`; no HTTP-mocking dependency is introduced.

### Module Dependencies
```
bin/fetch_edinet_financial_documents.py
├── lib/edinet_common.py
│   ├── API configuration (API_BASE_URL, RETRY_DELAYS)
│   ├── XBRL namespaces (NAMESPACES)
│   ├── Logging setup (setup_logging)
│   ├── Response validation (validate_edinet_response, summarize_request_error, _redact_subscription_key)
│   └── Utility functions (fetch_document_list, format_date)
├── lib/xbrl_parser.py
│   ├── XBRLParser class
│   ├── extract_financial_metrics()
│   └── Dynamic search algorithms
└── lib/data_scraper.py (PR4 / issue #185 で requests 化)
    ├── get_financial_data() - メインエントリポイント（市場データのみ）
    └── parse_market_data() - SSR HTMLから株価・時価総額を抽出

bin/update_delisted_companies.py
└── lib/delisted_detector.py
    ├── load_jpx_listed_set() - JPX「東証上場銘柄一覧」(data_j.xls) から現存銘柄を取得
    ├── load_observed_secs_from_jsons() - data/jsons/*.json から過去に観測したsecCodeを収集
    ├── load_regional_skip_set() - config/stock_exchange_mapping.yml（地方単独上場銘柄）を除外リストとして読込
    └── compute_delisted() / merge_delisted_yaml() - 上場廃止判定をdata/delisted_companies.ymlへ反映

bin/consolidate_documents.py
├── lib/edinet_common.py
│   ├── Logging setup (setup_logging)
│   └── Utility functions (load_json_file)
└── data/delisted_companies.yml (--delisted、既定 data/delisted_companies.yml)
    └── DataConsolidator._annotate_delisted() が各社に isDelisted / delistedDate を付与
```

### Design Principles

#### Separation of Concerns
- **Presentation Layer**: Command-line scripts in bin/
- **Business Logic**: Core functionality in lib/
- **Data Layer**: JSON file I/O operations

#### Error Handling Strategy
- **Fail-Safe Operation**: Individual document failures don't stop the entire process
- **Batch vs document scope**: fail-safe applies to individual documents, not to the batch-level listing. In `bin/fetch_edinet_financial_documents.py`, an `EdinetAPIError` from `get_documents()` is logged and ends the run with `sys.exit(1)`; an `EdinetAPIError` from `download_document()` is logged at WARNING and only that document is skipped
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

#### Deterministic Tie Resolution (PR6 / issue #187)
- 候補選択は優先度降順に加え、二次キー（タグの local-name）・三次キー（contextRef）でタイブレークする。全13箇所の候補ソートが `key=lambda x: (-priority, local_name, context_ref)` を使う。
- これにより、同点候補がドキュメント/反復順に依存して選ばれることを排除し、Python バージョン間で抽出結果を再現可能にする（候補タプルは一様に `(value, priority, local_name, context_ref)`）。

### Per-Document Taxonomy & XBRL Hardening (2026-06 Update)

#### Per-Document Namespace Resolution
- EDINET taxonomy editions coexist by fiscal period (e.g. 2024-11-01 and 2025-11-01), so a hardcoded namespace map silently returns null for filings on a newer edition.
- `detect_taxonomy_namespaces()` (lib/edinet_common.py) reads the `jpcrp_cor`/`jppfs_cor`/`jpigp_cor`/`jpdei_cor` xmlns URIs actually declared by each document and merges them over the static defaults; it is fail-safe and logs a WARNING when no known taxonomy resolves.
- `parse_financial_data()` assigns the resolved map to the (reused) extractor instance per document. Detected URIs are used only as `findall` dict values, never dereferenced.

#### Equity Concept Selection
- `equity` prioritizes NetAssets (純資産合計) over ShareholdersEquity (株主資本), the NCI-inclusive total net assets (IFRS filers resolve to `EquityIFRS`, the equivalent total).

#### XML Hardening
- The XBRL parse path uses `defusedxml.ElementTree.fromstring` to reject XML entity-expansion ("billion laughs") payloads.

#### テスト・回帰ガード (PR6 / issue #187)
- `tests/fixtures/xbrl/` に合成XBRLフィクスチャ（JGAAP 2024/2025、IFRS、銀行、連結≠個別、同点タイブレーク）を配置。すべて架空企業（entity `E00001` / secCode `9999`）の明示的に偽の数値で、`tests/_xbrl_fixture_utils.py` の `parse_fixture` から読み込む。
- ゴールデン回帰ハーネス `tests/test_golden_regression.py` が抽出結果を `tests/golden/golden_baseline.json` と突き合わせ、`EXPECTED_CHANGES` 許可リスト外の REGRESSION 行が出たら失敗する（`REGEN_GOLDEN=1` で再生成、冪等）。
- IFRS経路は `tests/test_ifrs_extraction.py` で検証（jpigp名前空間の解決、equity=`EquityIFRS`、net_sales=jpcrp IFRS売上サマリ、ordinaryIncome=null）。
- Python 3.11/3.12/3.13 のCIマトリクスは `.github/workflows/tests.yml` として適用済み。push / pull_request のたびに全件（21モジュール・172テスト）実行される。`tests/test_stock_exchange_mapping.py` の3テストは取引所マッピングデータが古く既知失敗のため `--deselect` されている（詳細は `.claude/skills/running-tests/`）。

### 市場データ取得アーキテクチャ（2026-06 更新, PR4 / issue #185）

#### データ取得フロー
1. **EDINET API経由でXBRLドキュメントを取得**
   - 有価証券報告書のメタデータとXBRLファイルをダウンロード
   - APIレート制限: 1リクエスト/秒を遵守

2. **市場データ（株価・時価総額）を取得**
   - 証券コードをYahooティッカーに変換（lib/ticker_generator.py）し、SSRの基本クォートページ `https://finance.yahoo.co.jp/quote/{ticker}` を `requests` + BeautifulSoup で取得
   - 取得対象は stockPrice と marketCapitalization（円）のみ。財務諸表項目はEDINET XBRLが正本
   - Playwright（ヘッドレスブラウザ）は廃止
   - `--no-market-data` を指定するとこの取得自体をスキップでき、stockPrice/marketCapitalizationと派生指標（per/pbr/ev/evPerEbitda）はnullになる。日次CIジョブ（`edinet-fetcher.yml`）はこのフラグを付けて実行しており、公開データセットではデフォルトでこれらのフィールドがnullになる

3. **データの統合と計算**
   - equity と cash は常にXBRLから取得（財務諸表の正式値）
   - marketCap は取得値を優先し、無ければ 発行済株式数×株価 でフォールバック
   - 各種財務指標を計算（PER、PBR、EV/EBITDA等）

#### 技術スタック・取得作法
- **requests + BeautifulSoup**: SSRページのHTMLを plain GET で取得・解析（ヘッドレスブラウザ不要）
- **抽出アンカー**: 値はハッシュ化クラス名に依存せず、日本語ラベル「時価総額」（自身のDataListItemデータ要素にスコープ）とプライスボードの意味的クラス断片にアンカーして抽出。隣接指標・兄弟要素・ツールチップの数値混入を防ぐ
- **ペーシング/リトライ**: 使い回す `Session` 上で 1リクエスト/秒以上（ジッター付き）、403/429 はバックオフ、デフォルトTLS検証を維持
- **フェイルセーフ**: 市場データ取得失敗時は該当フィールドをnullにしWARNINGを出力（企業の行は中断しない）。null件数は実行サマリに集計
- **暫定ブリッジ**: Yahooスクレイピングは ToS 上禁止であり、null許容の暫定手段。将来は公式の市場データソース（J-Quants 等）へ移行予定

#### データソース分割（2026-06 更新, PR2-3 / issue #183-184）

財務諸表項目はEDINET XBRLを正本として無条件に取得する。市場データのみ market fetcher（Yahoo SSR基本クォートページを `requests` で取得）から取得する。

**市場データ（market fetcher）から取得するフィールド**:
- stockPrice（株価）
- marketCapitalization（時価総額）

**EDINET XBRLから取得するフィールド**:
- characteristic（企業特色）
- netSales（売上高）
- employees（従業員数）
- operatingIncome（営業利益）
- ordinaryIncome（経常利益）※IFRS提出会社は経常利益概念がないためnull
- depreciation（減価償却費）
- bps（1株当たり純資産）
- outstandingShares（発行済株式数）
- netIncome（当期純利益）
- eps（1株当たり利益）
- equity（純資産合計）
- debt（ネット有利子負債）
- cash（現金及び現金同等物）

#### 概念の整合（PR3 / issue #184）
- netIncome は親会社株主に帰属する当期純利益（`ProfitLossAttributableToOwnersOfParent`）を優先し、非支配株主持分を含む bare `ProfitLoss` は最後の手段とする。
- debt はネット有利子負債 = 短期借入金 + 1年内返済予定の長期借入金 + 長期借入金 + 社債 + リース債務 − 現金及び現金同等物。
- EV = 時価総額 + ネット有利子負債。debt が既に現金控除済みのため、EVで現金を二重控除しない（現金の控除は debt 側で一度だけ）。

#### ドキュメントリンク（PR5 / issue #186）
- 各レコードは `docPdfURL`（PDF）と `docURL`（EDINET Webビューア: `https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{docID}`）を持つ。`docID` は `^[A-Za-z0-9]+$` で検証し、不正なら両URLとも null（壊れたURLを残さない）。
- Webビューアは決算期の右に非ソートの「報告書」列を追加し、Web（docURL）/ PDF（docPdfURL）リンクを表示する。

#### エラーハンドリング
- 市場データ取得失敗時もXBRL処理を継続
- 失敗したフィールドはnullを設定（捏造しない）
- 財務諸表項目はXBRLの `_extract_*` から取得する。EPSは `_extract_eps` を正本とし、operatingIncome×0.7 の近似は廃止（捏造EPSが自己計算PERを汚染するため）

#### パフォーマンス考慮事項
- 市場データ取得は Playwright を廃止し `requests` の単一GET（企業ごと1リクエスト）。ヘッドレスブラウザ起動コストは解消（PR4 / issue #185）
- レート制限: 使い回す `Session` 上で 1リクエスト/秒以上のペーシング（ジッター付き）と 403/429 バックオフを実装済み