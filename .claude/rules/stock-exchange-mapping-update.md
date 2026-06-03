# Stock Exchange Mapping Update Guide

## 概要

`config/stock_exchange_mapping.yml`は、地方取引所に**単独上場**している企業の証券コードと取引所コードのマッピングを管理するファイルです。このガイドでは、ファイルの形式、データソース、更新手順、およびメンテナンス方法について説明します。

## 1. ファイル形式のリファレンス

### 基本構造

```yaml
stock_exchanges:
  # 名古屋証券取引所 (N)
  "1738": "N"
  "1777": "N"

  # 福岡証券取引所 (F)
  "1771": "F"
  "1999": "F"

  # 札幌証券取引所 (S)
  "1449": "S"
  "1832": "S"
```

### フォーマット規則

- **形式**: YAML (key-value pairs)
- **証券コード**:
  - 4桁の数値文字列（引用符で囲む）
  - 例: `"1738"`, `"2467"`, `"9942"`
  - 注意: 4桁未満の場合は先頭ゼロ詰めなし（例: "123"ではなく`"123A"`のような形式になる場合もあります）
- **取引所コード**:
  - `"N"`: 名古屋証券取引所 (Nagoya Stock Exchange)
  - `"F"`: 福岡証券取引所 (Fukuoka Stock Exchange)
  - `"S"`: 札幌証券取引所 (Sapporo Stock Exchange)

### 重要な制約

**単独上場のみ**: このファイルには、地方取引所に**単独で上場**している企業のみを含めてください。東京証券取引所（東証）との重複上場や、複数の地方取引所に上場している企業は**除外**してください。

### セクション構成

- 取引所ごとにコメント行で区切る
- コメントには日本語の取引所名と英略称を記載
- 各セクション内では証券コード順にソート（推奨）

## 2. データソース

### 公式データソースの使用

**必ず公式の取引所ウェブサイトを使用してください。** 非公式のデータソースや推測に基づく情報は使用しないでください。

### 各取引所の単独上場企業リスト

#### 名古屋証券取引所（NSE）
- **URL**: [名古屋証券取引所 上場会社検索](https://www.nse.or.jp/listing/search/)
- **取引所コード**: `"N"`
- **説明**: 検索ページで「単独区分」→「単独」チェックボックスを選択して検索すると、名古屋証券取引所のみに上場している企業が表示される
- **旧URL**: `https://www.nse.or.jp/listing/single/` は404（2026-03-28確認）

#### 福岡証券取引所（FSE）
- **URL**: [福岡証券取引所 上場会社一覧](https://www.fse.or.jp/listed/list.php)
- **取引所コード**: `"F"`
- **説明**: 全上場会社一覧（単独のみではない）。各企業の詳細ページで証券コードと上場区分を確認する必要あり
- **旧URL**: `https://www.fse.or.jp/listing/single/` は404（2026-03-28確認）

#### 札幌証券取引所（SSE）
- **URL**: [札幌証券取引所 単独上場会社](https://www.sse.or.jp/tandoku)
- **取引所コード**: `"S"`
- **説明**: 札幌証券取引所のみに上場している企業のリスト。証券コードと企業名が直接表示される
- **旧URL**: `https://www.sse.or.jp/listing/single/` は404（2026-03-28確認）

### データ取得時の注意事項

1. **公式ソースの確認**: 各取引所の公式ウェブサイトからデータを取得してください
2. **最新性の確認**: データ取得時の日付を記録しておくことを推奨します
3. **単独上場の確認**: 「単独上場」ページから取得したデータのみを使用してください

## 3. 更新手順

### ステップ1: データ収集

1. 各取引所の公式ウェブサイトにアクセスし、単独上場銘柄リストを確認します
2. 証券コードと企業名のペアをリストアップします
3. データ収集日を記録します

### ステップ2: データ検証

各証券コードについて以下を確認してください：

1. **証券コードの形式**:
   - 4桁の数値であることを確認
   - 先頭ゼロがある場合は保持（例: "0123"）
2. **単独上場の確認**:
   - 東証や他の地方取引所に重複上場していないことを確認
   - 公式の「単独上場」リストに記載されていることを確認
3. **重複チェック**:
   - 同じ証券コードが複数の取引所に存在しないことを確認

### ステップ3: YAMLファイルの編集

1. **ファイルを開く**: `config/stock_exchange_mapping.yml`
2. **バックアップ作成**: 編集前に必ずバックアップを作成してください
3. **エントリの追加/更新**:
   ```yaml
   # 新規エントリの追加例
   "1234": "N"  # 企業名（任意のコメント）
   ```
4. **エントリの削除**: 単独上場でなくなった企業のエントリを削除
5. **ソート**: 各セクション内で証券コード順にソート（推奨）

### ステップ4: フォーマット検証

1. **YAML構文チェック**:
   ```bash
   # Python環境でYAMLの構文を検証
   python -c "import yaml; yaml.safe_load(open('config/stock_exchange_mapping.yml'))"
   ```
2. **インデントの確認**: スペース2つでインデントされていることを確認
3. **引用符の確認**: 証券コードと取引所コードが引用符で囲まれていることを確認

### ステップ5: テスト実行

変更後、関連するスクリプトが正常に動作することを確認してください：

```bash
# YAMLファイルが正しく読み込まれることを確認
python -c "
import yaml
with open('config/stock_exchange_mapping.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
    print(f'Total mappings: {len(data[\"stock_exchanges\"])}')
    print(f'Nagoya (N): {sum(1 for v in data[\"stock_exchanges\"].values() if v == \"N\")}')
    print(f'Fukuoka (F): {sum(1 for v in data[\"stock_exchanges\"].values() if v == \"F\")}')
    print(f'Sapporo (S): {sum(1 for v in data[\"stock_exchanges\"].values() if v == \"S\")}')
"
```

### ステップ6: コミットとドキュメント化

1. **変更内容の記録**:
   ```bash
   git add config/stock_exchange_mapping.yml
   git commit -m "update: stock exchange mapping for [取引所名] (YYYY-MM-DD)"
   ```
2. **変更ログの作成**: 更新内容（追加/削除された証券コード）を記録

## 4. メンテナンスガイドライン

### 更新頻度

- **定期更新**: 四半期ごと（3ヶ月に1回）の更新を推奨
- **臨時更新**: 以下の場合は即座に更新を検討してください：
  - 新規上場のニュースがあった場合
  - 上場廃止のニュースがあった場合
  - 東証への市場変更のニュースがあった場合

### データ精度の検証方法

#### 1. 自動検証スクリプトの実施

```python
# 簡易検証スクリプト例
import yaml
import re

def validate_stock_exchange_mapping(filepath):
    """stock_exchange_mapping.ymlの基本的な検証を行う"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    errors = []
    stock_exchanges = data.get('stock_exchanges', {})

    # 証券コードの形式チェック
    for code, exchange in stock_exchanges.items():
        # 4桁の数値または数値+Aの形式をチェック
        if not re.match(r'^\d{4}[A]?$', code):
            errors.append(f"Invalid code format: {code}")

        # 取引所コードのチェック
        if exchange not in ['N', 'F', 'S']:
            errors.append(f"Invalid exchange code: {exchange} for {code}")

    # 重複チェック
    if len(stock_exchanges) != len(set(stock_exchanges.keys())):
        errors.append("Duplicate security codes found")

    return errors

# 実行例
errors = validate_stock_exchange_mapping('config/stock_exchange_mapping.yml')
if errors:
    print("Validation errors found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Validation passed!")
```

#### 2. 公式データとの照合

- 各取引所の公式リストと定期的に照合する
- 差分がある場合は原因を調査し、必要に応じて修正する

#### 3. 統計情報の確認

```bash
# 各取引所のエントリ数を確認
python -c "
import yaml
with open('config/stock_exchange_mapping.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
    exchanges = data['stock_exchanges']
    print(f'Total: {len(exchanges)}')
    for exchange in ['N', 'F', 'S']:
        count = sum(1 for v in exchanges.values() if v == exchange)
        print(f'{exchange}: {count}')
"
```

### テスト手順

#### 統合テストの実施

更新後は、以下のスクリプトが正常に動作することを確認してください：

1. **ticker_generator.py**: ティッカーシンボル生成が正しく動作するか
2. **url_generator.py**: Yahoo Finance URLが正しく生成されるか
3. **data_scraper.py**: スクレイピング処理が正常に動作するか

```bash
# テスト例（実際のテストケースに応じて調整）
python -m pytest tests/ -v -k stock_exchange
```

#### 手動テスト

1. **サンプル証券コードでの確認**:
   ```bash
   # 追加した証券コードでティッカー生成をテスト
   python -c "
   from lib.ticker_generator import generate_ticker
   import yaml

   with open('config/stock_exchange_mapping.yml', 'r', encoding='utf-8') as f:
       data = yaml.safe_load(f)

   # 各取引所から1つずつサンプルを取得してテスト
   for code, exchange in list(data['stock_exchanges'].items())[:3]:
       ticker = generate_ticker(code)
       print(f'{code} ({exchange}) -> {ticker}')
   "
   ```

2. **データ取得の動作確認**: 実際のスクレイピングが正常に動作するか確認

### トラブルシューティング

#### よくある問題

1. **YAML構文エラー**:
   - インデントが正しいか確認（スペース2つ）
   - 引用符が正しく閉じられているか確認
   - 特殊文字のエスケープが必要な場合は対応

2. **証券コードの形式エラー**:
   - 4桁になっているか確認
   - 数値文字列として引用符で囲まれているか確認
   - 先頭ゼロが削除されていないか確認

3. **重複上場企業の混入**:
   - 公式の「単独上場」リストに記載されているか再確認
   - 最新の上場情報を確認

### ベストプラクティス

1. **バージョン管理**: すべての変更をGitで管理し、変更履歴を残す
2. **レビュー**: 重要な更新の際は、2人以上でレビューを実施
3. **ドキュメント**: 大きな変更の際は、変更理由と影響範囲を記録
4. **自動化**: 可能であれば、公式サイトからのデータ取得を自動化することを検討

## 参考情報

### 関連ファイル

- `lib/ticker_generator.py`: このマッピングを使用してティッカーシンボルを生成
- `lib/url_generator.py`: Yahoo Finance URLの生成にこのマッピングを使用
- `lib/data_scraper.py`: スクレイピング処理でこのマッピングを参照

### 関連ドキュメント

- `.claude/rules/coding-standards.md`: コーディング規約
- `.claude/rules/testing-guidelines.md`: テスト戦略
- `docs/context/changelog.md`: 変更履歴

### 外部リンク

- [名古屋証券取引所](https://www.nse.or.jp/)
- [福岡証券取引所](https://www.fse.or.jp/)
- [札幌証券取引所](https://www.sse.or.jp/)
- [YAML仕様](https://yaml.org/spec/)
