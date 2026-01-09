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

// ---------- Density Management ----------
class DensityManager {
    constructor() {
        this.toggle = document.getElementById('density-toggle');
        this.init();
    }

    init() {
        let savedDensity = null;
        try {
            savedDensity = localStorage.getItem('density');
        } catch (e) {
            console.warn('localStorage unavailable:', e);
        }

        if (savedDensity) {
            this.setDensity(savedDensity);
        } else {
            this.setDensity('comfortable');
        }

        if (this.toggle) {
            this.toggle.addEventListener('click', () => this.toggleDensity());
        }
    }

    setDensity(density) {
        document.documentElement.setAttribute('data-density', density);
        try {
            localStorage.setItem('density', density);
        } catch (e) {
            console.warn('localStorage unavailable:', e);
        }
    }

    toggleDensity() {
        const currentDensity = document.documentElement.getAttribute('data-density');
        const newDensity = currentDensity === 'compact' ? 'comfortable' : 'compact';
        this.setDensity(newDensity);

        // Announce change to screen readers
        const message = newDensity === 'compact' ? 'コンパクト表示に切替' : '標準表示に切替';
        this.announceChange(message);
    }

    announceChange(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('role', 'status');
        announcement.setAttribute('aria-live', 'polite');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        setTimeout(() => announcement.remove(), 1000);
    }
}

// ---------- Column Visibility Management ----------
class ColumnVisibilityManager {
    constructor() {
        this.toggleBtn = document.getElementById('column-toggle');
        this.dropdown = document.getElementById('column-dropdown');
        this.resetBtn = document.getElementById('column-reset');
        this.dropdownList = this.dropdown?.querySelector('.column-dropdown-list');

        // Column definitions with labels
        this.columns = [
            { index: 0, key: 'secCode', label: '証券コード', required: true },
            { index: 1, key: 'filerName', label: '企業名称', required: true },
            { index: 2, key: 'periodEnd', label: '決算期', required: false },
            { index: 3, key: 'stockPrice', label: '株価', required: false },
            { index: 4, key: 'netSales', label: '売上高', required: false },
            { index: 5, key: 'employees', label: '従業員数', required: false },
            { index: 6, key: 'operatingIncome', label: '営業利益', required: false },
            { index: 7, key: 'operatingIncomeRate', label: '営業利益率', required: false },
            { index: 8, key: 'ordinaryIncome', label: '経常利益', required: false },
            { index: 9, key: 'ordinaryIncomeRate', label: '経常利益率', required: false },
            { index: 10, key: 'ebitda', label: 'EBITDA', required: false },
            { index: 11, key: 'ebitdaMargin', label: 'EBITDAマージン', required: false },
            { index: 12, key: 'marketCapitalization', label: '時価総額', required: false },
            { index: 13, key: 'per', label: 'PER', required: false },
            { index: 14, key: 'ev', label: '企業価値', required: false },
            { index: 15, key: 'evPerEbitda', label: 'EV/EBITDA', required: false },
            { index: 16, key: 'pbr', label: 'PBR', required: false },
            { index: 17, key: 'equity', label: '純資産合計', required: false },
            { index: 18, key: 'debt', label: 'ネット有利子負債', required: false },
            { index: 19, key: 'issuedDate', label: 'EDINET提出日', required: false },
            { index: 20, key: 'retrievedDate', label: '最終更新日', required: false }
        ];

        this.visibilityState = {};
        this.init();
    }

    init() {
        // Load saved visibility state
        let savedState = null;
        try {
            const savedJson = localStorage.getItem('columnVisibility');
            if (savedJson) {
                const parsed = JSON.parse(savedJson);
                // Validate that parsed data is a plain object with boolean values
                if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                    savedState = parsed;
                }
            }
        } catch (e) {
            console.warn('localStorage unavailable or invalid:', e);
        }

        // Initialize visibility state
        this.columns.forEach(col => {
            if (savedState && typeof savedState[col.key] === 'boolean') {
                this.visibilityState[col.key] = col.required ? true : savedState[col.key];
            } else {
                this.visibilityState[col.key] = true;
            }
        });

        this.buildDropdownList();
        this.setupEventListeners();
        this.applyVisibility();
    }

    buildDropdownList() {
        if (!this.dropdownList) return;

        this.dropdownList.innerHTML = '';

        this.columns.forEach(col => {
            const item = document.createElement('label');
            item.className = `column-checkbox-item${col.required ? ' disabled' : ''}`;
            item.setAttribute('role', 'menuitemcheckbox');
            item.setAttribute('aria-checked', String(this.visibilityState[col.key]));

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = this.visibilityState[col.key];
            checkbox.disabled = col.required;
            checkbox.dataset.columnKey = col.key;

            const label = document.createElement('span');
            label.textContent = col.label;

            item.appendChild(checkbox);
            item.appendChild(label);
            this.dropdownList.appendChild(item);

            if (!col.required) {
                checkbox.addEventListener('change', (e) => {
                    this.visibilityState[col.key] = e.target.checked;
                    item.setAttribute('aria-checked', String(e.target.checked));
                    this.saveState();
                    this.applyVisibility();
                });
            }
        });
    }

    setupEventListeners() {
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            });
        }

        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', () => {
                this.resetAll();
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.dropdown?.contains(e.target) && !this.toggleBtn?.contains(e.target)) {
                this.closeDropdown();
            }
        });

        // Close dropdown on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.dropdown?.classList.contains('open')) {
                this.closeDropdown();
            }
        });
    }

    toggleDropdown() {
        const isOpen = this.dropdown?.classList.contains('open');
        if (isOpen) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }

    openDropdown() {
        this.dropdown?.classList.add('open');
        this.toggleBtn?.setAttribute('aria-expanded', 'true');
    }

    closeDropdown() {
        this.dropdown?.classList.remove('open');
        this.toggleBtn?.setAttribute('aria-expanded', 'false');
    }

    resetAll() {
        this.columns.forEach(col => {
            this.visibilityState[col.key] = true;
        });

        // Update checkboxes and aria-checked attributes
        const items = this.dropdownList?.querySelectorAll('.column-checkbox-item');
        items?.forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = true;
            }
            item.setAttribute('aria-checked', 'true');
        });

        this.saveState();
        this.applyVisibility();
    }

    saveState() {
        try {
            localStorage.setItem('columnVisibility', JSON.stringify(this.visibilityState));
        } catch (e) {
            console.warn('localStorage unavailable:', e);
        }
    }

    applyVisibility() {
        const table = document.getElementById('data-table');
        if (!table) return;

        this.columns.forEach(col => {
            const isVisible = this.visibilityState[col.key];

            // Apply to header
            const th = table.querySelector(`thead tr th:nth-child(${col.index + 1})`);
            if (th) {
                th.setAttribute('data-hidden', !isVisible);
            }

            // Apply to all body cells
            const tds = table.querySelectorAll(`tbody tr td:nth-child(${col.index + 1})`);
            tds.forEach(td => {
                td.setAttribute('data-hidden', !isVisible);
            });
        });
    }
}

// ---------- Keyboard Shortcuts Management ----------
class KeyboardShortcutsManager {
    constructor(themeManager, densityManager) {
        this.themeManager = themeManager;
        this.densityManager = densityManager;
        this.modal = document.getElementById('shortcuts-modal');
        this.closeBtn = document.getElementById('shortcuts-close');
        this.previousActiveElement = null;
        this.handleModalKeydown = this.handleModalKeydown.bind(this);
        this.init();
    }

    init() {
        this.setupKeyboardListeners();
        this.setupModalListeners();
    }

    handleModalKeydown(e) {
        if (e.key !== 'Tab') return;

        const focusableElements = this.modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    }

    setupKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            // Ignore if user is typing in an input field
            const isTyping = e.target.tagName === 'INPUT' ||
                             e.target.tagName === 'TEXTAREA' ||
                             e.target.isContentEditable;

            // Special handling for Escape - always allow
            if (e.key === 'Escape') {
                // Close modal if open
                if (!this.modal?.hidden) {
                    this.closeModal();
                    return;
                }

                // Blur search input
                const searchInput = document.getElementById('search-input');
                const mobileSearchInput = document.getElementById('mobile-search-input');
                if (document.activeElement === searchInput || document.activeElement === mobileSearchInput) {
                    document.activeElement.blur();
                }
                return;
            }

            // Don't process other shortcuts if typing
            if (isTyping) return;

            // ? - Show shortcuts modal
            if (e.key === '?' && e.shiftKey) {
                e.preventDefault();
                this.toggleModal();
                return;
            }

            // / or Ctrl+K (Cmd+K on macOS) - Focus search
            if (e.key === '/' || ((e.ctrlKey || e.metaKey) && e.key === 'k')) {
                e.preventDefault();
                this.focusSearch();
                return;
            }

            // d - Toggle dark mode
            if (e.key === 'd') {
                e.preventDefault();
                this.themeManager?.toggleTheme();
                return;
            }

            // c - Toggle density
            if (e.key === 'c') {
                e.preventDefault();
                this.densityManager?.toggleDensity();
                return;
            }
        });
    }

    setupModalListeners() {
        // Close button
        this.closeBtn?.addEventListener('click', () => {
            this.closeModal();
        });

        // Click outside modal content to close
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    }

    focusSearch() {
        // Try desktop search first, fall back to mobile
        const searchInput = document.getElementById('search-input');
        const mobileSearchInput = document.getElementById('mobile-search-input');

        // Check if on mobile (using media query)
        const isMobile = window.matchMedia('(max-width: 768px)').matches;

        if (isMobile && mobileSearchInput) {
            mobileSearchInput.focus();
        } else if (searchInput) {
            searchInput.focus();
        }
    }

    toggleModal() {
        if (this.modal?.hidden) {
            this.openModal();
        } else {
            this.closeModal();
        }
    }

    openModal() {
        if (!this.modal) return;
        this.previousActiveElement = document.activeElement;
        this.modal.hidden = false;
        // Add focus trap
        this.modal.addEventListener('keydown', this.handleModalKeydown);
        // Focus close button for accessibility
        setTimeout(() => {
            this.closeBtn?.focus();
        }, 100);
    }

    closeModal() {
        if (!this.modal) return;
        this.modal.hidden = true;
        this.modal.removeEventListener('keydown', this.handleModalKeydown);
        // Restore focus to previous element
        this.previousActiveElement?.focus();
    }
}

// ---------- Initialization ----------
let themeManager;
let densityManager;
let columnVisibilityManager;

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize systems
    toastNotification = new ToastNotification();
    themeManager = new ThemeManager();
    densityManager = new DensityManager();
    columnVisibilityManager = new ColumnVisibilityManager();
    new KeyboardShortcutsManager(themeManager, densityManager);

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

    // Reapply column visibility after data render
    if (columnVisibilityManager) {
        columnVisibilityManager.applyVisibility();
    }
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
    const mobileSearchInput = document.getElementById('mobile-search-input');
    const mobileSearchButton = document.getElementById('mobile-search-button');

    // Helper function for input restriction
    function restrictToAlphanumeric(e) {
        const originalValue = e.target.value;
        const cleanedValue = originalValue.replace(/[^0-9A-Za-z]/g, '');

        if (originalValue !== cleanedValue) {
            const cursorPosition = Math.min(e.target.selectionStart || 0, cleanedValue.length);
            e.target.value = cleanedValue;
            e.target.setSelectionRange(cursorPosition, cursorPosition);
        }
    }

    // Helper function to sync inputs
    function syncSearchInputs(sourceInput, targetInput) {
        if (targetInput) {
            targetInput.value = sourceInput.value;
        }
    }

    // Desktop search setup
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            restrictToAlphanumeric(e);
            syncSearchInputs(searchInput, mobileSearchInput);
        });

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch('desktop');
            }
        });
    }

    if (searchButton) {
        searchButton.addEventListener('click', () => performSearch('desktop'));
    }

    // Mobile search setup
    if (mobileSearchInput) {
        mobileSearchInput.addEventListener('input', (e) => {
            restrictToAlphanumeric(e);
            syncSearchInputs(mobileSearchInput, searchInput);
        });

        mobileSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch('mobile');
            }
        });
    }

    if (mobileSearchButton) {
        mobileSearchButton.addEventListener('click', () => performSearch('mobile'));
    }
}

function performSearch(source = 'desktop') {
    const inputId = source === 'mobile' ? 'mobile-search-input' : 'search-input';
    const searchInput = document.getElementById(inputId);
    const searchValue = searchInput ? searchInput.value.trim().toUpperCase() : '';

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
    const mobileExportButton = document.getElementById('mobile-export-button');

    if (exportButton) {
        exportButton.addEventListener('click', exportToExcel);
    }

    if (mobileExportButton) {
        mobileExportButton.addEventListener('click', exportToExcel);
    }
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
