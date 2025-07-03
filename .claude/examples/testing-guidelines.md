# Testing Strategy

## テスト戦略

### 現在のテスト状況
- 明示的なテストスイートは未実装
- 動作確認は手動実行とログ確認に依存

### 推奨テスト戦略

#### 単体テスト
- lib/モジュールの個別機能をテスト
- テストフレームワーク: pytest推奨
- モック: unittest.mockを使用

#### 統合テスト
- EDINET APIとの連携テスト
- XBRLパース処理の確認
- エンドツーエンドのデータフロー検証

#### E2Eテスト
- 実際のAPIを使用した全体フローテスト
- 日次実行スクリプトの動作確認
- データ統合処理の検証

### テストの命名規則
```python
# テストファイル名
test_<module_name>.py

# テスト関数名
def test_<function_name>_<scenario>():
    """何をテストするかを明確に記述"""
    pass

# 例
def test_fetch_document_list_success():
    """正常なAPI応答でドキュメントリストを取得できることを確認"""
    pass

def test_fetch_document_list_api_error():
    """APIエラー時に適切に処理されることを確認"""
    pass
```

### モックの使い方
```python
from unittest.mock import patch, MagicMock

@patch('requests.get')
def test_api_call(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_get.return_value = mock_response
    
    # テスト実行
    result = fetch_document_list("dummy_key", "2025-06-28")
    assert result == []
```

### カバレッジの目標値
- 目標: コアロジックの80%以上
- 重点領域:
  - XBRL解析ロジック
  - データ変換処理
  - エラーハンドリング

### テストデータの管理方法
```
tests/
├── fixtures/
│   ├── sample_xbrl.xml      # サンプルXBRLデータ
│   ├── api_responses.json   # APIレスポンスのモック
│   └── expected_output.json # 期待される出力
└── test_*.py               # テストファイル
```

### 将来の実装推奨事項
1. pytestの導入
2. CI/CDでのテスト自動実行
3. テストカバレッジレポートの生成
4. パフォーマンステストの追加

## Development Testing

### Running Tests

When you have an API key available, test the tools:

#### Test fetch_edinet_financial_documents
```bash
# Test with a recent date
python bin/fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY --verbose

# Test with different retry settings
python bin/fetch_edinet_financial_documents.py --date 2025-06-10 --outputdir data/jsons --api-key YOUR_API_KEY --max-retries 5 --verbose
```

#### Test consolidate_documents
```bash
# Test consolidation with generated data
python bin/consolidate_documents.py --inputdir data/jsons/ --output data/edinet.json --summary --verbose

# Test with minimal output
python bin/consolidate_documents.py --inputdir data/jsons/ --output data/edinet_minimal.json
```

### Manual Testing Checklist

#### Pre-execution Checks
- [ ] Valid EDINET API key available
- [ ] Output directory exists and is writable
- [ ] Internet connection is stable
- [ ] Sufficient disk space for output

#### Execution Verification
- [ ] Script starts without import errors
- [ ] API connection established successfully
- [ ] Progress indicators show activity
- [ ] Log file created in expected location

#### Output Validation
- [ ] JSON file created with expected structure
- [ ] Data fields contain appropriate types
- [ ] Securities codes are 4 digits
- [ ] Period end dates in correct format
- [ ] Numeric fields are numbers or null

#### Error Handling Tests
- [ ] Script continues after individual document failures
- [ ] Network errors trigger retry mechanism
- [ ] Invalid API key produces clear error message
- [ ] Missing output directory is created automatically

### Performance Testing

#### Baseline Metrics
- Single document processing: < 5 seconds
- Daily batch (100 documents): < 15 minutes
- Consolidation (30 daily files): < 1 minute

#### Load Testing
```bash
# Test with a high-volume day
python bin/fetch_edinet_financial_documents.py --date 2025-03-31 --outputdir data/jsons --api-key YOUR_API_KEY

# Monitor memory usage
# Use system tools (top, htop, Activity Monitor) during execution
```

### Integration Testing

#### End-to-End Workflow
1. Fetch data for multiple consecutive days
2. Verify each daily file is created correctly
3. Run consolidation on all daily files
4. Verify consolidated output contains all companies
5. Check for data consistency across days

#### API Integration Tests
- Test with invalid API key
- Test with future dates (no data)
- Test with weekends/holidays
- Test network interruption recovery