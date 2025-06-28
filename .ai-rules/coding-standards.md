# Coding Standards

## 詳細なコーディング規約

### Python コーディング標準
- **PEP 8準拠**: 基本的にPEP 8に従う
- **Python バージョン**: 3.x系を使用

### インデント、改行、スペースのルール
- インデント: スペース4つ
- 行の最大長: 120文字（PEP 8の79文字より緩和）
- 空行:
  - トップレベル関数・クラス定義の間: 2行
  - メソッド定義の間: 1行
  - ロジックブロックの区切り: 1行

### 関数の長さ、複雑度の上限
- 関数の最大行数: 50行を目安
- 循環的複雑度: 10以下を推奨
- ネストの深さ: 最大4レベル

### コメントの書き方
```python
# 単一行コメント: 処理の意図を説明

def fetch_document_list(api_key, date):
    """
    指定日のEDINET文書リストを取得する。
    
    Args:
        api_key (str): EDINET APIキー
        date (str): 取得対象日（YYYY-MM-DD形式）
        
    Returns:
        list: 文書情報のリスト
    """
    # API制限: 1リクエスト/秒
    time.sleep(1)
```

### エラーハンドリングのパターン

#### 基本パターン
```python
try:
    # 処理実行
    result = process_document(doc)
except SpecificException as e:
    logger.error(f"特定のエラー: {e}")
    # 個別エラーは継続
    continue
except Exception as e:
    logger.error(f"予期しないエラー: {e}")
    # 必要に応じて再スロー
    raise
```

#### フェイルセーフ原則
- 個別文書の処理失敗で全体を停止しない
- エラーはログに記録し、処理を継続
- 重要なエラーは集計して最後に報告

### 命名規則の詳細
- **変数名**: 説明的な名前を使用
  - Good: `document_list`, `api_response`
  - Bad: `dl`, `resp`
- **定数**: モジュールレベルで定義
  - `API_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"`
- **プライベート関数**: アンダースコアで開始
  - `_validate_response(response)`

### インポート規則
```python
# 標準ライブラリ
import os
import sys
import json
from datetime import datetime

# サードパーティライブラリ
import requests
from lxml import etree

# ローカルモジュール
from lib.edinet_common import setup_logging
from lib.xbrl_parser import XBRLParser
```

### データ形式の一貫性
- 日付: ISO 8601形式（YYYY-MM-DD）
- 時刻: タイムゾーン付きISO形式
- 数値: nullまたは数値（文字列化しない）
- 真偽値: true/false（小文字）

### ログ出力規則
```python
# ログレベルの使い分け
logger.debug("詳細なデバッグ情報")
logger.info("正常な処理フロー")
logger.warning("注意が必要だが継続可能")
logger.error("エラーだが処理は継続")
logger.critical("致命的エラー、処理停止")

# 構造化ログ
logger.info(f"処理完了: 成功={success_count}, 失敗={error_count}")
```

## Error Handling

The system includes robust error handling for various scenarios:

### Error Categories

#### Missing Data
- **Behavior**: Skip companies with incomplete data
- **Logging**: Log missing fields with company identifier
- **Example**:
```python
if not company_data.get('secCode'):
    logger.warning(f"Missing secCode for document {doc_id}")
    continue
```

#### API Errors
- **Behavior**: Log errors and continue processing
- **Retry Logic**: Automatic retry with exponential backoff
- **Example**:
```python
try:
    response = requests.get(url, params=params)
    response.raise_for_status()
except requests.RequestException as e:
    logger.error(f"API request failed: {e}")
    # Retry logic applies
```

#### File I/O Errors
- **Behavior**: Display clear error messages
- **Recovery**: Attempt to create directories if missing
- **Example**:
```python
try:
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
except IOError as e:
    logger.error(f"Failed to write file {filepath}: {e}")
```

#### Network Issues
- **Behavior**: Implement retry logic with delays
- **Timeout Handling**: Configurable request timeouts
- **Connection Pooling**: Reuse connections when possible

#### XBRL Parsing Errors
- **Behavior**: Handle malformed or incomplete XBRL data
- **Fallback**: Use dynamic search when standard patterns fail
- **Logging**: Record parsing failures with context

### Error Recovery Strategies

1. **Graceful Degradation**: Continue with partial data rather than failing completely
2. **Error Aggregation**: Collect all errors and report summary at the end
3. **Contextual Logging**: Include document ID, company name, and processing stage
4. **User-Friendly Messages**: Translate technical errors into actionable guidance

## Data Quality

The system ensures data quality through multiple mechanisms:

### Data Validation

#### Input Validation
- **Date Format**: Validate YYYY-MM-DD format before API calls
- **API Key**: Check for presence and basic format
- **File Paths**: Verify directory existence and write permissions

#### Extracted Data Validation
- **Type Checking**: Ensure numeric fields contain numbers or null
- **Range Validation**: Check for reasonable values (e.g., PER between 0-1000)
- **Required Fields**: Verify presence of critical fields (secCode, periodEnd)

### Missing Fields Handling
- **Null Assignment**: Set missing fields to null rather than omitting
- **Graceful Degradation**: Process documents even with partial data
- **Logging**: Record all missing fields for analysis

### Data Consistency
- **Type Consistency**: Ensure consistent data types across all outputs
- **Format Standards**: Apply consistent formatting rules
  - Securities codes: Always 4 digits
  - Period end: Always YYYY年M月期 format
  - Numbers: Never stringify numeric values

### Duplicate Handling
- **Latest Data Precedence**: In consolidation, newer data overwrites older
- **Duplicate Detection**: Use secCode as unique identifier
- **Logging**: Record duplicate occurrences

### Quality Metrics
- **Success Rate Tracking**: Monitor extraction success per field
- **Error Rate Analysis**: Track common failure patterns
- **Completeness Score**: Calculate percentage of successfully extracted fields

### Data Integrity Checks
```python
def validate_financial_data(data):
    """Validate extracted financial data"""
    # Check required fields
    if not data.get('secCode') or not data.get('periodEnd'):
        return False
    
    # Validate numeric fields
    numeric_fields = ['netSales', 'operatingIncome', 'netIncome', 'equity']
    for field in numeric_fields:
        value = data.get(field)
        if value is not None and not isinstance(value, (int, float)):
            return False
    
    # Range validation
    per = data.get('per')
    if per is not None and (per < 0 or per > 1000):
        logger.warning(f"Suspicious PER value: {per}")
    
    return True
```