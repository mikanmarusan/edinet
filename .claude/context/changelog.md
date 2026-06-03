# EDINET プロジェクト変更履歴・学習事項

## 概要
このファイルはEDINETプロジェクトにおける重要な修正履歴、学習事項、技術的な知見を記録します。

## 重要な修正履歴

### 市場時価総額計算の修正
- **問題**: 自己株式数のみを使用して市場時価総額を計算していた
- **原因**: EDINETのXBRLパターンの理解不足により、誤ったデータ要素を抽出
- **解決**: 正しいEDINETパターン `NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc` を最優先に設定
- **重要な学習**: 
  - 市場時価総額 = 株価 × 発行済株式総数（自己株式を含む）
  - EDINETタクソノミーの正確な理解が必要
  - 存在しないパターン名を使用しないこと

### 非連結財務諸表の条件付き処理
- **問題**: 連結財務諸表を持たない企業のデータが取得できない
- **原因**: NonConsolidatedMemberコンテキストのデータを一律除外していた
- **解決**: 連結財務諸表が存在しない場合のみ非連結データを使用
- **実装仕様**:
  - `_has_consolidated_data`メソッドで連結データの有無を判定
  - 連結データがある場合：従来通り連結データを優先（NonConsolidatedMember除外）
  - 連結データがない場合：NonConsolidatedMemberデータを使用
  - 過去データは除外（CurrentYearコンテキストのみ使用）
- **対象メソッド**: 
  - `extract_numeric_value_with_context`および全動的検索メソッド

### 連結・個別データの優先順位改善（2025年7月）
- **問題**: 連結財務諸表を持つ企業でも個別（提出会社）データを取得してしまうバグ
- **原因**: コンテキスト優先度の判定ロジックが不十分
- **解決**: 
  - BusinessResultsOfGroupコンテキストを最優先に設定（+50〜80ポイント）
  - ReportingCompanyコンテキストにペナルティ付与（-30ポイント）
  - 連結データ検出ロジックの強化
- **学習ポイント**:
  - XBRLのコンテキスト構造を正確に理解することが重要
  - BusinessResultsOfGroup = 連結データの最も確実な指標
  - ReportingCompany = 個別データの指標
  - 優先度スコアリングによる柔軟な判定が有効

### issuedDateフィールドの追加（2025年7月）
- **概要**: 有価証券報告書の提出日をJSONに記録
- **フィールド仕様**:
  - フィールド名: `issuedDate`
  - データ型: 文字列
  - フォーマット: `YYYY-MM-DD`（ISO 8601形式）
  - データソース: `--date`パラメータ（コマンドライン引数）
  - JSON内位置: `cash`の後、`retrievedDate`の前
- **実装詳細**:
  - `XBRLParser.parse_financial_data()`に`issued_date`パラメータ追加
  - `XBRLParser._build_financial_data_structure()`に`issued_date`パラメータ追加
  - `fetch_edinet_financial_documents.py`から`args.date`を渡す
- **目的**: 
  - 有価証券報告書の提出日を記録し、時系列分析を可能にする
  - `retrievedDate`（データ取得日）と区別して実際の報告書提出日を保持

### Yahoo Finance統合の実装（2025年7月）
- **概要**: EDINETデータをYahoo Financeのリアルタイム市場データで補完
- **新規ライブラリ**:
  - `lib/ticker_generator.py`: 証券コードからYahooティッカーシンボルへの変換
  - `lib/url_generator.py`: Yahoo Finance URLの生成
  - `lib/data_scraper.py`: Playwrightを使用したWebスクレイピング
- **技術的変更**:
  - Headless Browser (Playwright) を使用したデータ取得
  - EDINETデータ取得後にYahoo Financeから補完データを取得
  - 失敗時はEDINETデータのみで処理を継続（フェイルセーフ）
- **データソース詳細**:
  - **Yahoo Financeから取得**: characteristic, stockPrice, netSales, employees, operatingIncome, ordinaryIncome（新規）, depreciation, bps, debt, outstandingShares, netIncome, eps
  - **EDINETから取得**: equity, cash（財務諸表の正式な値が必要なため）
  - **計算値**: operatingIncomeRate, ordinaryIncomeRate（新規）, ebitda, ebitdaMargin, marketCapitalization, per, ev, evPerEbitda, pbr
- **注意事項**:
  - レート制限未実装（Issue #91）
  - ブラウザインスタンスの最適化が必要（Issue #92）
  - デバッグprint文の削除が必要（Issue #90）

## 技術的学習事項

### XBRLタクソノミーの理解
- EDINETのXBRL構造は企業によって異なるため、動的検索が必要
- コンテキスト（連結/個別、当期/過去）の優先度設定が重要
- 存在しないタグ名を使用しないよう、実際のXBRL構造を確認すること

### Yahoo Finance統合の知見
- Playwrightによるヘッドレスブラウザは安定した データ取得を実現
- finance.yahoo.co.jpの構造は変更される可能性があるため、定期的な確認が必要
- レート制限の実装が今後の課題

### データ品質管理
- 財務データの妥当性検証（負の値、異常な値の処理）
- データソース間での整合性確認
- 欠損データの適切な処理とログ出力

## 最近の改善実装

### Webビューアのモダン化（2025年8月 - Issue #119）
- **概要**: ブラウザのalert()をトースト通知システムに置き換え
- **実装内容**:
  - `ToastNotification`クラスによる非ブロッキング通知システム
  - タイプ別スタイリング（error/warning/info/success）
  - 自動消去機能（デフォルト5秒）とマニュアルクローズ
  - アニメーション付き表示/非表示（slideIn/slideOut）
  - ARIAアトリビュートによるアクセシビリティ対応
  - モバイルレスポンシブ対応
- **置き換え箇所**:
  - 証券コードバリデーションエラー → warning toast
  - 企業が見つからない → info toast
  - 複数マッチ通知 → info toast（3秒表示）
  - エクスポートデータなし → warning toast
  - Excelエクスポート成功 → success toast
- **技術詳細**:
  - CSSアニメーション使用
  - pointer-eventsによる適切なイベント処理
  - z-indexによるレイヤー管理（z-index: 10000）

### 上場廃止企業の検出とWeb UI表示（2026年4月）
- **概要**: JPX公開の「東証上場銘柄一覧」(`data_j.xls`) との差分で上場廃止企業を検出し、`data/edinet.json`と Web ビューアで視覚的に区別する
- **背景**: EDINETは有価証券報告書のみを提供し、上場廃止情報を持たない。有報を提出しなくなった企業は fetcher から消えるが、過去の `data/jsons/*.json` に残ったデータは「ゾンビ」化していた
- **検出ロジック**:
  - `delisted = (observed_secs - regional_skip) - jpx_listed`
  - `observed_secs`: `data/jsons/*.json` で過去に観測された全 secCode
  - `jpx_listed`: JPX `data_j.xls` から抽出した現役の東証上場 secCode
  - `regional_skip`: `config/stock_exchange_mapping.yml` 登録コード（地方取引所単独上場銘柄のため JPX データに含まれず、判定対象から**除外**する）
- **新規ファイル**:
  - `lib/delisted_detector.py` - 差分計算ロジック
  - `bin/update_delisted_companies.py` - JPX 取得・YAML 更新（Fail-safe エスカレーション付き）
  - `data/delisted_companies.yml` - 上場廃止企業の永続化 YAML
  - `tests/test_delisted_detector.py`, `tests/test_consolidate_delisted.py`
- **変更ファイル**:
  - `bin/consolidate_documents.py` - `--delisted` 引数で yml を読み、各 company に `isDelisted` / `delistedDate` フィールドを付与
  - `docs/script.js` / `docs/styles.css` / `docs/index.html` - `.delisted-row` クラスと `廃止` バッジ、Excel エクスポート列追加
  - `.github/workflows/edinet-fetcher.yml` - fetch と consolidate の間に update ステップ挿入、`concurrency` グループ追加
  - `pyproject.toml` / `requirements.txt` - `xlrd==1.2.0` を明示的にピン（xlrd 2.x 以降は `.xls` 非対応）
- **重要な技術判断**:
  - **pandas 経由ではなく xlrd を直接呼ぶ**: pandas 2.x は `xlrd>=2.0.1` を要求するが xlrd 2.x は `.xls` 未対応という矛盾のため、`xlrd.open_workbook()` を直接呼ぶ
  - **`stock_exchange_mapping.yml` は判定スキップリスト（exclusion）として使用**: ホワイトリスト扱いはしない（mapping 未登録の地方単独上場銘柄は誤検出される可能性があるが、それは既存の quarterly update 運用問題に還元される）
  - **JPX 取得失敗の段階的エスカレーション**: 1 連続失敗→stderr warning、2 連続→`$GITHUB_STEP_SUMMARY` に警告、3 連続→`exit 1` で step を失敗させる。連続失敗カウンタは `metadata.consecutive_failures` に永続化
- **初期導入時の検出数**: 約 200 件（直近の TOB/MBO による上場廃止が大半。e.g., イオンモール, SCSK, NTTデータグループ, ベネッセHD, ＳＢＩレオスひふみ 等）

## 今後の改善予定

### 技術的改善
1. Yahoo Financeアクセスのレート制限実装
2. ブラウザインスタンスの最適化
3. デバッグprint文の削除
4. エラーハンドリングの強化

### 機能拡張
1. 更多財務指標の抽出
2. 時系列データ分析機能
3. データ品質レポート機能
4. 自動化スケジュール機能

## 関連ドキュメント
- `.claude/context/product-requirements.md` - プロダクト要件詳細
- `.claude/context/architecture.md` - アーキテクチャ設計
- `.claude/rules/debugging-guide.md` - デバッグ手法