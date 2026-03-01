/**
 * Chart.js Configuration and Utilities
 * Custom chart configurations for the backup management system
 */

// Default chart colors
const chartColors = {
    primary: '#0d6efd',
    success: '#198754',
    danger: '#dc3545',
    warning: '#ffc107',
    info: '#0dcaf0',
    secondary: '#6c757d',
    light: '#f8f9fa',
    dark: '#212529'
};

// Default chart options
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                padding: 15,
                font: {
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: {
                size: 14
            },
            bodyFont: {
                size: 13
            },
            cornerRadius: 4
        }
    }
};

/**
 * Create Compliance Rate Donut Chart
 */
function createComplianceChart(canvasId, compliantCount, nonCompliantCount) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const total = compliantCount + nonCompliantCount;
    const complianceRate = total > 0 ? ((compliantCount / total) * 100).toFixed(1) : 0;

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['準拠', '非準拠'],
            datasets: [{
                data: [compliantCount, nonCompliantCount],
                backgroundColor: [chartColors.success, chartColors.danger],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            ...defaultChartOptions,
            cutout: '70%',
            plugins: {
                ...defaultChartOptions.plugins,
                tooltip: {
                    ...defaultChartOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        },
        plugins: [{
            id: 'centerText',
            beforeDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                ctx.restore();

                const fontSize = (height / 114).toFixed(2);
                ctx.font = `bold ${fontSize}em sans-serif`;
                ctx.textBaseline = 'middle';

                const text = `${complianceRate}%`;
                const textX = Math.round((width - ctx.measureText(text).width) / 2);
                const textY = height / 2;

                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });

    return chart;
}

/**
 * Create Job Success Rate Bar Chart
 */
function createSuccessRateChart(canvasId, jobData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: jobData.labels,
            datasets: [
                {
                    label: '成功',
                    data: jobData.success,
                    backgroundColor: chartColors.success,
                    borderRadius: 4
                },
                {
                    label: '失敗',
                    data: jobData.failed,
                    backgroundColor: chartColors.danger,
                    borderRadius: 4
                }
            ]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                x: {
                    stacked: false,
                    grid: {
                        display: false
                    }
                },
                y: {
                    stacked: false,
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    return chart;
}

/**
 * Create Time Series Trend Line Chart
 */
function createTrendChart(canvasId, trendData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.dates,
            datasets: [
                {
                    label: '成功',
                    data: trendData.success,
                    borderColor: chartColors.success,
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: '失敗',
                    data: trendData.failed,
                    borderColor: chartColors.danger,
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            ...defaultChartOptions,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                ...defaultChartOptions.plugins,
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    }
                }
            }
        }
    });

    return chart;
}

/**
 * Create Media Usage Pie Chart
 */
function createMediaUsageChart(canvasId, mediaData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['使用中', '使用可能', '貸出中', 'メンテナンス', '破棄予定'],
            datasets: [{
                data: [
                    mediaData.in_use || 0,
                    mediaData.available || 0,
                    mediaData.lent || 0,
                    mediaData.maintenance || 0,
                    mediaData.retired || 0
                ],
                backgroundColor: [
                    chartColors.primary,
                    chartColors.success,
                    chartColors.warning,
                    chartColors.info,
                    chartColors.danger
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: defaultChartOptions
    });

    return chart;
}

/**
 * Create Verification Results Chart
 */
function createVerificationChart(canvasId, verificationData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['成功', '失敗', '警告'],
            datasets: [{
                data: [
                    verificationData.passed || 0,
                    verificationData.failed || 0,
                    verificationData.warning || 0
                ],
                backgroundColor: [
                    chartColors.success,
                    chartColors.danger,
                    chartColors.warning
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            ...defaultChartOptions,
            cutout: '60%'
        }
    });

    return chart;
}

/**
 * Create Storage Capacity Chart
 */
function createStorageChart(canvasId, storageData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: storageData.labels,
            datasets: [{
                label: '使用量 (GB)',
                data: storageData.used,
                backgroundColor: chartColors.primary,
                borderRadius: 4
            }, {
                label: '空き容量 (GB)',
                data: storageData.free,
                backgroundColor: chartColors.light,
                borderRadius: 4
            }]
        },
        options: {
            ...defaultChartOptions,
            indexAxis: 'y',
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true
                }
            }
        }
    });

    return chart;
}

/**
 * Update chart data dynamically
 */
function updateChartData(chart, newData) {
    if (!chart) return;

    chart.data.datasets.forEach((dataset, index) => {
        if (newData[index]) {
            dataset.data = newData[index];
        }
    });

    chart.update('none'); // Update without animation for performance
}

/**
 * Destroy chart safely
 */
function destroyChart(chart) {
    if (chart) {
        chart.destroy();
    }
}

// Export functions
window.ChartUtils = {
    createComplianceChart,
    createSuccessRateChart,
    createTrendChart,
    createMediaUsageChart,
    createVerificationChart,
    createStorageChart,
    updateChartData,
    destroyChart,
    chartColors,
    defaultChartOptions
};
