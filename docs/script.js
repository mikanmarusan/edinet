// 定数定義
const SCROLL_THRESHOLD = 300;  // トップへ戻るボタンの表示閾値（ピクセル）
const MILLION = 1000000;       // 百万円単位への変換
const DEBOUNCE_DELAY = 300;    // 検索デバウンス遅延（ミリ秒）

let allData = [];
let searchTimeout = null;      // デバウンス用タイマー
let currentSort = { column: null, direction: 'asc' };  // ソート状態管理

// ページ読み込み時の処理
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    setupSearchEvents();
    setupBackToTopButton();
    setupExportButton();
    setupSortableHeaders();
});

// データの読み込み
async function loadData() {
    try {
        // GitHub Pages用とローカル用で切り替え
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const dataUrl = isLocal 
            ? '../data/edinet.json'  // ローカル: 元のパス
            : 'data.json';  // GitHub Pages: docs内のdata.json
        
        console.log('Loading data from:', dataUrl);
        const response = await fetch(dataUrl);
        if (!response.ok) {
            throw new Error('データの読み込みに失敗しました');
        }
        allData = await response.json();
        displayData(allData);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('table-container').style.display = 'block';
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('loading').textContent = 'データの読み込みに失敗しました。';
    }
}

// データの表示
function displayData(data) {
    const tbody = document.getElementById('data-tbody');
    tbody.innerHTML = '';
    
    data.forEach(item => {
        const row = document.createElement('tr');
        row.id = `row-${item.secCode}`;
        
        row.innerHTML = `
            <td class="sec-code fixed-column">${item.yahooURL ? `<a href="${encodeURI(item.yahooURL)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.secCode)}</a>` : escapeHtml(item.secCode) || '-'}</td>
            <td class="company-name fixed-column">${item.docPdfURL ? `<a href="${encodeURI(item.docPdfURL)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.filerName)}</a>` : escapeHtml(item.filerName) || '-'}</td>
            <td>${escapeHtml(item.periodEnd) || '-'}</td>
            <td class="number-cell">${formatStockPrice(item.stockPrice)}</td>
            <td class="number-cell">${formatNumber(item.netSales)}</td>
            <td class="number-cell">${formatEmployees(item.employees)}</td>
            <td class="number-cell">${formatNumber(item.operatingIncome)}</td>
            <td class="number-cell">${formatPercentage(item.operatingIncomeRate)}</td>
            <td class="number-cell">${formatNumber(item.ebitda)}</td>
            <td class="number-cell">${formatPercentage(item.ebitdaMargin)}</td>
            <td class="number-cell">${formatNumber(item.marketCapitalization)}</td>
            <td class="number-cell">${formatRatio(item.per)}</td>
            <td class="number-cell">${formatNumber(item.ev)}</td>
            <td class="number-cell">${formatRatio(item.evPerEbitda)}</td>
            <td class="number-cell">${formatRatio(item.pbr)}</td>
            <td class="number-cell">${formatNumber(item.equity)}</td>
            <td class="number-cell">${formatNumber(item.debt)}</td>
            <td>${escapeHtml(item.retrievedDate) || '-'}</td>
        `;
        
        tbody.appendChild(row);
    });
}

// 数値を百万円単位でフォーマット
function formatNumber(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    const millionValue = Math.round(value / MILLION);
    return millionValue.toLocaleString('ja-JP');
}

// パーセンテージをフォーマット（小数点1桁）
function formatPercentage(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    return value.toFixed(1);
}

// 倍率をフォーマット（小数点1桁）
function formatRatio(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    return value.toFixed(1);
}

// 株価をフォーマット（整数、円単位）
function formatStockPrice(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    return Math.round(value).toLocaleString('ja-JP');
}

// 従業員数をフォーマット（整数、千単位区切り）
function formatEmployees(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    return value.toLocaleString('ja-JP');
}

// テキストを指定文字数で切り詰め
function truncateText(text, maxLength) {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// HTMLエスケープ
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// デバウンス関数
function debounce(func, delay) {
    return function (...args) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => func.apply(this, args), delay);
    };
}

// 検索機能のセットアップ
function setupSearchEvents() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    
    // デバウンス付きの検索関数
    const debouncedSearch = debounce(performSearch, DEBOUNCE_DELAY);
    
    // 検索ボタンクリック時（即座に実行）
    searchButton.addEventListener('click', () => {
        clearTimeout(searchTimeout);
        performSearch();
    });
    
    // Enterキーでも検索実行（即座に実行）
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            clearTimeout(searchTimeout);
            performSearch();
        }
    });
    
    // 入力時はデバウンス付きで実行
    searchInput.addEventListener('input', debouncedSearch);
}

// 検索実行
function performSearch() {
    const searchValue = document.getElementById('search-input').value.trim();
    
    if (!searchValue) {
        alert('証券コードを入力してください');
        return;
    }
    
    // 前回のハイライトを削除
    const previousHighlight = document.querySelector('.highlight');
    if (previousHighlight) {
        previousHighlight.classList.remove('highlight');
    }
    
    // 部分一致検索
    const matchedItems = allData.filter(item => 
        item.secCode && item.secCode.includes(searchValue)
    );
    
    if (matchedItems.length === 0) {
        alert(`証券コード「${searchValue}」にマッチする企業が見つかりませんでした`);
        return;
    }
    
    // 最初にマッチした項目にスクロール
    const firstMatch = matchedItems[0];
    const targetRow = document.getElementById(`row-${firstMatch.secCode}`);
    
    if (targetRow) {
        // ハイライト追加
        targetRow.classList.add('highlight');
        
        // スクロール（ヘッダーの高さを考慮）
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // 複数マッチした場合は通知
    if (matchedItems.length > 1) {
        console.log(`${matchedItems.length}件の企業がマッチしました`);
    }
}

// トップへ戻るボタンの設定
function setupBackToTopButton() {
    const backToTopButton = document.getElementById('back-to-top');
    const tableContainer = document.getElementById('table-container');
    
    if (!backToTopButton || !tableContainer) {
        return;
    }
    
    // テーブルコンテナのスクロールを監視
    tableContainer.addEventListener('scroll', () => {
        if (tableContainer.scrollTop > SCROLL_THRESHOLD) {
            backToTopButton.classList.add('visible');
        } else {
            backToTopButton.classList.remove('visible');
        }
    });
    
    // クリック時のスクロール処理
    backToTopButton.addEventListener('click', () => {
        tableContainer.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// エクスポートボタンの設定
function setupExportButton() {
    const exportButton = document.getElementById('export-button');
    if (!exportButton) return;
    
    exportButton.addEventListener('click', exportToExcel);
}

// ソート機能のセットアップ
function setupSortableHeaders() {
    const sortableHeaders = document.querySelectorAll('.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const sortColumn = header.dataset.sort;
            handleSort(sortColumn);
        });
    });
}

// ソート処理
function handleSort(column) {
    // 同じ列をクリックした場合は方向を変更
    if (currentSort.column === column) {
        if (currentSort.direction === 'asc') {
            currentSort.direction = 'desc';
        } else if (currentSort.direction === 'desc') {
            // デフォルト（証券コード昇順）にリセット
            currentSort.column = 'secCode';
            currentSort.direction = 'asc';
        }
    } else {
        // 新しい列をクリックした場合は昇順から開始
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    
    // データをソート
    const sortedData = sortData(allData, currentSort.column, currentSort.direction);
    
    // 表示を更新
    displayData(sortedData);
    
    // ソート状態を視覚的に更新
    updateSortIndicators();
}

// データのソート
function sortData(data, column, direction) {
    return [...data].sort((a, b) => {
        let aValue = a[column];
        let bValue = b[column];
        
        // null値は最後にソート
        if (aValue === null || aValue === undefined) {
            return 1;
        }
        if (bValue === null || bValue === undefined) {
            return -1;
        }
        
        // 数値の場合
        if (typeof aValue === 'number' && typeof bValue === 'number') {
            return direction === 'asc' ? aValue - bValue : bValue - aValue;
        }
        
        // 文字列の場合
        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();
        
        if (direction === 'asc') {
            return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
        } else {
            return aStr > bStr ? -1 : aStr < bStr ? 1 : 0;
        }
    });
}

// ソート状態の視覚的更新
function updateSortIndicators() {
    // 全てのソート表示をクリア
    document.querySelectorAll('.sortable').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc', 'sort-active');
    });
    
    // 現在のソート列にインジケータを追加
    if (currentSort.column) {
        const activeHeader = document.querySelector(`[data-sort="${currentSort.column}"]`);
        if (activeHeader) {
            activeHeader.classList.add('sort-active');
            activeHeader.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    }
}

// Excelエクスポート機能
function exportToExcel() {
    if (!allData || allData.length === 0) {
        alert('エクスポートするデータがありません');
        return;
    }
    
    // エクスポート用データの準備
    const exportData = allData.map(item => ({
        '証券コード': item.secCode || '',
        '企業名称': item.filerName || '',
        '有価証券報告書URL': item.docPdfURL || '',
        'Yahoo!ファイナンスURL': item.yahooURL || '',
        '決算期': item.periodEnd || '',
        '決算期末株価(円)': item.stockPrice || '',
        '売上高(百万円)': item.netSales ? Math.round(item.netSales / MILLION) : '',
        '期末従業員数(人)': item.employees || '',
        '営業利益(百万円)': item.operatingIncome ? Math.round(item.operatingIncome / MILLION) : '',
        '営業利益率(%)': item.operatingIncomeRate || '',
        'EBITDA(百万円)': item.ebitda ? Math.round(item.ebitda / MILLION) : '',
        'EBITDAマージン(%)': item.ebitdaMargin || '',
        '時価総額(百万円)': item.marketCapitalization ? Math.round(item.marketCapitalization / MILLION) : '',
        'PER(倍)': item.per || '',
        '企業価値(百万円)': item.ev ? Math.round(item.ev / MILLION) : '',
        'EV/EBITDA(倍)': item.evPerEbitda || '',
        'PBR(倍)': item.pbr || '',
        '純資産合計(百万円)': item.equity ? Math.round(item.equity / MILLION) : '',
        'ネット有利子負債(百万円)': item.debt ? Math.round(item.debt / MILLION) : '',
        '最終更新日': item.retrievedDate || ''
    }));
    
    // ワークシート作成
    const ws = XLSX.utils.json_to_sheet(exportData);
    
    // カラム幅の設定
    ws['!cols'] = [
        {wch: 10},  // 証券コード
        {wch: 30},  // 企業名称
        {wch: 50},  // 有価証券報告書URL
        {wch: 40},  // Yahoo!ファイナンスURL
        {wch: 12},  // 決算期
        {wch: 15},  // 決算期末株価
        {wch: 15},  // 売上高
        {wch: 15},  // 期末従業員数
        {wch: 15},  // 営業利益
        {wch: 12},  // 営業利益率
        {wch: 15},  // EBITDA
        {wch: 15},  // EBITDAマージン
        {wch: 15},  // 時価総額
        {wch: 10},  // PER
        {wch: 15},  // 企業価値
        {wch: 12},  // EV/EBITDA
        {wch: 10},  // PBR
        {wch: 15},  // 純資産合計
        {wch: 20},  // ネット有利子負債
        {wch: 12}   // 最終更新日
    ];
    
    // ワークブック作成
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "財務データ");
    
    // ファイル名生成（現在日付）
    const today = new Date();
    const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
    const fileName = `edinet_data_${dateStr}.xlsx`;
    
    // ダウンロード実行
    XLSX.writeFile(wb, fileName);
}