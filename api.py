#!/usr/bin/env python3
"""
API сервер для HLS Stream Checker
Предоставляет веб-интерфейс и API для управления проверкой HLS потоков
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Импорт конфигурации проекта
import config

app = Flask(__name__, static_folder='web', template_folder='web')
CORS(app)

# Глобальные переменные
current_process: Optional[subprocess.Popen] = None
log_buffer = []
is_checking = False
check_thread: Optional[threading.Thread] = None
start_time = None

# Директории
PROJECT_ROOT = Path(__file__).parent.absolute()
WEB_DIR = PROJECT_ROOT / "web"
DATA_DIR = PROJECT_ROOT / "data"
CSV_DIR = DATA_DIR / "csv"
JSON_DIR = DATA_DIR / "json"
LOGS_DIR = PROJECT_ROOT / "logs"


@app.route('/')
def index():
    """Главная страница - веб-интерфейс"""
    return send_from_directory(WEB_DIR, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    """Обслуживание статических файлов"""
    return send_from_directory(WEB_DIR, filename)


@app.route('/api/health')
def health_check():
    """Проверка состояния API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "isChecking": is_checking,
        "uptime": (datetime.now() - start_time).total_seconds() if start_time else 0
    })


@app.route('/api/check', methods=['POST'])
def start_check():
    """Запуск проверки HLS потоков"""
    global current_process, is_checking, check_thread, log_buffer, start_time
    
    if is_checking:
        return jsonify({"error": "Проверка уже запущена"}), 400
    
    data = request.get_json()
    
    # Получение параметров
    channel_count = data.get('channelCount', 'all')
    duration = data.get('duration', 5)
    refresh_playlist = data.get('refreshPlaylist', False)
    export_data = data.get('exportData', True)
    monitor_interval = data.get('monitorInterval', 60)
    
    # Формирование команды
    cmd = ["python", "hls_checker_single.py", 
           "--count", str(channel_count),
           "--minutes", str(duration),
           "--monitor-interval", str(monitor_interval)]
    
    if refresh_playlist:
        cmd.append("--refresh")
    
    if not export_data:
        cmd.append("--no-export")
    
    # Запуск процесса в отдельном потоке
    def run_check():
        global is_checking, log_buffer, current_process
        is_checking = True
        log_buffer = []
        
        try:
            # Запуск процесса
            current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Чтение вывода построчно
            while True:
                output = current_process.stdout.readline()
                if output == '' and current_process.poll() is not None:
                    break
                if output:
                    log_buffer.append(output.strip())
                    # Ограничиваем размер буфера логов
                    if len(log_buffer) > 1000:
                        log_buffer = log_buffer[-500:]  # Оставляем последние 500 записей
            
            current_process.wait()
        except Exception as e:
            log_buffer.append(f"❌ Ошибка запуска проверки: {str(e)}")
        finally:
            is_checking = False
            current_process = None
    
    # Запуск в отдельном потке
    check_thread = threading.Thread(target=run_check)
    check_thread.daemon = True
    check_thread.start()
    
    # Запоминаем время начала
    start_time = datetime.now()
    
    return jsonify({"status": "started", "message": "Проверка HLS потоков начата"})


@app.route('/api/check/stop', methods=['POST'])
def stop_check():
    """Остановка проверки HLS потоков"""
    global current_process, is_checking, check_thread, start_time
    
    if not is_checking:
        return jsonify({"error": "Проверка не запущена"}), 400
    
    # Остановка процесса
    if current_process and current_process.poll() is None:
        current_process.terminate()
        try:
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            current_process.kill()
    
    is_checking = False
    current_process = None
    check_thread = None
    start_time = None
    
    return jsonify({"status": "stopped", "message": "Проверка HLS потоков остановлена"})


@app.route('/api/check/status')
def check_status():
    """Получение статуса проверки"""
    global current_process, start_time
    
    process_running = False
    if current_process:
        process_running = current_process.poll() is None
    
    uptime = 0
    if start_time and is_checking:
        uptime = (datetime.now() - start_time).total_seconds()
    
    return jsonify({
        "isChecking": is_checking,
        "isProcessRunning": process_running,
        "logLines": len(log_buffer),
        "uptime": uptime
    })


@app.route('/api/logs')
def get_logs():
    """Получение логов проверки"""
    # Получение параметров пагинации
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Возврат последних логов
    start_idx = max(0, len(log_buffer) - limit - offset)
    end_idx = len(log_buffer) - offset
    logs = log_buffer[start_idx:end_idx]
    
    return jsonify({
        "logs": logs,
        "total": len(log_buffer),
        "limit": limit,
        "offset": offset
    })


@app.route('/api/data/latest')
def get_latest_data():
    """Получение последних данных проверки"""
    try:
        # Поиск последнего JSON отчета
        json_files = list(JSON_DIR.glob("hls_api_report_*.json"))
        if not json_files:
            return jsonify({"error": "Нет доступных данных"}), 404
        
        # Сортировка по времени создания (новые первыми)
        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_file = json_files[0]
        
        # Чтение данных
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Ошибка загрузки данных: {str(e)}"}), 500


@app.route('/api/data/files')
def get_data_files():
    """Получение списка экспортированных файлов"""
    try:
        files = {
            "csv": [],
            "json": []
        }
        
        # CSV файлы
        if CSV_DIR.exists():
            csv_files = list(CSV_DIR.glob("*.csv"))
            csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for file in csv_files:
                files["csv"].append({
                    "name": file.name,
                    "path": f"/data/csv/{file.name}",
                    "size": file.stat().st_size,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
        
        # JSON файлы
        if JSON_DIR.exists():
            json_files = list(JSON_DIR.glob("*.json"))
            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for file in json_files:
                files["json"].append({
                    "name": file.name,
                    "path": f"/data/json/{file.name}",
                    "size": file.stat().st_size,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
        
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": f"Ошибка получения списка файлов: {str(e)}"}), 500


@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """Обслуживание экспортированных файлов данных"""
    # Определение директории по расширению
    if filename.endswith('.csv'):
        return send_from_directory(CSV_DIR, filename)
    elif filename.endswith('.json'):
        return send_from_directory(JSON_DIR, filename)
    else:
        return jsonify({"error": "Неподдерживаемый тип файла"}), 400


@app.route('/api/config')
def get_config():
    """Получение конфигурации приложения"""
    return jsonify({
        "defaultChannelCount": config.DEFAULT_CHANNEL_COUNT,
        "defaultDurationMinutes": config.DEFAULT_DURATION_MINUTES,
        "defaultRefreshPlaylist": config.DEFAULT_REFRESH_PLAYLIST,
        "defaultExportData": config.DEFAULT_EXPORT_DATA,
        "requestTimeout": config.REQUEST_TIMEOUT,
        "maxRetries": config.MAX_RETRIES,
        "serviceCheckInterval": config.SERVICE_CHECK_INTERVAL
    })


def main():
    """Запуск API сервера"""
    global start_time
    start_time = datetime.now()
    
    print("🚀 Запуск API сервера HLS Stream Checker...")
    print("🌐 Доступен по адресу: http://localhost:5000")
    print("📁 Статические файлы: web/")
    print("📊 Данные экспорта: data/")
    print("📋 Логи: logs/")
    print("⌨️  Нажмите Ctrl+C для остановки")
    
    # Создание необходимых директорий
    WEB_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    CSV_DIR.mkdir(exist_ok=True)
    JSON_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Запуск сервера
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)


if __name__ == '__main__':
    main()