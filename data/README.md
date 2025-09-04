# HLS Checker - Экспортированные данные

## Описание файлов

### CSV файлы (data/csv/)

1. **segments_stats_YYYYMMDD_HHMMSS.csv** - Детальная статистика по каждому сегменту
   - timestamp_session: Время начала сессии
   - channel_name: Название канала
   - segment_name: Имя сегмента
   - success: Успешность загрузки (True/False)
   - size_mb: Размер в мегабайтах
   - download_time_seconds: Время загрузки в секундах
   - download_speed_mbps: Скорость загрузки в MB/s
   - error_message: Сообщение об ошибке (если есть)

2. **channels_stats_YYYYMMDD_HHMMSS.csv** - Агрегированная статистика по каналам
   - channel_name: Название канала
   - total_segments: Общее количество сегментов
   - success_rate_percent: Процент успешности
   - total_mb: Общий объем данных в MB
   - avg_download_speed_mbps: Средняя скорость загрузки

3. **summary_stats_YYYYMMDD_HHMMSS.csv** - Общая сводная статистика сессии
   - total_channels: Общее количество каналов
   - overall_success_rate_percent: Общий процент успешности
   - total_mb: Общий объем загруженных данных

### JSON файлы (data/json/)

1. **full_stats_YYYYMMDD_HHMMSS.json** - Полная статистика в структурированном виде
   - metadata: Метаданные сессии
   - global_statistics: Полная статистика
   - analysis: Аналитические данные (лучший/худший канал, ошибки)

## Использование данных

### Анализ в Excel/Google Sheets
Импортируйте CSV файлы для создания графиков и сводных таблиц.

### Программная обработка
Используйте JSON файлы для автоматической обработки и создания отчетов.

### Python пример
```python
import pandas as pd
import json

# Загрузка данных сегментов
segments_df = pd.read_csv('data/csv/segments_stats_20240904_201200.csv')

# Анализ успешности по каналам
success_by_channel = segments_df.groupby('channel_name')['success'].mean()

# Загрузка JSON для детального анализа
with open('data/json/full_stats_20240904_201200.json', 'r', encoding='utf-8') as f:
    full_stats = json.load(f)
```

## Структура папок
```
data/
├── csv/           # CSV файлы для табличного анализа
├── json/          # JSON файлы для программной обработки
└── README.md      # Этот файл с описанием
```
