# Documentation

## ディレクトリ構造

### 主要なディレクトリとその役割
```
edinet/
├── bin/                    # 実行可能スクリプト
│   ├── fetch_edinet_financial_documents.py  # 日次データ取得
│   └── consolidate_documents.py             # データ統合
├── lib/                    # 共有ライブラリモジュール
│   ├── __init__.py        # パッケージ初期化
│   ├── edinet_common.py   # API設定、共通関数
│   └── xbrl_parser.py     # XBRL解析専用機能
├── data/                  # データディレクトリ
│   ├── jsons/            # 日次JSONファイル (YYYY-MM-DD.json)
│   └── edinet.json       # 統合済み最新データ
├── .ai-rules/            # AI向け詳細ルール
├── .github/workflows/    # GitHub Actions定義
└── requirements.txt      # Python依存関係
```

### ファイルの配置ルール
- 実行可能スクリプト: bin/
- 共有コード: lib/
- 出力データ: data/jsons/
- ログファイル: プロジェクトルート（script_YYYYMMDD.log）

### モジュール間の依存関係
```
bin/fetch_edinet_financial_documents.py
└── lib/edinet_common.py
    └── lib/xbrl_parser.py

bin/consolidate_documents.py
└── lib/edinet_common.py
```

## コード内ドキュメントの書き方
- docstringはGoogle スタイルを使用
- 関数の目的、引数、戻り値を明記
- 複雑なロジックにはインラインコメントを追加

## API ドキュメントの形式
現在は内部ツールのため、詳細なAPIドキュメントは未作成。
将来的にはSphinxやmkdocsの使用を検討。

## README の更新タイミング
- 新機能追加時
- 使用方法の変更時
- 依存関係の更新時

## 変更履歴の記録方法
- GitHubのリリースノートを活用
- 重要な変更はCHANGELOG.mdに記録（将来実装）

## 図表の作成ガイドライン
- アーキテクチャ図: draw.ioやmermaidを使用
- データフロー図: 処理の流れを視覚化
- シーケンス図: API呼び出しの順序を明確化