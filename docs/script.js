// 定数定義
const SCROLL_THRESHOLD = 300;  // トップへ戻るボタンの表示閾値（ピクセル）
const MILLION = 1000000;       // 百万円単位への変換

let allData = [];

// ページ読み込み時の処理
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    setupSearchEvents();
    setupBackToTopButton();
    setupExportButton();
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

// 検索機能のセットアップ
function setupSearchEvents() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    
    // 検索ボタンクリック時
    searchButton.addEventListener('click', performSearch);
    
    // Enterキーでも検索実行
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
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