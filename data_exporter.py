#!/usr/bin/env python3
"""
Оптимизированный модуль экспорта финальной статистики HLS проверки

Экспортирует только финальную статистику каналов и общую сводку
в дублированных форматах: CSV для менеджеров, JSON для API/фронтенда.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Константы путей
DATA_DIR = Path("data")
CSV_DIR = DATA_DIR / "csv"
JSON_DIR = DATA_DIR / "json"

logger = logging.getLogger("data_exporter")


class OptimizedDataExporter:
    """Оптимизированный экспортер финальной статистики HLS проверки"""
    
    def __init__(self, session_start: datetime, session_end: Optional[datetime] = None):
        """
        Инициализация экспортера данных
        
        Args:
            session_start: Время начала сессии
            session_end: Время окончания сессии (если None, используется текущее время)
        """
        self.session_start = session_start
        self.session_end = session_end or datetime.now()
        
        # Создаем уникальные идентификаторы сессии
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.session_duration = (self.session_end - self.session_start).total_seconds()
        
        # Создаем директории если не существуют
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создает необходимые директории для экспорта"""
        DATA_DIR.mkdir(exist_ok=True)
        CSV_DIR.mkdir(exist_ok=True)
        JSON_DIR.mkdir(exist_ok=True)
    
    def export_channels_summary_csv(self, global_stats) -> Path:
        """
        Экспортирует финальную статистику каналов в CSV (для менеджеров)
        
        Args:
            global_stats: Объект GlobalStats с данными
            
        Returns:
            Путь к созданному CSV файлу
        """
        # Лучшие практики именования: префикс_содержание_время
        csv_filename = f"hls_channels_final_stats_{self.session_id}.csv"
        csv_path = CSV_DIR / csv_filename
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'время_начала_сессии',
                'время_окончания_сессии',
                'продолжительность_секунд',
                'название_канала',
                'id_канала',
                'всего_сегментов',
                'успешных_загрузок',
                'неудачных_загрузок',
                'процент_успешности',
                'общий_объем_МБ',
                'средняя_скорость_МБ_с',
                'время_проверки_секунд',
                'master_url',
                'variant_url'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for channel in global_stats.channels:
                if channel.total_segments > 0:  # Только каналы с данными
                    total_mb = channel.total_bytes / (1024 * 1024) if channel.total_bytes > 0 else 0
                    
                    row = {
                        'время_начала_сессии': self.session_start.strftime('%Y-%m-%d %H:%M:%S'),
                        'время_окончания_сессии': self.session_end.strftime('%Y-%m-%d %H:%M:%S'),
                        'продолжительность_секунд': round(self.session_duration, 1),
                        'название_канала': channel.channel_name,
                        'id_канала': channel.channel_id,
                        'всего_сегментов': channel.total_segments,
                        'успешных_загрузок': channel.successful_downloads,
                        'неудачных_загрузок': channel.failed_downloads,
                        'процент_успешности': round(channel.success_rate, 2),
                        'общий_объем_МБ': round(total_mb, 2),
                        'средняя_скорость_МБ_с': round(channel.avg_download_speed, 3),
                        'время_проверки_секунд': round(channel.duration, 1),
                        'master_url': channel.master_url,
                        'variant_url': channel.variant_url
                    }
                    writer.writerow(row)
        
        logger.info(f"📈 Финальная статистика каналов экспортирована в CSV: {csv_path}")
        return csv_path
    
    def export_global_summary_csv(self, global_stats) -> Path:
        """
        Экспортирует общую сводную статистику в CSV (для менеджеров)
        
        Args:
            global_stats: Объект GlobalStats с данными
            
        Returns:
            Путь к созданному CSV файлу
        """
        csv_filename = f"hls_global_summary_{self.session_id}.csv"
        csv_path = CSV_DIR / csv_filename
        
        total_mb = global_stats.total_bytes / (1024 * 1024) if global_stats.total_bytes > 0 else 0
        avg_speed = (total_mb / self.session_duration) if self.session_duration > 0 else 0
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'время_начала_сессии',
                'время_окончания_сессии',
                'общая_продолжительность_секунд',
                'общее_количество_каналов',
                'успешно_проверено_каналов',
                'всего_сегментов',
                'успешных_загрузок',
                'неудачных_загрузок',
                'общий_процент_успешности',
                'общий_объем_МБ',
                'средняя_скорость_МБ_с'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            row = {
                'время_начала_сессии': self.session_start.strftime('%Y-%m-%d %H:%M:%S'),
                'время_окончания_сессии': self.session_end.strftime('%Y-%m-%d %H:%M:%S'),
                'общая_продолжительность_секунд': round(self.session_duration, 1),
                'общее_количество_каналов': global_stats.total_channels,
                'успешно_проверено_каналов': global_stats.completed_channels,
                'всего_сегментов': global_stats.total_segments,
                'успешных_загрузок': global_stats.successful_downloads,
                'неудачных_загрузок': global_stats.failed_downloads,
                'общий_процент_успешности': round(global_stats.overall_success_rate, 2),
                'общий_объем_МБ': round(total_mb, 2),
                'средняя_скорость_МБ_с': round(avg_speed, 3)
            }
            writer.writerow(row)
        
        logger.info(f"📊 Общая сводная статистика экспортирована в CSV: {csv_path}")
        return csv_path
    
    def export_optimized_json(self, global_stats) -> Path:
        """
        Экспортирует оптимизированную статистику в JSON (для фронтенда/API)
        
        Args:
            global_stats: Объект GlobalStats с данными
            
        Returns:
            Путь к созданному JSON файлу
        """
        json_filename = f"hls_api_report_{self.session_id}.json"
        json_path = JSON_DIR / json_filename
        
        # Создаем оптимизированную структуру для API
        api_data = {
            "analytics": {
                "overall_analysis": {
                    "success_rate": round(global_stats.overall_success_rate, 2),
                    "total_errors": global_stats.failed_downloads,
                    "error_distribution": global_stats.error_counts if hasattr(global_stats, 'error_counts') else {}
                }
            },
            "session": {
                "id": self.session_id,
                "start_time": self.session_start.isoformat(),
                "end_time": self.session_end.isoformat(),
                "duration_seconds": round(self.session_duration, 1),
                "export_timestamp": datetime.now().isoformat()
            },
            "summary": {
                "total_channels": global_stats.total_channels,
                "completed_channels": global_stats.completed_channels,
                "total_segments": global_stats.total_segments,
                "successful_downloads": global_stats.successful_downloads,
                "failed_downloads": global_stats.failed_downloads,
                "overall_success_rate": round(global_stats.overall_success_rate, 2),
                "total_data_mb": round(global_stats.total_bytes / (1024 * 1024), 2)
            },
            "channels": []
        }
        
        # Добавляем финальную статистику каналов
        for channel in global_stats.channels:
            if channel.total_segments > 0:
                # Подготовка статистики по ошибкам для канала
                error_stats = {}
                if hasattr(channel, 'error_counts'):
                    error_stats = {
                        "error_count": channel.failed_downloads,
                        "error_details": channel.error_counts
                    }
                
                channel_data = {
                    "id": channel.channel_id,
                    "name": channel.channel_name,
                    "stats": {
                        "total_segments": channel.total_segments,
                        "successful_downloads": channel.successful_downloads,
                        "failed_downloads": channel.failed_downloads,
                        "success_rate": round(channel.success_rate, 2),
                        "total_data_mb": round(
                            channel.total_bytes / (1024 * 1024), 
                            2
                        ),
                        "avg_speed_mbps": round(channel.avg_download_speed, 3),
                        "duration_seconds": round(channel.duration, 1),
                        "errors": error_stats
                    },
                    "urls": {
                        "master": channel.master_url,
                        "variant": channel.variant_url
                    }
                }
                api_data["channels"].append(channel_data)
        
        # Добавляем аналитику
        if api_data["channels"]:
            best_channel = max(api_data["channels"], key=lambda x: x["stats"]["success_rate"])
            worst_channel = min(api_data["channels"], key=lambda x: x["stats"]["success_rate"])
            
            # Обновляем analytics с детальной информацией
            api_data["analytics"].update({
                "best_channel": {
                    "name": best_channel["name"],
                    "success_rate": best_channel["stats"]["success_rate"],
                    "errors": best_channel["stats"].get("errors", {})
                },
                "worst_channel": {
                    "name": worst_channel["name"],
                    "success_rate": worst_channel["stats"]["success_rate"],
                    "errors": worst_channel["stats"].get("errors", {})
                },
                "channels_analysis": [
                    {
                        "name": ch["name"],
                        "success_rate": ch["stats"]["success_rate"],
                        "errors": ch["stats"].get("errors", {})
                    }
                    for ch in sorted(
                        api_data["channels"],
                        key=lambda x: x["stats"]["success_rate"],
                        reverse=True
                    )
                ]
            })
        
        # Сохраняем в JSON
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(api_data, jsonfile, ensure_ascii=False, indent=2)
        
        logger.info(f"🚀 API отчет экспортирован в JSON: {json_path}")
        return json_path
    
    def export_final_statistics(self, global_stats) -> Dict[str, Path]:
        """
        Экспортирует только финальную статистику в оптимальные форматы
        
        Args:
            global_stats: Объект GlobalStats с данными
            
        Returns:
            Словарь с путями к созданным файлам
        """
        logger.info("🚀 Начало экспорта финальной статистики...")
        
        exported_files = {
            'channels_csv': self.export_channels_summary_csv(global_stats),
            'global_csv': self.export_global_summary_csv(global_stats),
            'api_json': self.export_optimized_json(global_stats)
        }
        
        logger.info("=" * 70)
        logger.info("📁 ЭКСПОРТ ФИНАЛЬНОЙ СТАТИСТИКИ ЗАВЕРШЕН!")
        logger.info("📊 Созданные файлы:")
        for file_type, file_path in exported_files.items():
            if 'csv' in file_type:
                logger.info(f"   📈 {file_type}: {file_path} (для менеджеров)")
            else:
                logger.info(f"   🚀 {file_type}: {file_path} (для API/фронтенда)")
        logger.info("=" * 70)
        
        return exported_files


def create_optimized_readme():
    """Создает оптимизированный README файл с описанием структуры данных"""
    readme_content = """# HLS Checker - Финальные отчеты

## 📊 Описание файлов

### CSV файлы (для менеджеров и аналитиков)

1. **hls_channels_final_stats_YYYYMMDD_HHMMSS.csv** - Финальная статистика по каналам
   - время_начала_сессии / время_окончания_сессии: Временные рамки проверки
   - название_канала: Название проверяемого канала
   - процент_успешности: Процент успешных загрузок сегментов
   - общий_объем_МБ: Общий объем загруженных данных
   - средняя_скорость_МБ_с: Средняя скорость загрузки

2. **hls_global_summary_YYYYMMDD_HHMMSS.csv** - Общая сводка по всем каналам
   - общее_количество_каналов: Всего каналов в проверке
   - общий_процент_успешности: Общий показатель успешности
   - общий_объем_МБ: Общий объем данных всех каналов

### JSON файлы (для API и фронтенда)

1. **hls_api_report_YYYYMMDD_HHMMSS.json** - Структурированный API отчет
   - session: Метаданные сессии с временными метками
   - summary: Агрегированная статистика
   - channels: Массив данных по каналам
   - analytics: Лучший и худший каналы

## 🎯 Использование

### Для менеджеров
Откройте CSV файлы в Excel/Google Sheets для анализа и создания презентаций.

### Для разработчиков
Используйте JSON API для интеграции с дашбордами и веб-интерфейсами.

### Python пример работы с JSON
```python
import json

# Загрузка API отчета
with open('data/json/hls_api_report_20240904_201200.json', 'r', encoding='utf-8') as f:
    api_data = json.load(f)

# Получение сводки
summary = api_data['summary']
print(f"Общий успех: {summary['overall_success_rate']}%")

# Анализ каналов
for channel in api_data['channels']:
    print(f"{channel['name']}: {channel['stats']['success_rate']}%")
```

## 📁 Структура
```
data/
├── csv/           # CSV для Excel/менеджеров
├── json/          # JSON для API/фронтенда
└── README.md      # Этот файл
```
"""
    
    readme_path = DATA_DIR / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    logger.info(f"📖 Оптимизированный README создан: {readme_path}")
    return readme_path