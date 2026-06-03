---
name: update-stock-exchange-mapping
description: Scrape regional Japanese stock exchanges (Nagoya/Fukuoka/Sapporo) for single-listed stocks and update config/stock_exchange_mapping.yml. Use for quarterly mapping refresh.
allowed-tools:
  - mcp__plugin_playwright_playwright__browser_navigate
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_click
  - mcp__plugin_playwright_playwright__browser_evaluate
  - mcp__plugin_playwright_playwright__browser_close
  - mcp__plugin_playwright_playwright__browser_select_option
  - "Bash(node:*)"
  - "Bash(python3:*)"
  - "Bash(python:*)"
  - "Bash(.venv/bin/python3:*)"
  - Read
  - Edit
  - Write
  - Grep
---

# Update Stock Exchange Mapping

config/stock_exchange_mapping.yml を各取引所の公式サイトからスクレイピングして更新する。
新規上場銘柄のみ追加し、上場廃止銘柄はレポートのみ（自動削除しない）。

## References: Exchange Site Structure

### 札幌 (S) — https://www.sse.or.jp/tandoku
- 単独上場会社の専用ページ。本則市場 + アンビシャス市場 の2セクション（Sapporo PRO Frontier Marketは対象外）
- DOM構造: 各企業は `<dd>` 内の `<a href="listing/companyXXXX">` リンクで表示
- **証券コードはURLから取得**: `a.href.match(/company(\d+[A-Za-z]?)/)` → code
- **企業名は `<img>` の `alt` 属性から取得**: `a.querySelector('img').alt` → name
- 注意: `a.textContent` は空（画像リンクのため）。必ず上記の方法で取得すること
- テキスト付きリンク（67件）はフッター等の全上場企業リストなので除外する。`innerText` が空のリンク（17件）が単独上場企業
- 現在の件数: 17社

### 名古屋 (N) — https://www.nse.or.jp/listing/search/
- 上場会社検索ページ。「単独区分」→「単独」チェックボックスを選択して検索
- 操作手順:
  1. browser_navigate → URL
  2. browser_click → 「単独」のラベルテキストをクリック（チェックボックス本体はlabelに隠れているため、ラベルをクリックする）
  3. browser_select_option → 表示件数を「100」に変更
  4. browser_click → 「検索」ボタン
  5. browser_evaluate → テーブルからコードと企業名を抽出
  6. ページネーションがあれば次ページも同様に処理
- 検索結果テーブル: `<th>銘柄名（コード）</th>` を含むテーブルの `<td>` にデータ
- コード形式: **5桁の末尾0付き**（例: `17380`, `259A0`）で表示される
  - 4桁に変換: 5文字で末尾が `0` なら末尾を除去（`17380` → `1738`, `259A0` → `259A`）
- 銘柄名形式: `銘柄名（コード）` の全角括弧形式（例: `ＮＩＴＴＯＨ（17380）`）
- ETF銘柄（例: MAXIS S&P東海上場投信）が含まれるので除外すること
- JS抽出コード:
```javascript
(() => {
  const tables = document.querySelectorAll('table');
  for (const table of tables) {
    const ths = table.querySelectorAll('th');
    const headers = Array.from(ths).map(th => th.textContent.trim());
    if (headers.some(h => h.includes('銘柄'))) {
      const rows = table.querySelectorAll('tbody tr, tr');
      const results = [];
      for (const row of rows) {
        const tds = row.querySelectorAll('td');
        if (tds.length >= 2) {
          const text = tds[1].textContent.trim();
          const match = text.match(/^(.+?)（([0-9A-Za-z]{4,5})）$/);
          if (match) {
            let code = match[2];
            if (code.length === 5 && code.endsWith('0')) {
              code = code.slice(0, 4);
            }
            const name = match[1];
            // Exclude ETFs
            if (!name.includes('投信') && !name.includes('ETF') && !name.includes('ＭＡＸＩＳ')) {
              results.push({ code, name });
            }
          }
        }
      }
      return results;
    }
  }
  return [];
})()
```
- 現在の件数: 約60社（ETF含む）

### 福岡 (F) — https://www.fse.or.jp/listed/list.php
- 全上場会社一覧（**単独のみではない。東証との重複上場企業も含む**）
- 3セクション: 本則 / Q-Board / Fukuoka PRO Market（PRO Marketは対象外）
- 企業名のみ表示（証券コードは表示されない）
- **証券コードは各企業の詳細ページから取得**:
  - 詳細ページURL: `/listed/detail.php?copid=XXX`（XXXはエンコードされたID）
  - 詳細ページのHTMLは **Shift_JIS** エンコーディング → `TextDecoder('shift_jis')` でデコード必須
  - コードは `<th>コード</th>` の次の `<td>` に4桁で格納
- 単独上場のフィルタリング:
  - 福岡の詳細ページには東証上場の有無を示す明示的フラグがない
  - 方法: 取得した全コードから、既存YAMLのF銘柄セットとの差分で新規候補を特定。新規候補が東証にも上場しているかは、Yahoo Financeの `.T` サフィックスでアクセスできるかで判断するか、または手動確認する
- JS抽出コード（リスト取得 → 一括fetch）:
```javascript
// Step 1: Get all detail page URLs (exclude PRO Market)
const getDetailUrls = () => {
  const links = Array.from(document.querySelectorAll('a[href*="detail.php?copid="]'));
  const h3s = Array.from(document.querySelectorAll('h3'));
  const proH3 = h3s.find(h => h.textContent.includes('Fukuoka PRO Market'));
  return links.filter(a => {
    if (proH3 && !(a.compareDocumentPosition(proH3) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
    const name = a.textContent.trim();
    return !name.includes('ＮＥＸＴ') && !name.includes('投資法人') && !name.includes('上場投信');
  }).map(a => ({ name: a.textContent.trim(), url: a.href }));
};

// Step 2: Fetch each detail page and extract code (Shift_JIS decoding required)
const fetchCodes = async (items) => {
  const decoder = new TextDecoder('shift_jis');
  const results = [];
  for (const item of items) {
    try {
      const resp = await fetch(item.url);
      const buf = await resp.arrayBuffer();
      const html = decoder.decode(buf);
      const codeMatch = html.match(/<th>コード<\/th>[\s\S]*?<td>(\d{3,4}[A-Za-z]?)<\/td>/);
      if (codeMatch) {
        results.push({ code: codeMatch[1], name: item.name });
      }
    } catch(e) { /* skip */ }
  }
  return results;
};
```
- 現在の件数: 本則+Q-Board合計約108社（うち単独上場は約30社）

## Step 1: Read current YAML

Read `config/stock_exchange_mapping.yml` using the Read tool.
既存のコードを取引所ごとに把握する（N, F, S）。

## Step 2: Scrape 札幌 (S)

1. `browser_navigate` → `https://www.sse.or.jp/tandoku`
2. `browser_evaluate` で以下のJSを実行:

```javascript
(() => {
  const links = Array.from(document.querySelectorAll('a[href*="listing/company"]'));
  // Filter to image-only links (empty innerText = single-listed company entries)
  const emptyLinks = links.filter(a => a.innerText.trim().length === 0);
  return emptyLinks.map(a => {
    const img = a.querySelector('img');
    const codeMatch = a.href.match(/company(\d+[A-Za-z]?)/);
    return {
      code: codeMatch ? codeMatch[1] : null,
      name: img ? img.alt : null
    };
  }).filter(item => item.code && item.name);
})()
```

3. 結果を記録: sapporo_codes = [{code, name}, ...]
4. サニティチェック: 8件未満の場合はスクレイピング失敗と判断し、この取引所の更新をスキップ

## Step 3: Scrape 名古屋 (N)

1. `browser_navigate` → `https://www.nse.or.jp/listing/search/`
2. `browser_click` → 「単独」のラベルテキスト（チェックボックス本体ではなくラベルをクリック）
3. `browser_select_option` → 表示件数を「100」に変更
4. `browser_click` → 「検索」ボタン
5. `browser_evaluate` で以下のJSを実行:

```javascript
(() => {
  const tables = document.querySelectorAll('table');
  for (const table of tables) {
    const ths = table.querySelectorAll('th');
    const headers = Array.from(ths).map(th => th.textContent.trim());
    if (headers.some(h => h.includes('銘柄'))) {
      const rows = table.querySelectorAll('tbody tr, tr');
      const results = [];
      for (const row of rows) {
        const tds = row.querySelectorAll('td');
        if (tds.length >= 2) {
          const text = tds[1].textContent.trim();
          const match = text.match(/^(.+?)（([0-9A-Za-z]{4,5})）$/);
          if (match) {
            let code = match[2];
            if (code.length === 5 && code.endsWith('0')) {
              code = code.slice(0, 4);
            }
            const name = match[1];
            if (!name.includes('投信') && !name.includes('ETF') && !name.includes('ＭＡＸＩＳ')) {
              results.push({ code, name });
            }
          }
        }
      }
      return results;
    }
  }
  return [];
})()
```

6. ページネーションがある場合、次のページも同様に処理して全件取得
7. 結果を記録: nagoya_codes = [{code, name}, ...]
8. サニティチェック: 40件未満の場合はスクレイピング失敗と判断し、この取引所の更新をスキップ

## Step 4: Scrape 福岡 (F)

1. `browser_navigate` → `https://www.fse.or.jp/listed/list.php`
2. `browser_evaluate` で本則+Q-Boardの全企業の詳細ページURLを取得（PRO Market除外、ETF/REIT除外）
3. `browser_evaluate` で全詳細ページを一括fetchし、証券コードを抽出:

```javascript
(async () => {
  const links = Array.from(document.querySelectorAll('a[href*="detail.php?copid="]'));
  const h3s = Array.from(document.querySelectorAll('h3'));
  const proH3 = h3s.find(h => h.textContent.includes('Fukuoka PRO Market'));

  const filtered = links.filter(a => {
    if (proH3 && !(a.compareDocumentPosition(proH3) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
    const name = a.textContent.trim();
    return !name.includes('ＮＥＸＴ') && !name.includes('投資法人') && !name.includes('上場投信');
  });

  const decoder = new TextDecoder('shift_jis');
  const results = [];

  for (const a of filtered) {
    try {
      const resp = await fetch(a.href);
      const buf = await resp.arrayBuffer();
      const html = decoder.decode(buf);
      const codeMatch = html.match(/<th>コード<\/th>[\s\S]*?<td>(\d{3,4}[A-Za-z]?)<\/td>/);
      if (codeMatch) {
        results.push({ code: codeMatch[1], name: a.textContent.trim() });
      }
    } catch(e) { /* skip */ }
  }
  return results;
})()
```

4. 取得した全コードリストから、既存YAMLのF銘柄との差分を計算
   - 新規候補 = スクレイピング結果にあり、YAMLにないコード
   - 新規候補が東証にも上場している大企業（武田薬品、ブリヂストン等）でないことを確認
   - Q-Board銘柄は基本的に福岡単独上場
5. 結果を記録: fukuoka_codes = [{code, name}, ...]（単独上場のみ）
6. サニティチェック: 全体の取得件数が50件未満の場合はスクレイピング失敗と判断

NOTE: 福岡は全上場企業が返るため、単独上場のフィルタリングが必要。
既存YAMLのF銘柄 + 新規でQ-Board/本則にのみ上場している企業を追加する。

## Step 5: Close browser

`browser_close` を呼び出す。

## Step 6: Compute diff and display results

各取引所について:
- New codes = scraped codes - existing YAML codes (per exchange)
- Removed codes = existing YAML codes - scraped codes (per exchange)

結果を企業名付きで表示:

```
Stock Exchange Mapping Update — YYYY-MM-DD

札幌 (S):
  Scraped: XX codes
  New:     "XXXX" 企業名A
  Removed: "XXXX" (will NOT be deleted)

名古屋 (N):
  Scraped: XX codes
  New:     (none)
  Removed: (none)

福岡 (F):
  Scraped: XX codes (total), YY codes (single-listed)
  New:     "XXXX" 企業名B
  Removed: (none)
```

## Step 7: Update YAML (additions only)

Read the existing YAML file, add new codes to the appropriate exchange sections.
Use Edit tool to insert new entries in the correct sorted position within each section.

Format rules:
- Comments preserved: `# 名古屋証券取引所 (N)`, `# 福岡証券取引所 (F)`, `# 札幌証券取引所 (S)`
- Double-quoted keys and values: `"XXXX": "N"`
- 2-space indent
- Entries sorted lexicographically within each section
- Blank line between sections

Removed codes are NOT deleted from the YAML — only reported to the user.

## Step 8: Validate

Run the validation script. スクリプトはこのコマンドと同じディレクトリに同梱されている:

```bash
node .claude/skills/update-stock-exchange-mapping/validate-stock-exchange-mapping.js config/stock_exchange_mapping.yml
```

This script checks:
- YAML構文（root key, entry format）
- 証券コード形式（3-4桁 + 英字オプション）
- 取引所コード（N/F/S のみ）
- 重複コードの検出
- セクションコメントの存在
- 各セクション内のソート順
- 各取引所の件数レポート

Exit code 0 = passed, 1 = errors found.

## Step 9: Report final summary

Show complete summary with all additions (code + company name) per exchange.
Include the total count of codes per exchange after the update.

## Error Handling

- If a site times out or returns an error, report it and continue with the remaining exchanges. Do not abort the entire run.
- If browser_evaluate yields no recognizable security codes, warn the user that the page structure may have changed and show the raw snapshot text for inspection.
- Do not guess or invent codes. Only include codes actually observed in the scraped data.
- If any exchange's scraped count falls below the sanity threshold, skip that exchange and report it.
