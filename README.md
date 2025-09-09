# HLS Stream Checker

Professional tool for monitoring and analyzing HLS (HTTP Live Streaming) stream quality with advanced analytics and data export capabilities.

## Features

- Real-time HLS stream quality monitoring
- Detailed analytics and error tracking
- CSV and JSON data export
- Stream availability tracking
- Network performance metrics
- Automated playlist updates
- Systemd service integration
- **Resource usage monitoring** - CPU, memory, network and disk I/O tracking

## 🛠️ Технологии

- **Python 3.8+**
- **Requests** - HTTP запросы
- **Psutil** - system and process utilities
- **Dataclasses** - типизированные структуры данных
- **CSV/JSON** - экспорт данных
- **Logging** - детальное логирование

## 📦 Установка

```
# Клонирование репозитория
git clone https://github.com/username/hls_checker.git
cd hls_checker

# Установка зависимостей
pip install -r requirements.txt

# Запуск проверки
python hls_checker_single.py --help
```

## 🚀 Развёртывание на Ubuntu

### Автоматическая установка

Для автоматической установки всех зависимостей и настройки окружения на Ubuntu, используйте скрипт установки:

```
# Сделать скрипт исполняемым и запустить
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

Скрипт автоматически:
- Установит Python 3 и pip, если они отсутствуют
- Создаст виртуальное окружение
- Установит все зависимости из `requirements.txt`
- Создаст необходимые директории для данных

### Ручной запуск

После установки можно запускать проверку вручную:

```
# Активировать виртуальное окружение
source hls_venv/bin/activate

# Запустить проверку
python hls_checker_single.py --count 5 --minutes 2

# Деактивировать виртуальное окружение
deactivate
```

### Запуск как системный сервис

Для запуска как системного сервиса на Ubuntu:

1. Скопируйте файл сервиса:
   ```bash
   sudo cp hls_checker.service /etc/systemd/system/
   ```

2. Перезагрузите systemd:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Запустите сервис:
   ```bash
   sudo systemctl start hls_checker
   ```

4. Включите автозапуск:
   ```bash
   sudo systemctl enable hls_checker
   ```

5. Проверьте статус:
   ```bash
   sudo systemctl status hls_checker
   ```

### Скрипты управления

- `run_checker.sh` - скрипт для удобного запуска с параметрами
- `deploy.sh` - скрипт для полного развертывания на сервере

## 🚀 Использование

### Базовые команды

```
# Проверка одного канала на 1 минуту с мониторингом ресурсов каждые 30 секунд
python hls_checker_single.py --count 1 --minutes 1 --monitor-interval 30

# Проверка 5 каналов на 3 минуты
python hls_checker_single.py --count 5 --minutes 3

# Проверка всех каналов
python hls_checker_single.py --count all --minutes 2

# Обновить плейлист и проверить
python hls_checker_single.py --refresh --count 3 --minutes 1

# Запуск без экспорта данных
python hls_checker_single.py --count 1 --minutes 1 --no-export
```

### Параметры

| Параметр | Описание | Значения |
|----------|----------|----------|
| `--count` | Количество каналов для проверки | `1`, `10`, `20`, `all` |
| `--minutes` | Продолжительность проверки в минутах | Любое целое число |
| `--refresh` | Обновить плейлист перед проверкой | Флаг |
| `--no-export` | Отключить экспорт в CSV/JSON | Флаг |
| `--monitor-interval` | Интервал мониторинга ресурсов в секундах | Любое целое число (по умолчанию 60) |

## 📊 Экспорт данных

### CSV файлы (для менеджеров)

1. **hls_channels_final_stats_YYYYMMDD_HHMMSS.csv** - Финальная статистика каналов
2. **hls_global_summary_YYYYMMDD_HHMMSS.csv** - Общая сводка

### JSON файлы (для API/фронтенда)

1. **hls_api_report_YYYYMMDD_HHMMSS.json** - Структурированный отчет для API

### Структура данных

```
data/
├── csv/           # CSV файлы для Excel/менеджеров
├── json/          # JSON файлы для API/фронтенда
└── README.md      # Описание структуры данных
```

## 📈 Пример отчета

```
🏆 ОБЩАЯ ИТОГОВАЯ СТАТИСТИКА
📺 Общее количество каналов: 3
✅ Успешно проверено: 3
⏱ Общая продолжительность: 185.2 секунд
📈 Всего сегментов: 45
✅ Успешных загрузок: 43
❌ Неудачных загрузок: 2
🎯 Общий процент успеха: 95.6%
📡 Общий объём данных: 67.8 MB

🖥️ СВОДКА ПО РЕСУРСАМ:
📈 Средняя загрузка CPU: 1.65%
📈 Среднее использование памяти: 50.25%
🔥 Пиковая загрузка CPU: 2.1%
🔥 Пиковое использование памяти: 50.3%
📊 Количество измерений: 2
```

## 🏗️ Архитектура

```
hls_checker/
├── hls_checker_single.py      # Основной модуль
├── resource_monitor.py       # Мониторинг ресурсов
├── data_exporter.py          # Экспорт данных
├── stream_check_al_jazeare.py # Альтернативная реализация
├── playlist_streams.json     # Кэш плейлиста
├── data/                     # Экспортированные данные
│   ├── csv/                  # CSV отчеты
│   ├── json/                 # JSON отчеты
│   └── README.md            # Описание данных
└── README.md                # Этот файл
```

## 📝 Структуры данных

### SegmentStats
```python
@dataclass
class SegmentStats:
    name: str                 # Имя сегмента
    url: str                 # URL сегмента
    success: bool            # Успешность загрузки
    size_bytes: int          # Размер в байтах
    download_time: float     # Время загрузки
    timestamp: datetime      # Временная метка
    error_message: str       # Сообщение об ошибке
```

### ChannelStats
```python
@dataclass
class ChannelStats:
    channel_name: str        # Название канала
    total_segments: int      # Общее количество сегментов
    successful_downloads: int # Успешные загрузки
    success_rate: float      # Процент успешности
    avg_download_speed: float # Средняя скорость MB/s
    duration: float          # Продолжительность проверки
```

### ResourceStats
```python
@dataclass
class ResourceStats:
    timestamp: datetime      # Временная метка
    cpu_percent: float       # Загрузка CPU в процентах
    memory_percent: float    # Использование памяти в процентах
    memory_mb: float         # Использование памяти в мегабайтах
    network_bytes_sent: int  # Отправлено байт по сети
    network_bytes_recv: int  # Получено байт по сети
    disk_io_read_bytes: int  # Прочитано байт с диска
    disk_io_write_bytes: int # Записано байт на диск
```

## 🔧 Разработка

### Требования к коду

- Python 3.8+
- Type hints для всех функций
- Docstrings на русском языке
- Логирование всех операций
- Обработка исключений

### Стиль кода

- PEP 8 совместимость
- Русские комментарии и документация
- Emoji в логах для лучшей читаемости
- Dataclasses для структур данных

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 👥 Авторы

- **Команда разработки** - *Первоначальная работа*

## 📞 Поддержка

Если у вас есть вопросы или предложения:

1. Создайте [Issue](https://github.com/username/hls_checker/issues)
2. Отправьте Pull Request
3. Обратитесь к команде разработки

---

<div align="center">
  <p>Сделано с ❤️ для мониторинга HLS потоков</p>
</div>