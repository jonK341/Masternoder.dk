/**
 * Chart.js Enhanced - Advanced data visualizations
 */
class ChartJSEnhanced {
    constructor() {
        this.charts = {};
    }

    createPointsChart(canvasId, pointsData) {
        if (typeof Chart === 'undefined') {
            console.warn('[ChartJS] Chart.js not loaded');
            return;
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext('2d');

        // Destroy existing chart
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const pointTypes = Object.keys(pointsData).filter(key => 
            typeof pointsData[key] === 'number' && pointsData[key] > 0
        );

        this.charts[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: pointTypes.map(type => type.replace('_', ' ').toUpperCase()),
                datasets: [{
                    data: pointTypes.map(type => pointsData[type]),
                    backgroundColor: [
                        'rgba(0, 255, 136, 0.8)',
                        'rgba(0, 212, 255, 0.8)',
                        'rgba(255, 68, 68, 0.8)',
                        'rgba(68, 255, 68, 0.8)',
                        'rgba(255, 170, 0, 0.8)',
                        'rgba(255, 215, 0, 0.8)',
                        'rgba(136, 136, 255, 0.8)',
                    ],
                    borderColor: [
                        'rgba(0, 255, 136, 1)',
                        'rgba(0, 212, 255, 1)',
                        'rgba(255, 68, 68, 1)',
                        'rgba(68, 255, 68, 1)',
                        'rgba(255, 170, 0, 1)',
                        'rgba(255, 215, 0, 1)',
                        'rgba(136, 136, 255, 1)',
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.parsed.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    createProgressChart(canvasId, progressData) {
        if (typeof Chart === 'undefined') {
            return;
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext('2d');

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: progressData.labels || [],
                datasets: [{
                    label: 'Progress',
                    data: progressData.values || [],
                    borderColor: 'rgba(0, 255, 136, 1)',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }

    destroyChart(canvasId) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
            delete this.charts[canvasId];
        }
    }
}

// Global instance
const chartJSEnhanced = new ChartJSEnhanced();

