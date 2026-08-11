# Testing Strategy

## 現在のテスト状況

**pytestベースの自動テストスイートは実装済みで、CIで自動実行されている。**

- **Pythonテスト**: `tests/` 配下に20テストモジュール・140テストが存在する（unittestで記述し、pytestで収集・実行する）
- **CI**: `.github/workflows/tests.yml` が push / pull_request のたびに Python 3.11 / 3.12 / 3.13 のマトリクスで実行する（140件中3件は既知の理由で deselect。後述）
- **回帰ガード**: ゴールデン回帰ハーネス `tests/test_golden_regression.py` が、説明のつかない REGRESSION 行を1件でも検出したらCIを失敗させる
- **既知のギャップ**: `web/tests/` の node:test スイート（`node --test web/tests/`）は存在するが**CIに接続されていない**。Webビューア（`web/`）を変更したときは手動で実行すること
- **既知の除外**: `tests/test_stock_exchange_mapping.py` の3テストがCIで deselect されている（後述）

補助的に、実APIキーを使った手動スモークテストの手順を「Manual Smoke Testing」節に残している。これは自動スイートの代替ではなく、EDINET API / Yahoo への実接続を確認するための手順である。

## テストの実行方法

### Pythonスイート
```bash
# 全件実行（uv 経由。推奨）
uv run python -m pytest tests/ -v

# 全件実行（venv / 素のpython）
python -m pytest tests/ -v

# 特定モジュールのみ
python -m pytest tests/test_golden_regression.py -v

# カバレッジ付き
uv run python -m pytest tests/ -v --cov=lib --cov-report=term-missing
```

### CIと同じ条件で実行する
CIは既知の失敗3件を deselect している。同じ条件を手元で再現するには:
```bash
python -m pytest tests/ -v \
  --deselect tests/test_stock_exchange_mapping.py::TestStockExchangeMapping::test_fukuoka_stock_exchange \
  --deselect tests/test_stock_exchange_mapping.py::TestStockExchangeMapping::test_nagoya_stock_exchange \
  --deselect tests/test_stock_exchange_mapping.py::TestStockExchangeMapping::test_sapporo_stock_exchange
```

### Webビューアのスイート（CI未接続）
```bash
node --test web/tests/
```
新しい `*.test.js` を追加したときは `web/tests/index.js` に `require` を追記すること（Nodeの `--test` はディレクトリを再帰探索しないため、index経由で登録する）。

## テストの追加方法

### 命名規則
```python
# テストファイル名
test_<module_name>.py

# テスト関数名
def test_<function_name>_<scenario>():
    """何をテストするかを明確に記述"""
    pass
```

### 既存の書き方に合わせる
- テストは `unittest.TestCase` のサブクラスで書き、pytestで収集する（既存20モジュールがこの形式）
- モックは `unittest.mock`（`patch` / `MagicMock`）を使う
- 外部I/O（EDINET API、Yahoo）はテスト内で絶対に発生させない。必ずフィクスチャかモックで代替する

### XBRL抽出のテストを追加する
XBRL抽出ロジックを触るテストは、フィクスチャを直接パースするのではなく `tests/_xbrl_fixture_utils.py` のヘルパを使う:
```python
from _xbrl_fixture_utils import parse_fixture

def test_something():
    result = parse_fixture('consolidated_jgaap_2024.xbrl')
    assert result['netSales'] == ...
```
`parse_fixture` はフィクスチャを EDINET の PublicDoc ZIP レイアウトに包んでパーサに渡し、決定的な合成市場データ（`SYNTHETIC_YAHOO`）を注入する。これによりPER/PBR/EVもオフラインで再現可能になる。

### 新しいフィクスチャを追加する
- `tests/fixtures/xbrl/` に置き、`tests/_xbrl_fixture_utils.py` の `FIXTURES` に登録する
- 値はすべて**架空企業の明らかに偽の丸い数値**にする（entity `E00001` / secCode `9999`）。実企業の報告値は使わない
- 登録したらゴールデンベースラインを再生成する（次節）

### モックの例
```python
from unittest.mock import patch, MagicMock

@patch('requests.get')
def test_api_call(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_get.return_value = mock_response

    result = fetch_document_list("dummy_key", "2025-06-28")
    assert result == []
```

## ゴールデンベースラインの再生成

`tests/golden/golden_baseline.json` は `tests/fixtures/xbrl/` の各フィクスチャから抽出した追跡フィールド（`netSales`, `operatingIncome`, `ordinaryIncome`, `netIncome`, `equity`, `cash`, `debt`, `eps`, `bps`, `per`, `pbr`, `outstandingShares`, `ev`, `marketCapitalization`, `stockPrice`）のスナップショットである。

ハーネスは各フィールドについて `match` / `fix` / `REGRESSION` のいずれかの verdict を出す。`REGRESSION`（＝ベースラインと異なり、かつ許可リストにない）が1件でもあればCIが落ちる。

**抽出ロジックを意図的に変更したときの手順**:

1. `tests/test_golden_regression.py` の `EXPECTED_CHANGES` に `(フィクスチャ名, フィールド名) -> 新しい値` を追加する。これで該当行の verdict が `REGRESSION` から `fix` に変わり、レビュアーが差分の意図を読み取れる
2. 変更がレビューで受け入れられたら、ベースラインを再生成する:
   ```bash
   REGEN_GOLDEN=1 python -m pytest tests/test_golden_regression.py
   ```
   この再生成は冪等である
3. 再生成後、`EXPECTED_CHANGES` の該当エントリを削除する（ベースライン自体が新しい値になったため）

**`golden_baseline.json` を手で編集してはならない。** 必ず `REGEN_GOLDEN=1` で再生成する。フィクスチャを追加した場合も同様に再生成が必要で、しなければ「golden baseline に存在しない」旨のアサーションで失敗する。

## CIで deselect されている3テスト

`.github/workflows/tests.yml` は以下の3テストを `--deselect` している:

- `tests/test_stock_exchange_mapping.py::TestStockExchangeMapping::test_fukuoka_stock_exchange`
- `tests/test_stock_exchange_mapping.py::TestStockExchangeMapping::test_nagoya_stock_exchange`
- `tests/test_stock_exchange_mapping.py::TestStockExchangeMapping::test_sapporo_stock_exchange`

**理由**: `config/stock_exchange_mapping.yml` の地方取引所マッピングデータが古く、これら3テストは既知の失敗状態にある。テストコード側の欠陥ではなくデータの陳腐化が原因であり、マッピングを更新するまで失敗し続ける。CI全体を赤にしたままにせず、既知失敗として明示的に除外している。

**解消手順**: `.claude/rules/stock-exchange-mapping-update.md` の手順（または `update-stock-exchange-mapping` スキル）でマッピングを更新し、3テストが通ることを確認したうえで `.github/workflows/tests.yml` の `--deselect` 行を削除する。

## テストデータの構成

```
tests/
├── README.md                     # テスト実行方法のクイックリファレンス
├── _xbrl_fixture_utils.py        # FIXTURES / GOLDEN_FIELDS / parse_fixture
├── fixtures/
│   ├── xbrl/                     # 合成XBRLフィクスチャ（すべて架空企業）
│   │   ├── README.md
│   │   ├── consolidated_jgaap_2024.xbrl      # JGAAP・2024-11-01タクソノミ
│   │   ├── consolidated_jgaap_2025.xbrl      # JGAAP・2025-11-01タクソノミ
│   │   ├── ifrs_2024.xbrl                    # IFRS（jpigp名前空間）
│   │   ├── bank_2024.xbrl                    # 銀行業スキーマ
│   │   ├── consolidated_vs_parent_2024.xbrl  # 連結≠個別のコンテキスト分岐
│   │   └── tie_break_2024.xbrl               # 同点候補の決定的タイブレーク
│   ├── yahoo_quote_sample.html   # Yahooクォートページ（正常系）
│   ├── yahoo_quote_drift.html    # Yahooクォートページ（DOM変化）
│   └── yahoo_quote_empty.html    # Yahooクォートページ（値なし）
├── golden/
│   └── golden_baseline.json      # ゴールデン回帰ベースライン（自動生成）
└── test_*.py                     # 20テストモジュール
```

## カバレッジの目標値
- 目標: コアロジックの80%以上
- 重点領域:
  - XBRL解析ロジック
  - データ変換処理
  - エラーハンドリング

## 今後の改善候補
1. `web/tests/` の node:test スイートをCIに接続する（現在は手動実行のみ）
2. `config/stock_exchange_mapping.yml` を更新し、deselect されている3テストを復帰させる
3. テストカバレッジレポートのCI出力・可視化
4. パフォーマンステストの追加

---

## Manual Smoke Testing

自動スイートとは別に、実APIキーを使ってCLIツールのエンドツーエンド動作を確認する手順。自動テストの代替ではない。

### Running the Tools

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
