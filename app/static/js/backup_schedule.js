/**
 * Backup Schedule Management JavaScript
 * Handles schedule creation, editing, and cron expression validation
 */

(function() {
    'use strict';

    // Cron Expression Parser and Validator
    const CronParser = {
        /**
         * Validate cron expression format
         * @param {string} expression - Cron expression (5 fields)
         * @returns {object} - {valid: boolean, message: string}
         */
        validate: function(expression) {
            if (!expression || typeof expression !== 'string') {
                return {valid: false, message: 'Cron式が空です'};
            }

            const parts = expression.trim().split(/\s+/);
            if (parts.length !== 5) {
                return {valid: false, message: 'Cron式は5つのフィールドが必要です (分 時 日 月 曜日)'};
            }

            const [minute, hour, day, month, dayOfWeek] = parts;

            // Validate each field
            const validations = [
                {value: minute, min: 0, max: 59, name: '分'},
                {value: hour, min: 0, max: 23, name: '時'},
                {value: day, min: 1, max: 31, name: '日'},
                {value: month, min: 1, max: 12, name: '月'},
                {value: dayOfWeek, min: 0, max: 7, name: '曜日'}
            ];

            for (let validation of validations) {
                const result = this.validateField(validation.value, validation.min, validation.max);
                if (!result.valid) {
                    return {valid: false, message: `${validation.name}: ${result.message}`};
                }
            }

            return {valid: true, message: 'Cron式は有効です'};
        },

        /**
         * Validate individual cron field
         */
        validateField: function(value, min, max) {
            // Allow wildcard
            if (value === '*') {
                return {valid: true};
            }

            // Allow step values (*/5)
            if (/^\*\/\d+$/.test(value)) {
                const step = parseInt(value.split('/')[1]);
                if (step < 1 || step > max) {
                    return {valid: false, message: `ステップ値が範囲外です (1-${max})`};
                }
                return {valid: true};
            }

            // Allow range (1-5)
            if (/^\d+-\d+$/.test(value)) {
                const [start, end] = value.split('-').map(Number);
                if (start < min || end > max || start >= end) {
                    return {valid: false, message: `範囲が無効です (${min}-${max})`};
                }
                return {valid: true};
            }

            // Allow list (1,3,5)
            if (/^\d+(,\d+)*$/.test(value)) {
                const values = value.split(',').map(Number);
                for (let v of values) {
                    if (v < min || v > max) {
                        return {valid: false, message: `値が範囲外です (${min}-${max})`};
                    }
                }
                return {valid: true};
            }

            // Allow single number
            if (/^\d+$/.test(value)) {
                const num = parseInt(value);
                if (num < min || num > max) {
                    return {valid: false, message: `値が範囲外です (${min}-${max})`};
                }
                return {valid: true};
            }

            return {valid: false, message: '無効な形式です'};
        },

        /**
         * Generate human-readable description
         */
        describe: function(expression) {
            const parts = expression.trim().split(/\s+/);
            if (parts.length !== 5) {
                return 'Invalid cron expression';
            }

            const [minute, hour, day, month, dayOfWeek] = parts;
            let description = '';

            // Time
            if (minute === '*' && hour === '*') {
                description = '毎分';
            } else if (minute !== '*' && hour === '*') {
                description = `毎時${minute}分`;
            } else if (minute !== '*' && hour !== '*') {
                description = `${hour}:${minute.padStart(2, '0')}`;
            }

            // Day
            if (day === '*' && month === '*' && dayOfWeek === '*') {
                description += ' に毎日実行';
            } else if (day !== '*' && month === '*' && dayOfWeek === '*') {
                description += ` に毎月${day}日実行`;
            } else if (dayOfWeek !== '*' && day === '*') {
                const days = this.parseDayOfWeek(dayOfWeek);
                description += ` に${days}実行`;
            } else if (month !== '*') {
                description += ` に${month}月実行`;
            }

            return description;
        },

        parseDayOfWeek: function(value) {
            const dayNames = ['日曜', '月曜', '火曜', '水曜', '木曜', '金曜', '土曜'];

            if (value === '*') return '毎日';
            if (value === '1-5') return '平日';
            if (value === '0,6' || value === '6,0') return '週末';

            if (/^\d$/.test(value)) {
                return dayNames[parseInt(value)];
            }

            if (/^\d+(,\d+)*$/.test(value)) {
                return value.split(',').map(d => dayNames[parseInt(d)]).join('、');
            }

            return value;
        }
    };

    // Schedule Management
    const ScheduleManager = {
        init: function() {
            this.bindEvents();
            this.setupScheduleTypeSelector();
            this.setupCronBuilder();
        },

        bindEvents: function() {
            // Save schedule button
            const saveBtn = document.getElementById('saveScheduleBtn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => this.saveSchedule());
            }

            // Test cron button
            const testBtn = document.getElementById('testCronBtn');
            if (testBtn) {
                testBtn.addEventListener('click', () => this.testCronExpression());
            }

            // Edit schedule buttons
            document.querySelectorAll('.edit-schedule').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const scheduleId = e.currentTarget.dataset.scheduleId;
                    this.loadSchedule(scheduleId);
                });
            });

            // Delete schedule buttons
            document.querySelectorAll('.delete-schedule').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const scheduleId = e.currentTarget.dataset.scheduleId;
                    this.deleteSchedule(scheduleId);
                });
            });

            // Toggle schedule buttons
            document.querySelectorAll('.toggle-schedule').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const scheduleId = e.currentTarget.dataset.scheduleId;
                    const isActive = e.currentTarget.dataset.active === 'True';
                    this.toggleSchedule(scheduleId, !isActive);
                });
            });

            // Test schedule buttons
            document.querySelectorAll('.test-schedule').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const scheduleId = e.currentTarget.dataset.scheduleId;
                    this.testSchedule(scheduleId);
                });
            });
        },

        setupScheduleTypeSelector: function() {
            const typeSelector = document.getElementById('scheduleType');
            const presetOptions = document.getElementById('presetOptions');
            const customOptions = document.getElementById('customOptions');
            const builderOptions = document.getElementById('builderOptions');

            if (!typeSelector) return;

            typeSelector.addEventListener('change', function() {
                // Hide all options
                presetOptions.style.display = 'none';
                customOptions.style.display = 'none';
                builderOptions.style.display = 'none';

                // Show selected option
                switch(this.value) {
                    case 'preset':
                        presetOptions.style.display = 'block';
                        ScheduleManager.updatePreview();
                        break;
                    case 'custom':
                        customOptions.style.display = 'block';
                        break;
                    case 'builder':
                        builderOptions.style.display = 'block';
                        ScheduleManager.updateBuilderPreview();
                        break;
                }
            });

            // Preset change
            const presetSelect = document.getElementById('presetSchedule');
            if (presetSelect) {
                presetSelect.addEventListener('change', () => this.updatePreview());
            }

            // Custom cron input
            const cronInput = document.getElementById('cronExpression');
            if (cronInput) {
                cronInput.addEventListener('input', () => this.validateAndPreview());
            }
        },

        setupCronBuilder: function() {
            const fields = ['cronMinute', 'cronHour', 'cronDay', 'cronMonth', 'cronDayOfWeek'];

            fields.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (field) {
                    field.addEventListener('input', () => this.updateBuilderPreview());
                }
            });
        },

        updatePreview: function() {
            const presetSelect = document.getElementById('presetSchedule');
            if (!presetSelect) return;

            const cronExpression = presetSelect.value;
            this.displayPreview(cronExpression);
        },

        validateAndPreview: function() {
            const cronInput = document.getElementById('cronExpression');
            if (!cronInput) return;

            const expression = cronInput.value.trim();
            const validation = CronParser.validate(expression);

            if (validation.valid) {
                cronInput.classList.remove('is-invalid');
                cronInput.classList.add('is-valid');
                this.displayPreview(expression);
            } else {
                cronInput.classList.remove('is-valid');
                cronInput.classList.add('is-invalid');
                this.displayPreview('', validation.message);
            }
        },

        updateBuilderPreview: function() {
            const minute = document.getElementById('cronMinute').value || '*';
            const hour = document.getElementById('cronHour').value || '*';
            const day = document.getElementById('cronDay').value || '*';
            const month = document.getElementById('cronMonth').value || '*';
            const dayOfWeek = document.getElementById('cronDayOfWeek').value || '*';

            const expression = `${minute} ${hour} ${day} ${month} ${dayOfWeek}`;
            this.displayPreview(expression);
        },

        displayPreview: function(expression, error = null) {
            const previewExpr = document.getElementById('cronPreviewExpression');
            const previewDesc = document.getElementById('cronPreviewDescription');

            if (!previewExpr || !previewDesc) return;

            if (error) {
                previewExpr.textContent = 'エラー';
                previewExpr.className = 'mt-2 text-danger';
                previewDesc.textContent = error;
                previewDesc.className = 'mt-2 text-danger';
            } else {
                previewExpr.textContent = expression;
                previewExpr.className = 'mt-2';
                previewDesc.textContent = CronParser.describe(expression);
                previewDesc.className = 'mt-2 text-muted';
            }
        },

        getCurrentCronExpression: function() {
            const scheduleType = document.getElementById('scheduleType').value;

            switch(scheduleType) {
                case 'preset':
                    return document.getElementById('presetSchedule').value;
                case 'custom':
                    return document.getElementById('cronExpression').value.trim();
                case 'builder':
                    const minute = document.getElementById('cronMinute').value || '*';
                    const hour = document.getElementById('cronHour').value || '*';
                    const day = document.getElementById('cronDay').value || '*';
                    const month = document.getElementById('cronMonth').value || '*';
                    const dayOfWeek = document.getElementById('cronDayOfWeek').value || '*';
                    return `${minute} ${hour} ${day} ${month} ${dayOfWeek}`;
                default:
                    return '';
            }
        },

        testCronExpression: function() {
            const expression = this.getCurrentCronExpression();
            const validation = CronParser.validate(expression);

            if (!validation.valid) {
                this.showAlert('Cron式が無効です: ' + validation.message, 'danger');
                return;
            }

            // Send to server to calculate next run times
            fetch('/api/schedule/test-cron', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cron_expression: expression
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.displayNextRuns(data.next_runs);
                } else {
                    this.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('接続エラーが発生しました', 'danger');
            });
        },

        displayNextRuns: function(nextRuns) {
            const preview = document.getElementById('nextRunPreview');
            const list = document.getElementById('nextRunList');

            if (!preview || !list) return;

            list.innerHTML = '';
            nextRuns.forEach((run, index) => {
                const li = document.createElement('li');
                li.className = 'mb-2';
                li.innerHTML = `
                    <i class="bi bi-calendar-event text-primary"></i>
                    <strong>${index + 1}回目:</strong> ${run}
                `;
                list.appendChild(li);
            });

            preview.style.display = 'block';
        },

        saveSchedule: function() {
            const form = document.getElementById('scheduleForm');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const expression = this.getCurrentCronExpression();
            const validation = CronParser.validate(expression);

            if (!validation.valid) {
                this.showAlert('Cron式が無効です: ' + validation.message, 'danger');
                return;
            }

            const formData = {
                job_id: document.getElementById('jobSelect').value,
                cron_expression: expression,
                priority: document.getElementById('priority').value,
                description: document.getElementById('description').value,
                is_active: document.getElementById('isActive').checked
            };

            fetch('/api/schedule/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showAlert('スケジュールを作成しました', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    this.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('保存中にエラーが発生しました', 'danger');
            });
        },

        loadSchedule: function(scheduleId) {
            fetch(`/api/schedule/${scheduleId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Populate edit modal with data
                    // Implementation depends on edit modal structure
                    console.log('Schedule data:', data.schedule);
                } else {
                    this.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('読み込み中にエラーが発生しました', 'danger');
            });
        },

        deleteSchedule: function(scheduleId) {
            if (!confirm('このスケジュールを削除してもよろしいですか?')) {
                return;
            }

            fetch(`/api/schedule/${scheduleId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showAlert('スケジュールを削除しました', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    this.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('削除中にエラーが発生しました', 'danger');
            });
        },

        toggleSchedule: function(scheduleId, activate) {
            fetch(`/api/schedule/${scheduleId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({is_active: activate})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const action = activate ? '有効化' : '無効化';
                    this.showAlert(`スケジュールを${action}しました`, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    this.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('更新中にエラーが発生しました', 'danger');
            });
        },

        testSchedule: function(scheduleId) {
            if (!confirm('このスケジュールをテスト実行しますか?')) {
                return;
            }

            fetch(`/api/schedule/${scheduleId}/test`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showAlert('テスト実行を開始しました', 'info');
                } else {
                    this.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showAlert('テスト実行中にエラーが発生しました', 'danger');
            });
        },

        showAlert: function(message, type = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            const container = document.querySelector('.container-fluid');
            if (container) {
                container.insertBefore(alertDiv, container.firstChild);
                setTimeout(() => alertDiv.remove(), 5000);
            }
        }
    };

    // Storage Management
    const StorageManager = {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            // Test connection buttons
            document.querySelectorAll('.test-connection').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const storageId = e.currentTarget.dataset.storageId;
                    this.testConnection(storageId);
                });
            });

            // Edit storage buttons
            document.querySelectorAll('.edit-storage').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const storageId = e.currentTarget.dataset.storageId;
                    this.loadStorage(storageId);
                });
            });

            // Delete storage buttons
            document.querySelectorAll('.delete-storage').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const storageId = e.currentTarget.dataset.storageId;
                    this.deleteStorage(storageId);
                });
            });

            // Toggle storage buttons
            document.querySelectorAll('.toggle-storage').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const storageId = e.currentTarget.dataset.storageId;
                    const isActive = e.currentTarget.dataset.active === 'True';
                    this.toggleStorage(storageId, !isActive);
                });
            });

            // Save storage button
            const saveBtn = document.getElementById('saveStorageBtn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => this.saveStorage());
            }

            // Test connection button in modal
            const testBtn = document.getElementById('testConnectionBtn');
            if (testBtn) {
                testBtn.addEventListener('click', () => this.testNewConnection());
            }
        },

        testConnection: function(storageId) {
            const button = document.querySelector(`.test-connection[data-storage-id="${storageId}"]`);
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-arrow-repeat spinner-border spinner-border-sm"></i> テスト中...';
            }

            fetch(`/api/storage/${storageId}/test`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    ScheduleManager.showAlert('接続テストに成功しました', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    ScheduleManager.showAlert('接続テストに失敗しました: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                ScheduleManager.showAlert('テスト中にエラーが発生しました', 'danger');
            })
            .finally(() => {
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="bi bi-arrow-repeat"></i> 接続テスト';
                }
            });
        },

        loadStorage: function(storageId) {
            // Load storage data for editing
            fetch(`/api/storage/${storageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Storage data:', data.storage);
                    // Populate edit modal
                } else {
                    ScheduleManager.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                ScheduleManager.showAlert('読み込み中にエラーが発生しました', 'danger');
            });
        },

        deleteStorage: function(storageId) {
            if (!confirm('このストレージプロバイダーを削除してもよろしいですか?')) {
                return;
            }

            fetch(`/api/storage/${storageId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    ScheduleManager.showAlert('ストレージプロバイダーを削除しました', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    ScheduleManager.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                ScheduleManager.showAlert('削除中にエラーが発生しました', 'danger');
            });
        },

        toggleStorage: function(storageId, activate) {
            fetch(`/api/storage/${storageId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({is_active: activate})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const action = activate ? '有効化' : '無効化';
                    ScheduleManager.showAlert(`ストレージプロバイダーを${action}しました`, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    ScheduleManager.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                ScheduleManager.showAlert('更新中にエラーが発生しました', 'danger');
            });
        },

        saveStorage: function() {
            const form = document.getElementById('storageForm');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            fetch('/api/storage/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    ScheduleManager.showAlert('ストレージプロバイダーを作成しました', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    ScheduleManager.showAlert('エラー: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                ScheduleManager.showAlert('保存中にエラーが発生しました', 'danger');
            });
        },

        testNewConnection: function() {
            const form = document.getElementById('storageForm');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            fetch('/api/storage/test-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    ScheduleManager.showAlert('接続テストに成功しました', 'success');
                } else {
                    ScheduleManager.showAlert('接続テストに失敗しました: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                ScheduleManager.showAlert('テスト中にエラーが発生しました', 'danger');
            });
        }
    };

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        if (document.getElementById('scheduleTable')) {
            ScheduleManager.init();
        }
        if (document.querySelector('.storage-card')) {
            StorageManager.init();
        }
    });

    // Export for global access if needed
    window.ScheduleManager = ScheduleManager;
    window.StorageManager = StorageManager;
    window.CronParser = CronParser;

})();
