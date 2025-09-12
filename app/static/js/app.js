// Arabic TV HLS Stream Checker Frontend Application
class ArabicTVMonitor {
    constructor() {
        this.apiBase = '/v1/api/arabic_tv';
        this.channels = [];
        this.currentReportId = null;
        this.monitoringInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startStatusPolling();
    }

    setupEventListeners() {
        // Form submission
        document.getElementById('monitoring-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startMonitoring();
        });

        // Stop monitoring
        document.getElementById('stopBtn').addEventListener('click', () => {
            this.stopMonitoring();
        });

        // Channel type selection
        document.querySelectorAll('input[name="channelType"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const channelSelection = document.getElementById('channel-selection');
                if (e.target.value === 'specific') {
                    channelSelection.style.display = 'block';
                } else {
                    channelSelection.style.display = 'none';
                }
            });
        });

        // Refresh buttons
        document.getElementById('refreshChannels').addEventListener('click', () => {
            this.loadChannels();
        });

        document.getElementById('refreshReports').addEventListener('click', () => {
            this.loadReports();
        });

        document.getElementById('refreshLogs').addEventListener('click', () => {
            this.loadLogs();
        });

        // Log filtering
        document.getElementById('logLevel').addEventListener('change', () => {
            this.loadLogs();
        });

        document.getElementById('logSearch').addEventListener('input', 
            this.debounce(() => this.loadLogs(), 500)
        );

        // Tab switching
        document.querySelectorAll('#mainTabs button[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                const target = e.target.getAttribute('data-bs-target');
                if (target === '#reports') {
                    this.loadReports();
                } else if (target === '#logs') {
                    this.loadLogs();
                }
            });
        });

        // Report modal download buttons
        document.getElementById('downloadJsonReport').addEventListener('click', () => {
            if (this.currentReportId) {
                this.downloadReport(this.currentReportId, 'json');
            }
        });

        document.getElementById('downloadCsvReport').addEventListener('click', () => {
            if (this.currentReportId) {
                this.downloadReport(this.currentReportId, 'csv');
            }
        });
    }

    async loadInitialData() {
        await this.loadChannels();
        await this.loadReports();
        this.updateQuickStats();
    }

    async loadChannels() {
        try {
            this.showLoading('channelsTable');
            const response = await fetch(`${this.apiBase}/channels`);
            const channels = await response.json();
            
            this.channels = channels;
            this.renderChannelsTable(channels);
            this.populateChannelSelect(channels);
            this.updateQuickStats();
        } catch (error) {
            console.error('Error loading channels:', error);
            this.showError('Failed to load channels');
            document.getElementById('channelsTable').innerHTML = 
                '<tr><td colspan="4" class="text-center text-danger">Error loading channels</td></tr>';
        }
    }

    renderChannelsTable(channels) {
        const tbody = document.getElementById('channelsTable');
        
        if (channels.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No channels available</td></tr>';
            return;
        }

        tbody.innerHTML = channels.map(channel => `
            <tr>
                <td><strong>${channel.our_id}</strong></td>
                <td>${this.escapeHtml(channel.name_ru)}</td>
                <td>
                    <small class="text-muted">${this.truncateUrl(channel.url)}</small>
                </td>
                <td>
                    <span class="channel-status unknown">Unknown</span>
                </td>
            </tr>
        `).join('');
    }

    populateChannelSelect(channels) {
        const select = document.getElementById('channelIds');
        select.innerHTML = channels.map(channel => `
            <option value="${channel.our_id}">${channel.our_id} - ${this.escapeHtml(channel.name_ru)}</option>
        `).join('');
    }

    async startMonitoring() {
        try {
            const formData = this.getFormData();
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');

            startBtn.disabled = true;
            startBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Starting...';

            const response = await fetch(`${this.apiBase}/monitoring/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to start monitoring');
            }

            this.showSuccess('Monitoring started successfully!');
            startBtn.style.display = 'none';
            stopBtn.disabled = false;
            stopBtn.style.display = 'block';

            // Show status card
            document.getElementById('status-card').style.display = 'block';

        } catch (error) {
            console.error('Error starting monitoring:', error);
            this.showError(error.message);
            
            const startBtn = document.getElementById('startBtn');
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Start Monitoring';
        }
    }

    async stopMonitoring() {
        try {
            const stopBtn = document.getElementById('stopBtn');
            stopBtn.disabled = true;
            stopBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Stopping...';

            const response = await fetch(`${this.apiBase}/monitoring/stop`, {
                method: 'POST'
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to stop monitoring');
            }

            this.showSuccess('Monitoring stopped successfully!');
            this.resetMonitoringUI();

        } catch (error) {
            console.error('Error stopping monitoring:', error);
            this.showError(error.message);
            
            const stopBtn = document.getElementById('stopBtn');
            stopBtn.disabled = false;
            stopBtn.innerHTML = '<i class="bi bi-stop-fill"></i> Stop Monitoring';
        }
    }

    getFormData() {
        const channelType = document.querySelector('input[name="channelType"]:checked').value;
        let channels;

        if (channelType === 'all') {
            channels = 'all';
        } else {
            const selectedOptions = Array.from(document.getElementById('channelIds').selectedOptions);
            channels = selectedOptions.map(option => parseInt(option.value));
            
            if (channels.length === 0) {
                throw new Error('Please select at least one channel');
            }
        }

        return {
            channels: channels,
            duration_minutes: parseInt(document.getElementById('duration').value),
            export_data: document.getElementById('exportData').checked
        };
    }

    startStatusPolling() {
        this.monitoringInterval = setInterval(() => {
            this.updateMonitoringStatus();
        }, 2000); // Poll every 2 seconds
    }

    async updateMonitoringStatus() {
        try {
            const response = await fetch(`${this.apiBase}/monitoring/status`);
            const status = await response.json();

            this.updateStatusIndicator(status);
            this.updateStatusCard(status);

            // If monitoring completed, refresh reports
            if (status.status === 'completed') {
                setTimeout(() => {
                    this.loadReports();
                    this.resetMonitoringUI();
                }, 1000);
            }

        } catch (error) {
            console.error('Error updating status:', error);
        }
    }

    updateStatusIndicator(status) {
        const indicator = document.getElementById('status-indicator').querySelector('i');
        const text = document.getElementById('status-text');

        indicator.className = 'bi bi-circle-fill';
        
        switch (status.status) {
            case 'running':
                indicator.classList.add('status-running');
                text.textContent = 'Monitoring';
                break;
            case 'completed':
                indicator.classList.add('text-success');
                text.textContent = 'Completed';
                break;
            case 'error':
                indicator.classList.add('status-error');
                text.textContent = 'Error';
                break;
            default:
                indicator.classList.add('status-idle');
                text.textContent = 'Idle';
        }
    }

    updateStatusCard(status) {
        if (status.status === 'idle') {
            document.getElementById('status-card').style.display = 'none';
            return;
        }

        document.getElementById('status-card').style.display = 'block';
        document.getElementById('monitoringStatus').textContent = status.status;
        document.getElementById('startTime').textContent = status.start_time ? 
            new Date(status.start_time).toLocaleString() : '-';
        document.getElementById('monitoringDuration').textContent = status.duration_minutes || '-';
        document.getElementById('channelsCount').textContent = status.channels_count || '-';
        
        const progress = status.progress_percent || 0;
        document.getElementById('progressPercent').textContent = progress.toFixed(1);
        document.getElementById('progressBar').style.width = `${progress}%`;
        
        document.getElementById('estimatedCompletion').textContent = status.estimated_completion ?
            new Date(status.estimated_completion).toLocaleString() : '-';
    }

    resetMonitoringUI() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');

        startBtn.disabled = false;
        startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Start Monitoring';
        startBtn.style.display = 'block';

        stopBtn.disabled = true;
        stopBtn.innerHTML = '<i class="bi bi-stop-fill"></i> Stop Monitoring';
        stopBtn.style.display = 'none';

        document.getElementById('status-card').style.display = 'none';
    }

    async loadReports(page = 1) {
        try {
            this.showLoading('reportsTable');
            const response = await fetch(`${this.apiBase}/reports?page=${page}&per_page=10`);
            const data = await response.json();

            this.renderReportsTable(data.reports);
            this.renderPagination('reportsPagination', data, (p) => this.loadReports(p));
            this.updateQuickStats();

        } catch (error) {
            console.error('Error loading reports:', error);
            this.showError('Failed to load reports');
            document.getElementById('reportsTable').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Error loading reports</td></tr>';
        }
    }

    renderReportsTable(reports) {
        const tbody = document.getElementById('reportsTable');

        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No reports available</td></tr>';
            return;
        }

        tbody.innerHTML = reports.map(report => `
            <tr>
                <td>
                    <small class="text-muted">${report.report_id.substring(0, 8)}...</small>
                </td>
                <td>${new Date(report.start_time).toLocaleString()}</td>
                <td>${report.duration_minutes} min</td>
                <td>${report.channels_count}</td>
                <td>
                    <span class="badge ${this.getSuccessRateBadgeClass(report.success_rate)}">
                        ${report.success_rate.toFixed(1)}%
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" 
                            onclick="app.viewReport('${report.report_id}')">
                        <i class="bi bi-eye"></i>
                    </button>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-success dropdown-toggle" 
                                data-bs-toggle="dropdown">
                            <i class="bi bi-download"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" 
                                   onclick="app.downloadReport('${report.report_id}', 'json')">
                                <i class="bi bi-filetype-json"></i> JSON
                            </a></li>
                            <li><a class="dropdown-item" href="#" 
                                   onclick="app.downloadReport('${report.report_id}', 'csv')">
                                <i class="bi bi-filetype-csv"></i> CSV
                            </a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    async viewReport(reportId) {
        try {
            this.currentReportId = reportId;
            const response = await fetch(`${this.apiBase}/reports/${reportId}`);
            const report = await response.json();

            if (!response.ok) {
                throw new Error(report.detail || 'Failed to load report');
            }

            this.renderReportModal(report);
            const modal = new bootstrap.Modal(document.getElementById('reportModal'));
            modal.show();

        } catch (error) {
            console.error('Error viewing report:', error);
            this.showError(error.message);
        }
    }

    renderReportModal(report) {
        const modalBody = document.getElementById('reportModalBody');
        
        modalBody.innerHTML = `
            <div class="report-summary">
                <div class="row">
                    <div class="col-md-3">
                        <div class="metric-value">${report.total_channels}</div>
                        <div class="metric-label">Channels</div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-value">${report.total_checks}</div>
                        <div class="metric-label">Total Checks</div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-value">${report.overall_success_rate.toFixed(1)}%</div>
                        <div class="metric-label">Success Rate</div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-value">${report.duration_minutes}</div>
                        <div class="metric-label">Duration (min)</div>
                    </div>
                </div>
            </div>
            
            <h6>Channel Details</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Channel</th>
                            <th>Checks</th>
                            <th>Success</th>
                            <th>Failed</th>
                            <th>Success Rate</th>
                            <th>Avg Response</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${report.streams.map(stream => `
                            <tr>
                                <td>
                                    <strong>${stream.channel_id}</strong><br>
                                    <small class="text-muted">${this.escapeHtml(stream.channel_name)}</small>
                                </td>
                                <td>${stream.total_checks}</td>
                                <td class="text-success">${stream.successful_checks}</td>
                                <td class="text-danger">${stream.failed_checks}</td>
                                <td>
                                    <span class="badge ${this.getSuccessRateBadgeClass(stream.success_rate)}">
                                        ${stream.success_rate.toFixed(1)}%
                                    </span>
                                </td>
                                <td>${stream.avg_response_time.toFixed(3)}s</td>
                                <td>
                                    <span class="badge ${this.getStatusBadgeClass(stream.status)}">
                                        ${stream.status}
                                    </span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    async downloadReport(reportId, format) {
        try {
            const response = await fetch(`${this.apiBase}/reports/${reportId}/download?format=${format}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to download report');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `arabic_tv_report_${reportId}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            this.showSuccess(`Report downloaded as ${format.toUpperCase()}`);

        } catch (error) {
            console.error('Error downloading report:', error);
            this.showError(error.message);
        }
    }

    async loadLogs(page = 1) {
        try {
            this.showLoading('logsContainer');
            
            const level = document.getElementById('logLevel').value;
            const search = document.getElementById('logSearch').value;
            
            let url = `${this.apiBase}/logs?page=${page}&per_page=50`;
            if (level) url += `&level=${level}`;
            if (search) url += `&search=${encodeURIComponent(search)}`;

            const response = await fetch(url);
            const data = await response.json();

            this.renderLogs(data.logs);
            this.renderPagination('logsPagination', data, (p) => this.loadLogs(p));

        } catch (error) {
            console.error('Error loading logs:', error);
            this.showError('Failed to load logs');
            document.getElementById('logsContainer').innerHTML = 
                '<div class="text-center text-danger">Error loading logs</div>';
        }
    }

    renderLogs(logs) {
        const container = document.getElementById('logsContainer');

        if (logs.length === 0) {
            container.innerHTML = '<div class="text-center">No logs found</div>';
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="log-entry">
                <span class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</span>
                <span class="log-level ${log.level}">${log.level}</span>
                ${log.source ? `<span class="text-muted">[${log.source}]</span>` : ''}
                <div class="log-message">${this.escapeHtml(log.message)}</div>
            </div>
        `).join('');

        // Auto-scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    renderPagination(containerId, data, onPageClick) {
        const container = document.getElementById(containerId);
        
        if (data.total_count <= data.per_page) {
            container.innerHTML = '';
            return;
        }

        const totalPages = Math.ceil(data.total_count / data.per_page);
        const currentPage = data.page;

        let pagination = '<ul class="pagination pagination-sm">';
        
        // Previous button
        pagination += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="event.preventDefault(); ${currentPage > 1 ? `app.${onPageClick.name}(${currentPage - 1})` : ''}">
                    <i class="bi bi-chevron-left"></i>
                </a>
            </li>
        `;

        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        if (startPage > 1) {
            pagination += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="event.preventDefault(); app.${onPageClick.name}(1)">1</a>
                </li>
            `;
            if (startPage > 2) {
                pagination += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            pagination += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="event.preventDefault(); app.${onPageClick.name}(${i})">${i}</a>
                </li>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                pagination += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
            pagination += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="event.preventDefault(); app.${onPageClick.name}(${totalPages})">${totalPages}</a>
                </li>
            `;
        }

        // Next button
        pagination += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="event.preventDefault(); ${currentPage < totalPages ? `app.${onPageClick.name}(${currentPage + 1})` : ''}">
                    <i class="bi bi-chevron-right"></i>
                </a>
            </li>
        `;

        pagination += '</ul>';
        container.innerHTML = pagination;
    }

    updateQuickStats() {
        document.getElementById('totalChannels').textContent = this.channels.length;
        // Total reports will be updated when reports are loaded
    }

    // Utility methods
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        element.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                Loading...
            </div>
        `;
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container');
        const alertId = 'alert-' + Date.now();
        
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" id="${alertId}" role="alert">
                ${this.escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHtml);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }
        }, 5000);
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    truncateUrl(url, maxLength = 50) {
        if (url.length <= maxLength) return url;
        return url.substring(0, maxLength) + '...';
    }

    getSuccessRateBadgeClass(rate) {
        if (rate >= 90) return 'bg-success';
        if (rate >= 70) return 'bg-warning';
        return 'bg-danger';
    }

    getStatusBadgeClass(status) {
        switch (status) {
            case 'active': return 'bg-success';
            case 'warning': return 'bg-warning';
            case 'error': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the application
const app = new ArabicTVMonitor();
