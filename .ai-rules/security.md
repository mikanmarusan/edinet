# Security Best Practices

## セキュリティのベストプラクティス

### 機密情報の扱い方

#### APIキーの管理
- **必須**: APIキーはコマンドライン引数として明示的に指定
- **禁止**: ハードコード、デフォルト値の設定
- **推奨**: 環境変数からの読み込み（将来的な実装）

```python
# Good: 明示的なパラメータ要求
parser.add_argument('--api-key', required=True, help='EDINET API key')

# Bad: デフォルト値やハードコード
API_KEY = "xxxxxxxx"  # 絶対にNG
```

#### ログ出力での配慮
- APIキーや個人情報をログに出力しない
- エラーメッセージにも機密情報を含めない

```python
# Bad
logger.error(f"API call failed with key: {api_key}")

# Good
logger.error("API call failed: Authentication error")
```

### 入力値検証のルール

#### コマンドライン引数の検証
```python
def validate_date_format(date_str):
    """日付形式（YYYY-MM-DD）を検証"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_api_key(api_key):
    """APIキーの基本的な形式を検証"""
    if not api_key or len(api_key) < 10:
        raise ValueError("Invalid API key format")
    return api_key
```

#### 外部データの検証
- EDINET APIレスポンスの妥当性確認
- XBRLデータの構造検証
- 不正なデータによる処理停止を防ぐ

### 認証・認可の実装パターン
- 現在はAPIキーベースの認証のみ
- 将来的な拡張に備えた設計

### 依存関係の脆弱性チェック

#### 定期的な更新
```bash
# 脆弱性チェック（推奨）
pip install safety
safety check

# 依存関係の更新
pip install --upgrade -r requirements.txt
```

#### 最小権限の原則
- ファイルアクセスは必要最小限に
- 書き込み権限は出力ディレクトリのみ

### データ保護
- 個人情報を含む可能性のあるデータは慎重に扱う
- 出力ファイルの権限設定に注意

```python
# ファイル作成時の権限指定
import os
import stat

def save_json_secure(data, filepath):
    """セキュアなJSON保存"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 読み取り専用に設定（オプション）
    os.chmod(filepath, stat.S_IRUSR | stat.S_IRGRP)
```

### エラーハンドリングでのセキュリティ
- スタックトレースに機密情報を含めない
- 外部に公開されるエラーメッセージは最小限に

### 将来的な実装推奨事項
1. secrets管理システムの導入
2. API呼び出しのレート制限実装
3. 監査ログの実装
4. データ暗号化の検討