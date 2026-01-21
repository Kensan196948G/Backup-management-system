/**
 * Dashboard Real-time Updates
 * Polls server every 5 seconds for latest data
 */

class DashboardUpdater {
    constructor(updateInterval = 5000) {
        this.updateInterval = updateInterval;
        this.isActive = true;
        this.charts = {};
    }

    /**
     * Start auto-update
     */
    start() {
        this.isActive = true;
        this.update();
        this.intervalId = setInterval(() => {
            if (this.isActive) {
                this.update();
            }
        }, this.updateInterval);
    }

    /**
     * Stop auto-update
     */
    stop() {
        this.isActive = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }

    /**
     * Fetch and update dashboard data
     */
    async update() {
        try {
            const response = await fetch('/api/dashboard/stats');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            this.updateStats(data);
            this.updateCharts(data);
            this.updateAlerts(data.alerts);
            this.updateLastUpdate();
        } catch (error) {
            console.error('Dashboard update failed:', error);
            this.showError('データの更新に失敗しました');
        }
    }

    /**
     * Update statistics cards
     */
    updateStats(data) {
        if (data.stats) {
            this.updateElement('total-jobs', data.stats.total_jobs);
            this.updateElement('active-jobs', data.stats.active_jobs);
            this.updateElement('success-rate', data.stats.success_rate + '%');
            this.updateElement('total-media', data.stats.total_media);
            this.updateElement('compliance-rate', data.stats.compliance_rate + '%');
        }
    }

    /**
     * Update charts with new data
     */
    updateCharts(data) {
        // Update job status chart
        if (this.charts.jobStatus && data.job_status) {
            this.charts.jobStatus.data.datasets[0].data = [
                data.job_status.success,
                data.job_status.failed,
                data.job_status.running,
                data.job_status.pending
            ];
            this.charts.jobStatus.update('none'); // Update without animation
        }

        // Update compliance chart
        if (this.charts.compliance && data.compliance) {
            this.charts.compliance.data.datasets[0].data = [
                data.compliance.compliant,
                data.compliance.non_compliant
            ];
            this.charts.compliance.update('none');
        }

        // Update trend chart
        if (this.charts.trend && data.trend) {
            this.charts.trend.data.labels = data.trend.dates;
            this.charts.trend.data.datasets[0].data = data.trend.success;
            this.charts.trend.data.datasets[1].data = data.trend.failed;
            this.charts.trend.update('none');
        }
    }

    /**
     * Update alerts dropdown
     */
    updateAlerts(alerts) {
        if (!alerts || alerts.length === 0) {
            return;
        }

        const alertCount = document.getElementById('alert-count');
        const alertList = document.getElementById('alert-list');

        if (alertCount) {
            alertCount.textContent = alerts.length;
            alertCount.style.display = alerts.length > 0 ? 'inline' : 'none';
        }

        if (alertList) {
            alertList.innerHTML = alerts.map(alert => `
                <li>
                    <a class="dropdown-item" href="${alert.url}">
                        <div class="d-flex align-items-start">
                            <i class="bi bi-${alert.icon} text-${alert.severity} me-2"></i>
                            <div>
                                <strong>${alert.title}</strong><br>
                                <small class="text-muted">${alert.message}</small>
                            </div>
                        </div>
                    </a>
                </li>
            `).join('<li><hr class="dropdown-divider"></li>');
        }
    }

    /**
     * Update last update timestamp
     */
    updateLastUpdate() {
        const element = document.getElementById('last-update');
        if (element) {
            const now = new Date();
            element.textContent = now.toLocaleTimeString('ja-JP');
        }
    }

    /**
     * Update element content safely
     */
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element && value !== undefined) {
            element.textContent = value;
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        // You can implement toast notification here
        console.error(message);
    }

    /**
     * Register chart for updates
     */
    registerChart(name, chart) {
        this.charts[name] = chart;
    }
}

// Initialize dashboard updater when DOM is ready
let dashboardUpdater;

document.addEventListener('DOMContentLoaded', function() {
    dashboardUpdater = new DashboardUpdater(5000); // Update every 5 seconds

    // Start auto-update if on dashboard page
    if (document.getElementById('dashboard-container')) {
        dashboardUpdater.start();
    }

    // Stop update when user leaves page
    window.addEventListener('beforeunload', function() {
        if (dashboardUpdater) {
            dashboardUpdater.stop();
        }
    });

    // Pause updates when tab is not visible
    document.addEventListener('visibilitychange', function() {
        if (dashboardUpdater) {
            if (document.hidden) {
                dashboardUpdater.stop();
            } else {
                dashboardUpdater.start();
            }
        }
    });
});

// Export for use in other scripts
window.DashboardUpdater = DashboardUpdater;
window.dashboardUpdater = dashboardUpdater;
