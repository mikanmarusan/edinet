# Webビューア開発ガイド

## 概要
`/docs`ディレクトリ配下のWebビューアは、`data/edinet.json`の財務データを閲覧・検索するためのツールです。
タイトル: **上場企業有価証券報告書 from EDINET**
GitHub Pagesでの公開を前提とし、シンプルな3ファイル構成（HTML/CSS/JS）で実装されています。

## ファイル構成
```
docs/
├── index.html    # メインHTML（構造）
├── styles.css    # スタイルシート
├── script.js     # JavaScript（機能実装）
└── data.json     # 表示用データ（edinet.jsonのコピー）
```

## 実装上の重要ポイント

### 1. ヘッダー固定の実装
**問題**: CSSでの`position: fixed`が効かない場合がある
**解決策**: HTMLにインラインスタイルで直接指定
```html
<header style="position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; z-index: 9999 !important;">
```

### 2. テーブルヘッダーの固定
**アプローチ**: コンテナ内スクロール方式
- `#table-container`に高さ制限: `height: calc(100vh - 150px)`
- `thead`に`position: sticky`と`-webkit-sticky`（Safari対応）
- `top: 0`でコンテナ内の最上部に固定

### 3. データ読み込みのパス問題
**課題**: ローカルテストとGitHub Pagesでパスが異なる
**対応**: 相対パス`../data/edinet.json`を使用
- ローカルテスト時はプロジェクトルートからサーバー起動
- GitHub Pages時は自動的に正しいパスになる

### 4. 大量データの表示
**データ量**: 約4,000件の企業データ
**対策**: 
- 仮想スクロールは実装せず、ブラウザのネイティブ性能に依存
- テーブルコンテナ内でのスクロールで対応

## 表示項目（2025年6月29日更新）

### カラム定義（全18列）
1. **証券コード** (secCode) - 固定列、幅100px
2. **企業名称** (filerName) - 固定列、幅200px
3. **決算期** (periodEnd)
4. **決算期末株価（円）** (stockPrice) - 整数表示
5. **売上高（百万円）** (netSales)
6. **期末従業員数（人）** (employees) - 千単位区切り
7. **営業利益（百万円）** (operatingIncome)
8. **営業利益率（%）** (operatingIncomeRate) - 小数点1桁
9. **EBITDA（百万円）** (ebitda)
10. **EBITDAマージン（%）** (ebitdaMargin) - 小数点1桁
11. **時価総額（百万円）** (marketCapitalization)
12. **PER（倍）** (per) - 小数点1桁
13. **企業価値（百万円）** (ev)
14. **EV/EBITDA（倍）** (evPerEbitda) - 小数点1桁
15. **PBR（倍）** (pbr) - 小数点1桁
16. **純資産合計（百万円）** (equity)
17. **ネット有利子負債（百万円）** (debt)
18. **最終更新日** (retrievedDate)

### 固定列の実装（2025年6月29日追加）
証券コードと企業名称の2列を固定し、残りは横スクロール可能：
- **CSS**: `position: sticky`と`left`プロパティで実装
- **固定列の幅**: 証券コード100px、企業名称200px
- **影効果**: 2列目の右側に`linear-gradient`で視覚的な区切り
- **z-index管理**: ヘッダー固定列は`z-index: 11`、通常固定列は`z-index: 10`

## 機能実装の詳細

### 証券コード検索
```javascript
// 部分一致検索
const matchedItems = allData.filter(item => 
    item.secCode && item.secCode.includes(searchValue)
);
// 該当行へスクロール＋ハイライト
targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
targetRow.classList.add('highlight');
```

### 事業内容のツールチップ
- CSS擬似要素（`::after`）で実装
- `data-full-text`属性に全文を格納
- ホバー時に`content: attr(data-full-text)`で表示

### トップへ戻るボタン
- テーブルコンテナのスクロールを監視
- `tableContainer.scrollTop > 300`で表示切り替え
- `scrollTo()`でスムーズスクロール

### 数値フォーマット関数（2025年6月29日追加）
```javascript
formatNumber(value)        // 百万円単位、千単位区切り
formatPercentage(value)    // パーセント表示、小数点1桁
formatRatio(value)         // 倍率表示、小数点1桁
formatStockPrice(value)    // 株価表示、整数、千単位区切り
formatEmployees(value)     // 従業員数表示、千単位区切り
```

## トラブルシューティング

### ヘッダーが固定されない
1. ブラウザキャッシュをクリア（Cmd+Shift+R）
2. デベロッパーツールで`position`値を確認
3. インラインスタイルの`!important`を確認

### データが読み込まれない
1. コンソールでエラーを確認
2. ファイルパスが正しいか確認
3. CORSエラーの場合はローカルサーバーから実行

### パフォーマンス問題
- 4,000件程度なら問題ないが、それ以上の場合は仮想スクロール検討
- 検索処理は全件フィルタリングのため、件数増加時は最適化が必要

## ローカルテスト手順
```bash
cd /Users/chiaki/Development/github.com/mikanmarusan/edinet
python3 -m http.server 8080
# ブラウザで http://localhost:8080/docs/ にアクセス
```

## GitHub Pages設定
1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: main, Folder: /docs
4. 公開URL: https://[username].github.io/edinet/

## 更新履歴

### 2025年6月29日
- タイトルを「上場企業有価証券報告書 from EDINET」に変更
- 表示カラムを18列に拡張（財務指標・倍率・従業員数等を追加）
- 証券コードと企業名称の2列を固定列として実装
- 数値フォーマット関数を追加（パーセント、倍率、株価等）
- 横スクロール対応により多数の財務指標を一覧表示可能に