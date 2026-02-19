/**
 * Form Validation and AJAX Submission Utilities
 */

class FormHandler {
    constructor(formId, options = {}) {
        this.form = document.getElementById(formId);
        this.options = {
            validateOnInput: true,
            showSuccessMessage: true,
            redirectOnSuccess: true,
            redirectDelay: 1500,
            ...options
        };

        if (this.form) {
            this.init();
        }
    }

    /**
     * Initialize form handler
     */
    init() {
        this.setupValidation();
        this.setupSubmitHandler();
    }

    /**
     * Setup Bootstrap validation
     */
    setupValidation() {
        // Enable Bootstrap validation
        this.form.classList.add('needs-validation');

        // Real-time validation on input
        if (this.options.validateOnInput) {
            const inputs = this.form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateField(input);
                });

                input.addEventListener('input', () => {
                    if (input.classList.contains('is-invalid')) {
                        this.validateField(input);
                    }
                });
            });
        }

        // Custom validators
        this.addCustomValidators();
    }

    /**
     * Validate single field
     */
    validateField(field) {
        if (!field.checkValidity()) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            return false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            return true;
        }
    }

    /**
     * Validate entire form
     */
    validateForm() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        let isValid = true;

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    /**
     * Setup form submission handler
     */
    setupSubmitHandler() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            this.form.classList.add('was-validated');

            if (!this.form.checkValidity() || !this.validateForm()) {
                this.showError('入力内容に誤りがあります。確認してください。');
                return;
            }

            // Get submit button
            const submitBtn = this.form.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn ? submitBtn.innerHTML : '';

            try {
                // Disable submit button
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>送信中...';
                }

                // Submit form
                if (this.options.ajax) {
                    await this.submitAjax();
                } else {
                    this.form.submit();
                }
            } catch (error) {
                console.error('Form submission error:', error);
                this.showError('送信に失敗しました: ' + error.message);

                // Re-enable submit button
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            }
        });
    }

    /**
     * Submit form via AJAX
     */
    async submitAjax() {
        const formData = new FormData(this.form);
        const method = this.form.method || 'POST';
        const url = this.form.action || window.location.href;

        const response = await fetch(url, {
            method: method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            if (this.options.showSuccessMessage) {
                this.showSuccess(data.message || '正常に送信されました');
            }

            if (this.options.onSuccess) {
                this.options.onSuccess(data);
            }

            if (this.options.redirectOnSuccess && data.redirect_url) {
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, this.options.redirectDelay);
            }
        } else {
            this.showError(data.message || '送信に失敗しました');

            if (this.options.onError) {
                this.options.onError(data);
            }
        }

        return data;
    }

    /**
     * Add custom validators
     */
    addCustomValidators() {
        // Password strength validator
        const passwordInputs = this.form.querySelectorAll('input[type="password"][data-validate="strength"]');
        passwordInputs.forEach(input => {
            input.addEventListener('input', () => {
                const strength = this.checkPasswordStrength(input.value);
                const feedback = input.parentElement.querySelector('.password-strength-feedback');

                if (feedback) {
                    feedback.textContent = strength.message;
                    feedback.className = `password-strength-feedback text-${strength.class}`;
                }

                if (strength.score < 3) {
                    input.setCustomValidity('パスワードが弱すぎます');
                } else {
                    input.setCustomValidity('');
                }
            });
        });

        // Confirm password validator
        const confirmPasswordInputs = this.form.querySelectorAll('input[data-validate="confirm"]');
        confirmPasswordInputs.forEach(input => {
            const originalPasswordId = input.dataset.confirmTarget;
            const originalPassword = document.getElementById(originalPasswordId);

            if (originalPassword) {
                input.addEventListener('input', () => {
                    if (input.value !== originalPassword.value) {
                        input.setCustomValidity('パスワードが一致しません');
                    } else {
                        input.setCustomValidity('');
                    }
                    this.validateField(input);
                });

                originalPassword.addEventListener('input', () => {
                    if (input.value) {
                        this.validateField(input);
                    }
                });
            }
        });

        // Date range validator
        const dateInputs = this.form.querySelectorAll('input[type="date"][data-validate="range"]');
        dateInputs.forEach(input => {
            input.addEventListener('change', () => {
                const startDateId = input.dataset.rangeStart;
                const endDateId = input.dataset.rangeEnd;

                if (startDateId && endDateId) {
                    const startDate = document.getElementById(startDateId);
                    const endDate = document.getElementById(endDateId);

                    if (startDate && endDate) {
                        if (new Date(startDate.value) > new Date(endDate.value)) {
                            endDate.setCustomValidity('終了日は開始日より後である必要があります');
                        } else {
                            startDate.setCustomValidity('');
                            endDate.setCustomValidity('');
                        }
                        this.validateField(startDate);
                        this.validateField(endDate);
                    }
                }
            });
        });
    }

    /**
     * Check password strength
     */
    checkPasswordStrength(password) {
        let score = 0;

        if (!password) {
            return { score: 0, message: '', class: 'muted' };
        }

        // Length
        if (password.length >= 8) score++;
        if (password.length >= 12) score++;

        // Contains lowercase
        if (/[a-z]/.test(password)) score++;

        // Contains uppercase
        if (/[A-Z]/.test(password)) score++;

        // Contains numbers
        if (/\d/.test(password)) score++;

        // Contains special characters
        if (/[^A-Za-z0-9]/.test(password)) score++;

        const messages = [
            { score: 0, message: '', class: 'muted' },
            { score: 1, message: '非常に弱い', class: 'danger' },
            { score: 2, message: '弱い', class: 'warning' },
            { score: 3, message: '普通', class: 'info' },
            { score: 4, message: '強い', class: 'success' },
            { score: 5, message: '非常に強い', class: 'success' }
        ];

        return messages.find(m => m.score === Math.min(score, 5));
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showAlert(message, 'danger');
    }

    /**
     * Show alert message
     */
    showAlert(message, type) {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Insert before form or at top of form
        const alertContainer = document.createElement('div');
        alertContainer.innerHTML = alertHtml;

        if (this.form.parentElement) {
            this.form.parentElement.insertBefore(alertContainer.firstElementChild, this.form);
        } else {
            this.form.insertBefore(alertContainer.firstElementChild, this.form.firstChild);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }

    /**
     * Reset form
     */
    reset() {
        this.form.reset();
        this.form.classList.remove('was-validated');

        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });
    }
}

/**
 * Auto-save form data to localStorage
 */
class FormAutoSave {
    constructor(formId, storageKey) {
        this.form = document.getElementById(formId);
        this.storageKey = storageKey || `form_autosave_${formId}`;

        if (this.form) {
            this.init();
        }
    }

    init() {
        // Load saved data
        this.loadData();

        // Setup auto-save
        this.form.addEventListener('input', () => {
            this.saveData();
        });

        // Clear on submit
        this.form.addEventListener('submit', () => {
            this.clearData();
        });
    }

    saveData() {
        const formData = new FormData(this.form);
        const data = {};

        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }

        localStorage.setItem(this.storageKey, JSON.stringify(data));
    }

    loadData() {
        const savedData = localStorage.getItem(this.storageKey);

        if (savedData) {
            const data = JSON.parse(savedData);

            Object.keys(data).forEach(key => {
                const input = this.form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = data[key];
                }
            });
        }
    }

    clearData() {
        localStorage.removeItem(this.storageKey);
    }
}

// Export utilities
window.FormHandler = FormHandler;
window.FormAutoSave = FormAutoSave;
