# web/ — Webビューア

`data/edinet.json` の財務データを閲覧・検索する静的ビューア（タイトル: **上場企業の財務情報**）。
`index.html` / `styles.css` / `script.js` に `robots.txt` と `tests/` を加えた構成で、ビルド工程を持たない。

このファイルは `web/` 配下の作業時のみ読み込まれる。列定義・フォーマッタ・DOM構造は `script.js` を直接読むこと（ここには重複させない）。

## 公開経路

`.github/workflows/deploy-pages.yml` が `web/` の中身をそのまま `_site/` にコピーし、`data/edinet.json` を `data.json` にリネームして **`gh-pages` ブランチ**へ公開する（`force_orphan: true` で履歴肥大を防止）。公開URLは `https://mikanmarusan.net/edinet/`。

- `web/` に **`CNAME` を置いてはならない**（apexドメイン `mikanmarusan.net` はユーザーサイト側が保有しているため衝突する）。
- GitHub Pages の設定は `main:/docs` から `gh-pages` へ切替済み。`docs/` は現在アーキテクチャ文書の置き場であり、公開ソースではない。

## データ読み込みパスの分岐

`script.js` はローカルとPagesでパスを切り替えている：

```javascript
const dataUrl = isLocal ? '../data/edinet.json' : 'data.json';
```

ローカル確認はプロジェクトルートからサーバを起動し、`http://localhost:8080/web/` を開く（`file://` はCORSで失敗する）：

```bash
python3 -m http.server 8080
```

## 実装上の注意点

### 列の追加・削除

列定義は `script.js` のモジュールレベル定数 `COLUMN_DEFINITIONS` に集約されており、`ColumnVisibilityManager` と `web/tests/column_visibility.test.js` の両方がこれを参照する。**列を増減するときは `COLUMN_DEFINITIONS` の登録・`index.html` の `<th>`・行の `<td>` の3者を必ず同数に揃えること。** `applyVisibility` が index → `nth-child` で表示制御するため、ズレると別の列を誤って表示/非表示にする。

列の表示状態は `localStorage` の `columnVisibility` にスキーマ版付きラッパーで保存される。旧形式（素のマップ）が読まれた場合は破棄して既定値に戻し、一度だけ再保存する移行処理が入っている。`localStorage` へのアクセスは常に try/catch で囲むこと（プライベートウィンドウ等で例外を投げる）。

### ヘッダー固定

- ページヘッダーは `header` 要素に通常のCSS `position: fixed` を指定した「フローティングコマンドバー」実装（`web/styles.css` の `Header - Floating Command Bar` ブロック）。インラインスタイルや `!important` の回避策は使っていない。高さはCSS変数 `--header-height`（既定 `72px`、モバイルは `64px`）で管理する。
- テーブルヘッダーはコンテナ内スクロール方式。`#table-container` に `max-height: calc(100vh - var(--header-height) - 48px)`（`web/styles.css:410`）、`thead` に `position: sticky` / `-webkit-sticky`（Safari対応）を指定している。

### ソート・書き出し・上場廃止表示

- ソート可能な列は `data-sort` 属性を持つ8列のみ（`th.sortable`）。報告書列は `data-sort` を持たず、ソート対象外。
- Excelエクスポートは SheetJS（CDN読み込み）経由の `exportToExcel()` が担う。書き出される列は26列で、画面表示の22列（`COLUMN_DEFINITIONS`）とは別の列セット。
- 上場廃止銘柄は行に `.delisted-row` クラス、企業名セルに `.badge-delisted`（「廃止」バッジ）が付き、`title` 属性に `delistedDate` を表示する。

### テーマ・密度切替

ヘッダーの `#theme-toggle`（ライト/ダーク）と `#density-toggle`（表示密度）はいずれも `localStorage`（キー: `theme` / `density`）にユーザー選択を保存する。`ColumnVisibilityManager` 同様、`localStorage` アクセスは try/catch で囲むこと。

### 固定列

証券コードと企業名称の2列を `position: sticky` + `left` で固定し、残りは横スクロールする。2列目の右側に `linear-gradient` で区切りの影を出す。z-index はヘッダー固定列が `11`、通常の固定列が `10`。

### 通知

`alert()` は使わない。`ToastNotification` クラス経由で非ブロッキング通知を出す：

```javascript
toastNotification.show(message, type, duration); // type: 'error' | 'warning' | 'info' | 'success'
```

### データ量

約4,000件を仮想スクロールなしで描画している。件数が大きく増える場合は仮想スクロールの検討が必要。検索は全件フィルタリングのため同様。

## テスト

```bash
node --test web/tests/
```

**このスイートはCIに接続されていない。** `web/` を変更したら手動で実行すること。新しい `*.test.js` を追加したときは `web/tests/index.js` に `require` を追記する（Nodeの `--test` はディレクトリを再帰探索しない）。
