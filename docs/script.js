let allData = [];

// ページ読み込み時の処理
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    setupSearchEvents();
    setupBackToTopButton();
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
    const millionValue = Math.round(value / 1000000);
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
        if (tableContainer.scrollTop > 300) {
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