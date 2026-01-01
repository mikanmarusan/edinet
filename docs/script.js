// ============================================
// PRECISION FINANCE - Japanese Financial Data Viewer
// ============================================

// ---------- Constants ----------
const SCROLL_THRESHOLD = 300;
const MILLION = 1000000;
const ANIMATION_STAGGER_DELAY = 20; // ms between row animations

// JPX証券コード仕様に基づく正規表現
const SEC_CODE_PATTERN = /^(?:[0-9]{4}|[0-9][ACDFGHJKLMNPRSTUXY][0-9]{2}|[0-9]{3}[ACDFGHJKLMNPRSTUXY]|[0-9][ACDFGHJKLMNPRSTUXY][0-9][ACDFGHJKLMNPRSTUXY])$/i;

// ---------- State ----------
let allData = [];
let currentSort = { column: null, direction: 'asc' };

// ---------- Toast Notification System ----------
class ToastNotification {
    constructor() {
        this.container = document.getElementById('toast-container');
    }

    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');

        const icons = {
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
            success: '✓'
        };

        toast.innerHTML = `
            <span class="toast-icon" aria-hidden="true">${icons[type] || icons.info}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
            <button class="toast-close" aria-label="閉じる">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
        `;

        this.container.appendChild(toast);

        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.hide(toast));

        if (duration > 0) {
            setTimeout(() => this.hide(toast), duration);
        }

        return toast;
    }

    hide(toast) {
        if (!toast || toast.classList.contains('hiding')) return;

        toast.classList.add('hiding');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 250);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

let toastNotification;

// ---------- Theme Management ----------
class ThemeManager {
    constructor() {
        this.toggle = document.getElementById('theme-toggle');
        this.init();
    }

    init() {
        // Check for saved preference or system preference
        let savedTheme = null;
        try {
            savedTheme = localStorage.getItem('theme');
        } catch (e) {
            console.warn('localStorage unavailable:', e);
        }
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        if (savedTheme) {
            this.setTheme(savedTheme);
        } else if (systemPrefersDark) {
            this.setTheme('dark');
        } else {
            this.setTheme('light');
        }

        // Listen for toggle clicks
        this.toggle.addEventListener('click', () => this.toggleTheme());

        // Listen for system preference changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            let hasStoredTheme = false;
            try {
                hasStoredTheme = localStorage.getItem('theme') !== null;
            } catch (err) {
                // localStorage unavailable
            }
            if (!hasStoredTheme) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        try {
            localStorage.setItem('theme', theme);
        } catch (e) {
            console.warn('localStorage unavailable:', e);
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }
}

// ---------- Initialization ----------
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize systems
    toastNotification = new ToastNotification();
    new ThemeManager();

    // Load data and setup UI
    await loadData();
    setupSearchEvents();
    setupBackToTopButton();
    setupExportButton();
    setupSortableHeaders();
});

// ---------- Data Loading ----------
async function loadData() {
    try {
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const dataUrl = isLocal ? '../data/edinet.json' : 'data.json';

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
        const loadingEl = document.getElementById('loading');
        loadingEl.textContent = '';
        const container = document.createElement('div');
        container.className = 'loading-container';
        const p = document.createElement('p');
        p.className = 'loading-text';
        p.style.color = 'var(--negative)';
        p.textContent = 'データの読み込みに失敗しました';
        container.appendChild(p);
        loadingEl.appendChild(container);
    }
}

// ---------- Data Display ----------
function displayData(data) {
    const tbody = document.getElementById('data-tbody');
    tbody.innerHTML = '';

    data.forEach((item, index) => {
        const row = document.createElement('tr');
        row.id = `row-${item.secCode}`;

        // Add staggered animation delay
        if (index < 30) {
            row.style.animationDelay = `${index * ANIMATION_STAGGER_DELAY}ms`;
        } else {
            row.style.animationDelay = '300ms';
        }

        row.innerHTML = `
            <td class="sec-code sticky-col sticky-col-1">${item.yahooURL ? `<a href="${encodeURI(item.yahooURL)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.secCode)}</a>` : escapeHtml(item.secCode) || '-'}</td>
            <td class="company-name sticky-col sticky-col-2">${item.docPdfURL ? `<a href="${encodeURI(item.docPdfURL)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.filerName)}</a>` : escapeHtml(item.filerName) || '-'}</td>
            <td>${escapeHtml(item.periodEnd) || '-'}</td>
            <td class="number-cell">${formatStockPrice(item.stockPrice)}</td>
            <td class="number-cell">${formatNumber(item.netSales)}</td>
            <td class="number-cell">${formatEmployees(item.employees)}</td>
            <td class="number-cell ${getValueClass(item.operatingIncome)}">${formatNumber(item.operatingIncome)}</td>
            <td class="number-cell ${getValueClass(item.operatingIncomeRate)}">${formatPercentage(item.operatingIncomeRate)}</td>
            <td class="number-cell ${getValueClass(item.ordinaryIncome)}">${formatNumber(item.ordinaryIncome)}</td>
            <td class="number-cell ${getValueClass(item.ordinaryIncomeRate)}">${formatPercentage(item.ordinaryIncomeRate)}</td>
            <td class="number-cell">${formatNumber(item.ebitda)}</td>
            <td class="number-cell">${formatPercentage(item.ebitdaMargin)}</td>
            <td class="number-cell">${formatNumber(item.marketCapitalization)}</td>
            <td class="number-cell">${formatRatio(item.per)}</td>
            <td class="number-cell">${formatNumber(item.ev)}</td>
            <td class="number-cell">${formatRatio(item.evPerEbitda)}</td>
            <td class="number-cell">${formatRatio(item.pbr)}</td>
            <td class="number-cell">${formatNumber(item.equity)}</td>
            <td class="number-cell">${formatNumber(item.debt)}</td>
            <td>${escapeHtml(item.issuedDate) || '-'}</td>
            <td>${escapeHtml(item.retrievedDate) || '-'}</td>
        `;

        tbody.appendChild(row);
    });
}

// ---------- Formatting Functions ----------
function formatNumber(value) {
    if (value === null || value === undefined) return '-';
    const millionValue = Math.round(value / MILLION);
    return millionValue.toLocaleString('ja-JP');
}

function formatPercentage(value) {
    if (value === null || value === undefined) return '-';
    return value.toFixed(1);
}

function formatRatio(value) {
    if (value === null || value === undefined) return '-';
    return value.toFixed(1);
}

function formatStockPrice(value) {
    if (value === null || value === undefined) return '-';
    return Math.round(value).toLocaleString('ja-JP');
}

function formatEmployees(value) {
    if (value === null || value === undefined) return '-';
    return value.toLocaleString('ja-JP');
}

function getValueClass(value) {
    if (value === null || value === undefined) return '';
    return value < 0 ? 'negative' : '';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ---------- Search Functionality ----------
function validateSecCode(code) {
    if (!code) {
        return { valid: false, message: '証券コードを入力してください' };
    }

    if (!SEC_CODE_PATTERN.test(code)) {
        return {
            valid: false,
            message: '証券コードのフォーマットが正しくありません'
        };
    }

    return { valid: true };
}

function setupSearchEvents() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');

    // Input restriction: alphanumeric only
    searchInput.addEventListener('input', (e) => {
        const originalValue = e.target.value;
        const cleanedValue = originalValue.replace(/[^0-9A-Za-z]/g, '');

        if (originalValue !== cleanedValue) {
            const cursorPosition = Math.min(e.target.selectionStart || 0, cleanedValue.length);
            e.target.value = cleanedValue;
            e.target.setSelectionRange(cursorPosition, cursorPosition);
        }
    });

    searchButton.addEventListener('click', performSearch);

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

function performSearch() {
    const searchValue = document.getElementById('search-input').value.trim().toUpperCase();

    const validation = validateSecCode(searchValue);
    if (!validation.valid) {
        toastNotification.show(validation.message, 'warning');
        return;
    }

    // Remove previous highlight
    const previousHighlight = document.querySelector('.highlight');
    if (previousHighlight) {
        previousHighlight.classList.remove('highlight');
    }

    // Exact match search
    const matchedItems = allData.filter(item =>
        item.secCode && item.secCode.toUpperCase() === searchValue
    );

    if (matchedItems.length === 0) {
        toastNotification.show('該当する企業が見つかりませんでした', 'info');
        return;
    }

    // Scroll to first match
    const firstMatch = matchedItems[0];
    const targetRow = document.getElementById(`row-${firstMatch.secCode}`);

    if (targetRow) {
        targetRow.classList.add('highlight');
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    if (matchedItems.length > 1) {
        toastNotification.show(`${matchedItems.length}件の企業がマッチしました`, 'info', 3000);
    }
}

// ---------- Back to Top Button ----------
function setupBackToTopButton() {
    const backToTopButton = document.getElementById('back-to-top');
    const tableContainer = document.getElementById('table-container');

    if (!backToTopButton || !tableContainer) return;

    tableContainer.addEventListener('scroll', () => {
        if (tableContainer.scrollTop > SCROLL_THRESHOLD) {
            backToTopButton.classList.add('visible');
        } else {
            backToTopButton.classList.remove('visible');
        }
    });

    backToTopButton.addEventListener('click', () => {
        tableContainer.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// ---------- Export Functionality ----------
function setupExportButton() {
    const exportButton = document.getElementById('export-button');
    if (!exportButton) return;

    exportButton.addEventListener('click', exportToExcel);
}

function exportToExcel() {
    if (!allData || allData.length === 0) {
        toastNotification.show('エクスポートするデータがありません', 'warning');
        return;
    }

    const exportData = allData.map(item => ({
        '証券コード': item.secCode || '',
        '企業名称': item.filerName || '',
        '有価証券報告書URL': item.docPdfURL || '',
        'Yahoo!ファイナンスURL': item.yahooURL || '',
        '決算期': item.periodEnd || '',
        '株価(円)': item.stockPrice || '',
        '売上高(百万円)': item.netSales ? Math.round(item.netSales / MILLION) : '',
        '期末従業員数(人)': item.employees || '',
        '営業利益(百万円)': item.operatingIncome ? Math.round(item.operatingIncome / MILLION) : '',
        '営業利益率(%)': item.operatingIncomeRate || '',
        '経常利益(百万円)': item.ordinaryIncome ? Math.round(item.ordinaryIncome / MILLION) : '',
        '経常利益率(%)': item.ordinaryIncomeRate || '',
        'EBITDA(百万円)': item.ebitda ? Math.round(item.ebitda / MILLION) : '',
        'EBITDAマージン(%)': item.ebitdaMargin || '',
        '時価総額(百万円)': item.marketCapitalization ? Math.round(item.marketCapitalization / MILLION) : '',
        'PER(倍)': item.per || '',
        '企業価値(百万円)': item.ev ? Math.round(item.ev / MILLION) : '',
        'EV/EBITDA(倍)': item.evPerEbitda || '',
        'PBR(倍)': item.pbr || '',
        '純資産合計(百万円)': item.equity ? Math.round(item.equity / MILLION) : '',
        'ネット有利子負債(百万円)': item.debt ? Math.round(item.debt / MILLION) : '',
        'EDINET提出日': item.issuedDate || '',
        '最終更新日': item.retrievedDate || ''
    }));

    const ws = XLSX.utils.json_to_sheet(exportData);

    ws['!cols'] = [
        {wch: 10}, {wch: 30}, {wch: 50}, {wch: 40}, {wch: 12},
        {wch: 15}, {wch: 15}, {wch: 15}, {wch: 15}, {wch: 12},
        {wch: 15}, {wch: 12}, {wch: 15}, {wch: 15}, {wch: 15},
        {wch: 10}, {wch: 15}, {wch: 12}, {wch: 10}, {wch: 15},
        {wch: 20}, {wch: 12}, {wch: 12}
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "財務データ");

    const today = new Date();
    const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
    const fileName = `edinet_data_${dateStr}.xlsx`;

    XLSX.writeFile(wb, fileName);

    toastNotification.show(`${fileName} をエクスポートしました`, 'success');
}

// ---------- Sort Functionality ----------
function setupSortableHeaders() {
    const sortableHeaders = document.querySelectorAll('.sortable');

    sortableHeaders.forEach(header => {
        // Add accessibility attributes
        header.setAttribute('tabindex', '0');
        header.setAttribute('role', 'button');
        header.setAttribute('aria-sort', 'none');

        header.addEventListener('click', () => {
            const sortColumn = header.dataset.sort;
            handleSort(sortColumn);
        });

        // Keyboard navigation support
        header.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const sortColumn = header.dataset.sort;
                handleSort(sortColumn);
            }
        });
    });
}

function handleSort(column) {
    if (currentSort.column === column) {
        if (currentSort.direction === 'desc') {
            currentSort.direction = 'asc';
        } else if (currentSort.direction === 'asc') {
            // Reset to default
            currentSort.column = 'secCode';
            currentSort.direction = 'asc';
        }
    } else {
        currentSort.column = column;
        currentSort.direction = 'desc';
    }

    const sortedData = sortData(allData, currentSort.column, currentSort.direction);
    displayData(sortedData);
    updateSortIndicators();
}

function sortData(data, column, direction) {
    return [...data].sort((a, b) => {
        let aValue = a[column];
        let bValue = b[column];

        if (aValue === null || aValue === undefined) return 1;
        if (bValue === null || bValue === undefined) return -1;

        if (typeof aValue === 'number' && typeof bValue === 'number') {
            return direction === 'asc' ? aValue - bValue : bValue - aValue;
        }

        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();

        if (direction === 'asc') {
            return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
        } else {
            return aStr > bStr ? -1 : aStr < bStr ? 1 : 0;
        }
    });
}

function updateSortIndicators() {
    document.querySelectorAll('.sortable').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
        header.setAttribute('aria-sort', 'none');
    });

    if (currentSort.column) {
        const activeHeader = document.querySelector(`[data-sort="${currentSort.column}"]`);
        if (activeHeader) {
            const isAsc = currentSort.direction === 'asc';
            activeHeader.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            activeHeader.setAttribute('aria-sort', isAsc ? 'ascending' : 'descending');
        }
    }
}
