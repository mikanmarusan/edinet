# Webビューア開発ガイド

## 概要
`/docs`ディレクトリ配下のWebビューアは、`data/edinet.json`の財務データを閲覧・検索するためのツールです。
GitHub Pagesでの公開を前提とし、シンプルな3ファイル構成（HTML/CSS/JS）で実装されています。

## ファイル構成
```
docs/
├── index.html    # メインHTML（構造）
├── styles.css    # スタイルシート
└── script.js     # JavaScript（機能実装）
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