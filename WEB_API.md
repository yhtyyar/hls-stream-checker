# Веб API HLS Stream Checker

## Обзор

Веб API предоставляет программный интерфейс для управления проверкой HLS потоков и получения результатов через HTTP запросы.

## Базовый URL

```
http://localhost:5000/api
```

## Endpoint'ы

### 1. Проверка состояния API

**GET** `/api/health`

Проверяет состояние API сервера.

**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-11T10:30:00",
  "isChecking": false,
  "uptime": 120.5
}
```

### 2. Получение конфигурации

**GET** `/api/config`

Получает текущую конфигурацию приложения.

**Ответ:**
```json
{
  "defaultChannelCount": "all",
  "defaultDurationMinutes": 5,
  "defaultRefreshPlaylist": false,
  "defaultExportData": true,
  "requestTimeout": 20,
  "maxRetries": 3,
  "serviceCheckInterval": 60
}
```

### 3. Запуск проверки

**POST** `/api/check`

Запускает проверку HLS потоков с указанными параметрами.

**Тело запроса:**
```json
{
  "channelCount": "5",
  "duration": 3,
  "refreshPlaylist": true,
  "exportData": true,
  "monitorInterval": 30
}
```

**Ответ:**
```json
{
  "status": "started",
  "message": "Проверка HLS потоков начата"
}
```

### 4. Остановка проверки

**POST** `/api/check/stop`

Останавливает текущую проверку HLS потоков.

**Ответ:**
```json
{
  "status": "stopped",
  "message": "Проверка HLS потоков остановлена"
}
```

### 5. Получение статуса проверки

**GET** `/api/check/status`

Получает текущий статус проверки.

**Ответ:**
```json
{
  "isChecking": true,
  "isProcessRunning": true,
  "logLines": 45,
  "uptime": 120.5
}
```

### 6. Получение логов

**GET** `/api/logs?limit=50&offset=0`

Получает логи проверки с пагинацией.

**Параметры:**
- `limit` (опционально): Количество записей (по умолчанию 100)
- `offset` (опционально): Смещение (по умолчанию 0)

**Ответ:**
```json
{
  "logs": [
    "[2025-09-11 10:30:01] 🚀 НАЧАЛО ПРОВЕРКИ HLS КАНАЛОВ",
    "[2025-09-11 10:30:02] 📄 Всего каналов для проверки: 5"
  ],
  "total": 45,
  "limit": 50,
  "offset": 0
}
```

### 7. Получение последних данных

**GET** `/api/data/latest`

Получает последние данные проверки в формате JSON.

**Ответ:**
```json
{
  "analytics": {
    "overall_analysis": {
      "success_rate": 92.5,
      "total_errors": 3
    }
  },
  "session": {
    "id": "20250911_103000",
    "start_time": "2025-09-11T10:30:00",
    "end_time": "2025-09-11T10:35:00"
  },
  "summary": {
    "total_channels": 20,
    "completed_channels": 18,
    "overall_success_rate": 92.78
  },
  "channels": [
    {
      "name": "Al Jazeera الجزيرة",
      "stats": {
        "success_rate": 100.0,
        "total_data_mb": 12.5
      }
    }
  ]
}
```

### 8. Получение списка файлов данных

**GET** `/api/data/files`

Получает список экспортированных файлов данных.

**Ответ:**
```json
{
  "csv": [
    {
      "name": "hls_channels_final_stats_20250911_103000.csv",
      "path": "/data/csv/hls_channels_final_stats_20250911_103000.csv",
      "size": 2048,
      "modified": "2025-09-11T10:35:00"
    }
  ],
  "json": [
    {
      "name": "hls_api_report_20250911_103000.json",
      "path": "/data/json/hls_api_report_20250911_103000.json",
      "size": 1024,
      "modified": "2025-09-11T10:35:00"
    }
  ]
}
```

### 9. Скачивание файлов данных

**GET** `/data/<filename>`

Скачивает указанный файл данных.

**Пример:**
```
GET /data/json/hls_api_report_20250911_103000.json
```

## Коды ошибок

- `200`: Успешный запрос
- `400`: Некорректный запрос
- `404`: Ресурс не найден
- `500`: Внутренняя ошибка сервера

## Примеры использования

### Запуск проверки с Python

```python
import requests

# Запуск проверки
response = requests.post('http://localhost:5000/api/check', json={
    'channelCount': '5',
    'duration': 3,
    'refreshPlaylist': True
})

if response.status_code == 200:
    print("Проверка начата успешно")
else:
    print(f"Ошибка: {response.status_code}")
```

### Получение последних данных с JavaScript

```javascript
fetch('/api/data/latest')
    .then(response => response.json())
    .then(data => {
        console.log(`Общий процент успеха: ${data.summary.overall_success_rate}%`);
    })
    .catch(error => {
        console.error('Ошибка получения данных:', error);
    });
```