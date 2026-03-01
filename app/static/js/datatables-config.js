/**
 * DataTables Configuration
 * Common settings and utilities for DataTables
 */

// Japanese language settings
const japaneseLanguage = {
    "sEmptyTable": "テーブルにデータがありません",
    "sInfo": " _TOTAL_ 件中 _START_ から _END_ まで表示",
    "sInfoEmpty": " 0 件中 0 から 0 まで表示",
    "sInfoFiltered": "（全 _MAX_ 件より抽出）",
    "sInfoPostFix": "",
    "sInfoThousands": ",",
    "sLengthMenu": "_MENU_ 件表示",
    "sLoadingRecords": "読み込み中...",
    "sProcessing": "処理中...",
    "sSearch": "検索:",
    "sZeroRecords": "一致するレコードがありません",
    "oPaginate": {
        "sFirst": "先頭",
        "sLast": "最終",
        "sNext": "次",
        "sPrevious": "前"
    },
    "oAria": {
        "sSortAscending": ": 列を昇順に並べ替えるにはアクティブにする",
        "sSortDescending": ": 列を降順に並べ替えるにはアクティブにする"
    },
    "select": {
        "rows": {
            "_": "%d 行が選択されています",
            "0": "",
            "1": "1 行が選択されています"
        }
    },
    "buttons": {
        "copy": "コピー",
        "copyTitle": "クリップボードにコピー",
        "copySuccess": {
            "_": "%d 行をコピーしました",
            "1": "1 行をコピーしました"
        },
        "print": "印刷"
    }
};

// Default DataTables configuration
const defaultDataTablesConfig = {
    language: japaneseLanguage,
    pageLength: 25,
    lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "全て"]],
    responsive: true,
    autoWidth: false,
    dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
         '<"row"<"col-sm-12"B>>' +
         '<"row"<"col-sm-12"tr>>' +
         '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
    buttons: [
        {
            extend: 'copy',
            text: '<i class="bi bi-clipboard"></i> コピー',
            className: 'btn btn-sm btn-secondary me-1',
            exportOptions: {
                columns: ':visible:not(.no-export)'
            }
        },
        {
            extend: 'csv',
            text: '<i class="bi bi-file-earmark-spreadsheet"></i> CSV',
            className: 'btn btn-sm btn-success me-1',
            exportOptions: {
                columns: ':visible:not(.no-export)'
            }
        },
        {
            extend: 'excel',
            text: '<i class="bi bi-file-earmark-excel"></i> Excel',
            className: 'btn btn-sm btn-success me-1',
            exportOptions: {
                columns: ':visible:not(.no-export)'
            }
        },
        {
            extend: 'pdf',
            text: '<i class="bi bi-file-earmark-pdf"></i> PDF',
            className: 'btn btn-sm btn-danger me-1',
            orientation: 'landscape',
            exportOptions: {
                columns: ':visible:not(.no-export)'
            }
        },
        {
            extend: 'print',
            text: '<i class="bi bi-printer"></i> 印刷',
            className: 'btn btn-sm btn-info',
            exportOptions: {
                columns: ':visible:not(.no-export)'
            }
        }
    ]
};

/**
 * Initialize DataTable with custom config
 */
function initDataTable(tableId, customConfig = {}) {
    const config = {
        ...defaultDataTablesConfig,
        ...customConfig
    };

    return $(tableId).DataTable(config);
}

/**
 * Create DataTable with search builder
 */
function initAdvancedDataTable(tableId, customConfig = {}) {
    const config = {
        ...defaultDataTablesConfig,
        ...customConfig,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"Q>>' +
             '<"row"<"col-sm-12"B>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        searchBuilder: {
            depthLimit: 2
        }
    };

    return $(tableId).DataTable(config);
}

/**
 * Add custom filters to DataTable
 */
function addCustomFilters(table, filters) {
    filters.forEach(filter => {
        $(filter.element).on('change keyup', function() {
            const value = $(this).val();
            table.column(filter.column).search(value).draw();
        });
    });
}

/**
 * Add date range filter
 */
function addDateRangeFilter(table, columnIndex, startDateId, endDateId) {
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        const startDate = $(startDateId).val();
        const endDate = $(endDateId).val();
        const rowDate = data[columnIndex];

        if (!startDate && !endDate) {
            return true;
        }

        const start = startDate ? new Date(startDate) : null;
        const end = endDate ? new Date(endDate) : null;
        const row = rowDate ? new Date(rowDate) : null;

        if (!row) {
            return false;
        }

        if ((start === null || row >= start) && (end === null || row <= end)) {
            return true;
        }

        return false;
    });

    $(startDateId + ',' + endDateId).on('change', function() {
        table.draw();
    });
}

/**
 * Export table data as JSON
 */
function exportAsJSON(tableId, filename = 'data.json') {
    const table = $(tableId).DataTable();
    const data = table.rows().data().toArray();

    const jsonData = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonData], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();

    window.URL.revokeObjectURL(url);
}

/**
 * Add row selection functionality
 */
function enableRowSelection(table, callback) {
    $(table.table().body()).on('click', 'tr', function() {
        $(this).toggleClass('selected');

        const selectedRows = table.rows('.selected').data().toArray();
        if (callback) {
            callback(selectedRows);
        }
    });
}

/**
 * Add bulk actions
 */
function addBulkActions(table, actions) {
    const bulkActionHtml = `
        <div class="bulk-actions mb-3">
            <label>選択した行に対する操作:</label>
            <select class="form-select form-select-sm d-inline-block w-auto ms-2" id="bulk-action-select">
                <option value="">選択してください</option>
                ${actions.map(action => `<option value="${action.value}">${action.label}</option>`).join('')}
            </select>
            <button type="button" class="btn btn-sm btn-primary ms-2" id="bulk-action-btn">実行</button>
        </div>
    `;

    $(table.table().container()).prepend(bulkActionHtml);

    $('#bulk-action-btn').on('click', function() {
        const action = $('#bulk-action-select').val();
        const selectedRows = table.rows('.selected').data().toArray();

        if (!action) {
            alert('操作を選択してください');
            return;
        }

        if (selectedRows.length === 0) {
            alert('行を選択してください');
            return;
        }

        const actionObj = actions.find(a => a.value === action);
        if (actionObj && actionObj.callback) {
            actionObj.callback(selectedRows);
        }
    });
}

/**
 * Save table state to localStorage
 */
function saveTableState(tableId, stateName) {
    const table = $(tableId).DataTable();
    const state = table.state();
    localStorage.setItem(stateName, JSON.stringify(state));
}

/**
 * Load table state from localStorage
 */
function loadTableState(stateName) {
    const stateStr = localStorage.getItem(stateName);
    return stateStr ? JSON.parse(stateStr) : null;
}

/**
 * Clear table filters
 */
function clearFilters(table) {
    table.search('').columns().search('').draw();
}

/**
 * Highlight search results
 */
function highlightSearch(table) {
    table.on('draw', function() {
        const body = $(table.table().body());

        body.unhighlight();

        if (table.search()) {
            body.highlight(table.search());
        }
    });
}

// Initialize jQuery plugin for text highlighting
if (jQuery.fn.highlight === undefined) {
    jQuery.fn.highlight = function(text) {
        return this.each(function() {
            const $this = $(this);
            const html = $this.html();
            const highlighted = html.replace(
                new RegExp('(' + text + ')', 'gi'),
                '<mark>$1</mark>'
            );
            $this.html(highlighted);
        });
    };

    jQuery.fn.unhighlight = function() {
        return this.each(function() {
            const $this = $(this);
            $this.find('mark').contents().unwrap();
        });
    };
}

// Export utilities
window.DataTablesUtils = {
    defaultConfig: defaultDataTablesConfig,
    japaneseLanguage,
    initDataTable,
    initAdvancedDataTable,
    addCustomFilters,
    addDateRangeFilter,
    exportAsJSON,
    enableRowSelection,
    addBulkActions,
    saveTableState,
    loadTableState,
    clearFilters,
    highlightSearch
};
