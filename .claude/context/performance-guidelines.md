# Performance Optimization Guidelines

## パフォーマンス最適化の指針

### 現在の制約とボトルネック
- EDINET API: 1リクエスト/秒の制限
- XBRL解析: 大規模ファイルの処理時間
- メモリ使用: 複数企業データの同時処理

### APIコールの最適化

#### レート制限の遵守
```python
import time

# 現在の実装
time.sleep(1)  # 各APIコール後に1秒待機

# 将来的な改善案
class RateLimiter:
    def __init__(self, calls_per_second=1):
        self.calls_per_second = calls_per_second
        self.last_call = 0
    
    def wait_if_needed(self):
        elapsed = time.time() - self.last_call
        if elapsed < 1.0 / self.calls_per_second:
            time.sleep(1.0 / self.calls_per_second - elapsed)
        self.last_call = time.time()
```

#### バッチ処理の効率化
- 失敗した文書のリトライは最後にまとめて実行
- 並列処理の検討（API制限内で）

### XBRL解析の最適化

#### メモリ効率的な解析
```python
# ストリーミング解析の使用
from lxml import etree

def parse_xbrl_streaming(file_path):
    """大規模XBRLファイルの効率的解析"""
    context = etree.iterparse(file_path, events=('start', 'end'))
    context = iter(context)
    event, root = next(context)
    
    for event, elem in context:
        if event == 'end':
            # 要素を処理
            process_element(elem)
            # メモリ解放
            elem.clear()
            root.clear()
```

#### XPath最適化
- 頻繁に使用するXPathはコンパイル済みオブジェクトとして保存
- 名前空間の事前定義

### キャッシュ戦略

#### API応答のキャッシュ
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_document(doc_id):
    """ドキュメントのキャッシュ付き取得"""
    return fetch_document(doc_id)
```

#### 解析結果のキャッシュ
- 同一企業の複数期データは再利用
- メモリとディスクキャッシュの併用

### 非同期処理のパターン
- 現在は同期処理のみ
- 将来的にはasyncioの導入を検討

```python
# 将来的な実装例
import asyncio
import aiohttp

async def fetch_documents_async(doc_ids):
    """非同期での複数ドキュメント取得"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for doc_id in doc_ids:
            task = fetch_single_document(session, doc_id)
            tasks.append(task)
            await asyncio.sleep(1)  # レート制限
        
        return await asyncio.gather(*tasks)
```

### メモリ使用量の考慮事項

#### データ構造の最適化
- 不要なデータは早期に削除
- 大規模リストは generator を使用

```python
# メモリ効率的な実装
def process_documents_generator(documents):
    """ジェネレータを使用したメモリ効率的処理"""
    for doc in documents:
        result = process_single_document(doc)
        yield result
        # docのメモリは自動的に解放される
```

#### プロファイリング推奨
```python
import memory_profiler

@memory_profiler.profile
def memory_intensive_function():
    # メモリ使用量を監視したい処理
    pass
```

### パフォーマンス計測
- 処理時間の記録とログ出力
- ボトルネックの特定と改善

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    """処理時間計測用コンテキストマネージャ"""
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.info(f"{name}: {elapsed:.2f}秒")

# 使用例
with timer("XBRL解析"):
    parse_xbrl_document(doc)
```

### 将来的な最適化案
1. 並列処理の導入（multiprocessing）
2. データベースインデックスの活用
3. CDNを使用したデータ配信
4. 増分更新の実装

## Advanced XBRL Processing

The system implements sophisticated data extraction algorithms for robust financial metrics capture:

### Dynamic Search Capabilities
- **PER Extraction**: When standard XBRL patterns fail, dynamically searches for PER-related tags using keyword matching and priority scoring
- **EPS Extraction**: Advanced detection of diluted/basic EPS with context-aware fallback mechanisms and comprehensive tag pattern matching
- **Outstanding Shares**: Sophisticated share count detection with dynamic search across multiple tag variations and context prioritization
- **Cash Extraction**: Comprehensive cash and cash equivalents detection with period-end prioritization and consolidated data preference
- **BPS Extraction**: Book value per share detection with multiple calculation methods and tag patterns
- **Debt Extraction**: Net interest-bearing debt calculation with dynamic search for debt components

### Context-Aware Processing
- **Current Year Priority**: Automatically prioritizes current fiscal year data over historical data using XBRL context references
- **Consolidated Data Priority**: Systematically excludes NonConsolidatedMember contexts to prioritize consolidated financial data
- **Priority Scoring**: Implements intelligent scoring algorithms to select the most relevant data when multiple candidates exist
- **Range Validation**: Filters unreasonable values (e.g., PER > 1000, shares outside typical ranges) to ensure data quality
- **Period-End Prioritization**: For cash and time-sensitive metrics, prioritize end-of-period data over other temporal contexts

### Multi-Pattern Extraction
- Support for multiple extraction strategies per metric
- Fallback mechanisms when primary patterns fail
- Comprehensive tag pattern libraries for each financial metric

## API Rate Limiting

The system automatically enforces EDINET API rate limits:

### Current Implementation
- Maximum 1 request per second enforced with `time.sleep(1)`
- Applied after each API call to ensure compliance
- No parallel requests to avoid rate limit violations

### Retry Mechanism
- Automatic retry with exponential backoff for failed requests
- Default 3 retries with configurable maximum
- Delays: 1s, 2s, 4s between retries
- Comprehensive error handling for network issues

### Rate Limit Compliance
```python
# Current implementation in lib/edinet_common.py
for doc_info in document_info_list:
    # Process document...
    time.sleep(1)  # Rate limiting
```