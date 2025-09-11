// Глобальные переменные
let isChecking = false;
let logData = "";
let logUpdateInterval = null;

// DOM элементы
const checkForm = document.getElementById('checkForm');
const startCheckBtn = document.getElementById('startCheck');
const stopCheckBtn = document.getElementById('stopCheck');
const clearLogsBtn = document.getElementById('clearLogs');
const downloadLogsBtn = document.getElementById('downloadLogs');
const refreshDataBtn = document.getElementById('refreshData');
const statusMessage = document.getElementById('statusMessage');
const progressFill = document.getElementById('progressFill');
const logContent = document.getElementById('logContent');
const globalStats = document.getElementById('globalStats');
const channelsData = document.getElementById('channelsData');
const exportedFiles = document.getElementById('exportedFiles');

// Обработчики событий
document.addEventListener('DOMContentLoaded', function () {
    // Загрузка начальных данных
    loadInitialData();

    // Назначение обработчиков
    checkForm.addEventListener('submit', startCheck);
    stopCheckBtn.addEventListener('click', stopCheck);
    clearLogsBtn.addEventListener('click', clearLogs);
    downloadLogsBtn.addEventListener('click', downloadLogs);
    refreshDataBtn.addEventListener('click', loadInitialData);

    // Периодическое обновление статуса
    setInterval(updateCheckStatus, 2000);
});

// Загрузка начальных данных
function loadInitialData() {
    loadGlobalStats();
    loadChannelsData();
    loadExportedFiles();
}

// Обновление статуса проверки
function updateCheckStatus() {
    fetch('/api/check/status')
        .then(response => response.json())
        .then(data => {
            isChecking = data.isChecking;
            if (isChecking) {
                startCheckBtn.disabled = true;
                stopCheckBtn.disabled = false;
                // Обновляем логи в реальном времени
                updateLogs();
            } else {
                startCheckBtn.disabled = false;
                stopCheckBtn.disabled = true;
            }
        })
        .catch(error => {
            console.error('Ошибка получения статуса:', error);
        });
}

// Обновление логов
function updateLogs() {
    fetch('/api/logs?limit=50')
        .then(response => response.json())
        .then(data => {
            if (data.logs && data.logs.length > 0) {
                // Отображаем последние логи
                logContent.textContent = data.logs.join('\n');
                logContent.scrollTop = logContent.scrollHeight;
            }
        })
        .catch(error => {
            console.error('Ошибка получения логов:', error);
        });
}

// Загрузка общей статистики
function loadGlobalStats() {
    fetch('/api/data/latest')
        .then(response => {
            if (!response.ok) {
                throw new Error('Нет данных');
            }
            return response.json();
        })
        .then(data => {
            if (data.summary) {
                globalStats.innerHTML = `
                    <ul>
                        <li>📊 Общее количество каналов: <strong>${data.summary.total_channels}</strong></li>
                        <li>✅ Успешно проверено: <strong>${data.summary.completed_channels}</strong></li>
                        <li>⏱ Общая продолжительность: <strong>${data.summary.duration_seconds || 'N/A'} секунд</strong></li>
                        <li>📈 Всего сегментов: <strong>${data.summary.total_segments}</strong></li>
                        <li>✅ Успешных загрузок: <strong>${data.summary.successful_downloads}</strong></li>
                        <li>❌ Неудачных загрузок: <strong>${data.summary.failed_downloads}</strong></li>
                        <li>🎯 Общий процент успеха: <strong>${data.summary.overall_success_rate}%</strong></li>
                        <li>📡 Общий объём данных: <strong>${data.summary.total_data_mb || 0} MB</strong></li>
                    </ul>
                `;

                // Добавляем сводку по ресурсам если есть
                if (data.analytics && data.analytics.resource_summary) {
                    const resourceSummary = data.analytics.resource_summary;
                    globalStats.innerHTML += `
                        <div class="resource-summary">
                            <h4>🖥️ Сводка по ресурсам:</h4>
                            <ul>
                                <li>📈 Средняя загрузка CPU: <strong>${resourceSummary.cpu_average || 0}%</strong> (${resourceSummary.cpu_absolute_average || 0}% от общего количества ${resourceSummary.cpu_count || 0} ядер)</li>
                                <li>📈 Среднее использование памяти: <strong>${resourceSummary.memory_average_percent || 0}%</strong> (${resourceSummary.memory_average_mb || 0} MB из ${resourceSummary.memory_total_mb || 0} MB всего)</li>
                                <li>🔥 Пиковая загрузка CPU: <strong>${resourceSummary.cpu_peak || 0}%</strong> (${resourceSummary.cpu_absolute_peak || 0}% от общего количества ${resourceSummary.cpu_count || 0} ядер)</li>
                                <li>🔥 Пиковое использование памяти: <strong>${resourceSummary.memory_peak_percent || 0}%</strong> (${resourceSummary.memory_peak_mb || 0} MB из ${resourceSummary.memory_total_mb || 0} MB всего)</li>
                                <li>📊 Количество измерений: <strong>${resourceSummary.measurements_count || 0}</strong></li>
                            </ul>
                        </div>
                    `;
                }
            } else {
                globalStats.innerHTML = '<p>Данные будут загружены после первой проверки...</p>';
            }
        })
        .catch(error => {
            globalStats.innerHTML = '<p>Данные будут загружены после первой проверки...</p>';
        });
}

// Загрузка данных по каналам
function loadChannelsData() {
    fetch('/api/data/latest')
        .then(response => {
            if (!response.ok) {
                throw new Error('Нет данных');
            }
            return response.json();
        })
        .then(data => {
            if (data.channels && data.channels.length > 0) {
                let channelsHtml = '<ul>';
                data.channels.forEach(channel => {
                    const successRate = channel.stats.success_rate;
                    const className = successRate >= 90 ? 'success' : (successRate >= 70 ? 'warning' : 'error');
                    channelsHtml += `
                        <li class="${className}">
                            📺 ${channel.name}: <strong>${successRate}%</strong> успеха, ${channel.stats.total_data_mb || 0} MB данных
                        </li>
                    `;
                });
                channelsHtml += '</ul>';
                channelsData.innerHTML = channelsHtml;
            } else {
                channelsData.innerHTML = '<p>Данные будут загружены после первой проверки...</p>';
            }
        })
        .catch(error => {
            channelsData.innerHTML = '<p>Данные будут загружены после первой проверки...</p>';
        });
}

// Загрузка списка экспортированных файлов
function loadExportedFiles() {
    fetch('/api/data/files')
        .then(response => response.json())
        .then(data => {
            let filesHtml = '<ul>';

            // Добавляем CSV файлы
            if (data.csv && data.csv.length > 0) {
                filesHtml += '<h4>CSV отчеты:</h4>';
                data.csv.forEach(file => {
                    filesHtml += `
                        <li>
                            <a href="${file.path}" target="_blank" download>${file.name}</a> 
                            (${(file.size / 1024).toFixed(1)} KB)
                        </li>
                    `;
                });
            }

            // Добавляем JSON файлы
            if (data.json && data.json.length > 0) {
                filesHtml += '<h4>JSON данные:</h4>';
                data.json.forEach(file => {
                    filesHtml += `
                        <li>
                            <a href="${file.path}" target="_blank" download>${file.name}</a> 
                            (${(file.size / 1024).toFixed(1)} KB)
                        </li>
                    `;
                });
            }

            if (data.csv.length === 0 && data.json.length === 0) {
                filesHtml += '<li>После проверки здесь будут отображаться ссылки на экспортированные файлы</li>';
            }

            filesHtml += '</ul>';
            exportedFiles.innerHTML = filesHtml;
        })
        .catch(error => {
            exportedFiles.innerHTML = '<p>Ошибка загрузки списка файлов</p>';
        });
}

// Начало проверки
function startCheck(e) {
    e.preventDefault();

    if (isChecking) return;

    // Получение значений формы
    const channelCount = document.getElementById('channelCount').value;
    const duration = document.getElementById('duration').value;
    const refreshPlaylist = document.getElementById('refreshPlaylist').checked;
    const exportData = document.getElementById('exportData').checked;

    // Подготовка данных для отправки
    const requestData = {
        channelCount: channelCount,
        duration: parseInt(duration),
        refreshPlaylist: refreshPlaylist,
        exportData: exportData,
        monitorInterval: 30  // Фиксированный интервал мониторинга
    };

    // Отправка запроса на запуск проверки
    fetch('/api/check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'started') {
                // Обновление UI
                isChecking = true;
                startCheckBtn.disabled = true;
                stopCheckBtn.disabled = false;
                statusMessage.textContent = "🚀 Начало проверки HLS потоков...";
                logContent.textContent = "📥 Подготовка к проверке...\n";

                // Начинаем периодическое обновление логов
                if (logUpdateInterval) {
                    clearInterval(logUpdateInterval);
                }
                logUpdateInterval = setInterval(updateLogs, 2000);
            } else {
                statusMessage.textContent = "❌ Ошибка запуска проверки";
            }
        })
        .catch(error => {
            console.error('Ошибка запуска проверки:', error);
            statusMessage.textContent = "❌ Ошибка запуска проверки: " + error.message;
        });
}

// Остановка проверки
function stopCheck() {
    if (!isChecking) return;

    // Отправка запроса на остановку проверки
    fetch('/api/check/stop', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'stopped') {
                // Обновление UI
                isChecking = false;
                startCheckBtn.disabled = false;
                stopCheckBtn.disabled = true;
                statusMessage.textContent = "⏹ Проверка остановлена пользователем";

                // Останавливаем обновление логов
                if (logUpdateInterval) {
                    clearInterval(logUpdateInterval);
                    logUpdateInterval = null;
                }

                // Обновляем данные
                setTimeout(() => {
                    loadInitialData();
                }, 1000);
            } else {
                statusMessage.textContent = "❌ Ошибка остановки проверки";
            }
        })
        .catch(error => {
            console.error('Ошибка остановки проверки:', error);
            statusMessage.textContent = "❌ Ошибка остановки проверки: " + error.message;
        });
}

// Добавление записи в лог
function addLogEntry(message) {
    const timestamp = new Date().toLocaleTimeString();
    logData += `[${timestamp}] ${message}\n`;
    logContent.textContent = logData;
    logContent.scrollTop = logContent.scrollHeight;
}

// Очистка логов
function clearLogs() {
    logData = "";
    logContent.textContent = "Логи очищены.";
}

// Скачивание логов
function downloadLogs() {
    fetch('/api/logs')
        .then(response => response.json())
        .then(data => {
            const logText = data.logs.join('\n');
            const blob = new Blob([logText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `hls_check_logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Ошибка скачивания логов:', error);
        });
}