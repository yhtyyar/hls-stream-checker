#!/usr/bin/env python3
import argparse
import json
import logging
import os
import signal
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Импорт конфигурации
import config
# Импорт модуля мониторинга ресурсов
from resource_monitor import (start_resource_monitoring,
                              stop_resource_monitoring)

# -------------------- Конфигурация --------------------
PLAYLIST_URL = config.PLAYLIST_URL
PLAYLIST_PARAMS = config.PLAYLIST_PARAMS

# X-LHD-Agent header для всех запросов
X_LHD_AGENT = config.X_LHD_AGENT
X_LHD_AGENT_HEADER = json.dumps(X_LHD_AGENT, separators=(",", ":"))

# Базовые и специальные заголовки
BASE_HEADERS = {
    "user-agent": config.USER_AGENT,
    "x-lhd-agent": X_LHD_AGENT_HEADER,
}

PLAYLIST_HEADERS = {
    **BASE_HEADERS,
    "Host": "pl.technettv.com",
    "content-type": "application/x-www-form-urlencoded",
    "x-token": "null",
    "cache-control": "no-cache",
}

# Стратегия повторных запросов
RETRY_STRATEGY = Retry(
    total=config.MAX_RETRIES, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
)


def create_session():
    """Создает сессию с настроенными заголовками и retry-стратегией"""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Глобальные объекты
SESSION = create_session()
PLAYLIST_JSON = Path("playlist_streams.json")

# -------------------- Структуры данных для отчетности --------------------
# -------------------- Структуры данных --------------------


@dataclass
class SegmentStats:
    """Статистика одного сегмента"""

    name: str
    url: str
    success: bool
    size_bytes: int = 0
    download_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str = ""
    response_code: int = 0  # Код ответа HTTP


@dataclass
class ChannelStats:
    """Статистика канала"""

    channel_name: str = ""
    channel_id: Optional[str] = None
    master_url: str = ""
    variant_url: str = ""
    total_segments: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    total_bytes: int = 0
    total_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    segments: List[SegmentStats] = field(default_factory=list)
    processed_segments: Set[str] = field(default_factory=set)
    error_counts: Dict[str, Dict[int, int]] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Процент успешных загрузок"""
        if self.total_segments == 0:
            return 0.0
        return (self.successful_downloads / self.total_segments) * 100

    @property
    def avg_download_speed(self) -> float:
        """Средняя скорость загрузки в MB/s"""
        if self.total_time == 0:
            return 0.0
        return (self.total_bytes / (1024 * 1024)) / self.total_time

    @property
    def duration(self) -> float:
        """Длительность проверки в секундах"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


@dataclass
class GlobalStats:
    """Глобальная статистика всех каналов"""

    total_channels: int = 0
    completed_channels: int = 0
    total_segments: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    total_bytes: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    channels: List[ChannelStats] = field(default_factory=list)
    error_counts: Dict[str, Dict[int, int]] = field(default_factory=dict)

    @property
    def overall_success_rate(self) -> float:
        """Общий процент успешных загрузок"""
        if self.total_segments == 0:
            return 0.0
        return (self.successful_downloads / self.total_segments) * 100

    @property
    def duration(self) -> float:
        """Общая длительность в секундах"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


# -------------------- Глобальные объекты --------------------


# Глобальная статистика
global_stats = GlobalStats()


# -------------------- Логирование --------------------


# Создаем форматтер для логов с полной датой
log_formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Настраиваем вывод в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Настраиваем вывод в файл с минутной точностью для различения тестов
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"hls_checker_{timestamp}.log"
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(log_formatter)

# Конфигурируем логгер
logger = logging.getLogger("hls_checker")
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Отключаем лишние сообщения от urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)

# -------------------- API --------------------


def fetch_playlist() -> Optional[Dict]:
    try:
        # Разбиваем длинный payload на читаемые части
        payload_parts = [
            "subs_packs=%5B%5D&payload=",
            "W7ZxsWmx7n6mIy3LgFYDVYFu%2F8pa5iSJctK2rzI",
            "pzaFJyqbPMhjfTANi7fdMC0TXvpGJqInbwhgf%0AT",
            "%2BfiBojLZCzimRIvjowGZfdY",
            "vlrmoWeWe0ml9%2F5v6OaaKWYmM9gRJMUet%2FIJ",
            "TFOvUvrIlgU%2FNUaj%0AyeieV6",
            "a3vV6OcJXzKcDEBNtS0JYS8%2BzK5LmFQvWOxxeb",
            "n45hcwEkQ17jEsomIdPw4R6h4D",
            "gCb5qY%0AdQ0Nra9HwM6tG9s%2FQjBO9xuG21KkX",
            "azegIFLt1pQJpHdzaNiUJcYskS",
            "p%2BGa%2Fv%2FlKUjpG7dV5MVkh%0A2O71a9wjeq",
            "SaKbmq4D9ZhiTYbRZiEhxdli7i",
            "dQ%3D%3D%0A",
        ]
        data = "".join(payload_parts)

        logger.debug("Отправка запроса на %s", PLAYLIST_URL)
        logger.debug("Параметры: %s", PLAYLIST_PARAMS)
        logger.debug("Заголовки: %s", PLAYLIST_HEADERS)

        with SESSION.post(
            PLAYLIST_URL,
            params=PLAYLIST_PARAMS,
            data=data,
            headers=PLAYLIST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        ) as r:
            r.raise_for_status()
            response_data = r.json()
            logger.debug("Получен ответ: %s", r.status_code)
            logger.debug("Размер ответа: %d байт", len(r.text))
            logger.debug("Тип данных ответа: %s", type(response_data))

            if isinstance(response_data, dict):
                logger.debug("Ключи в ответе: %s", list(response_data.keys()))

            return response_data
        r.raise_for_status()

        response_data = r.json()
        logger.debug(f"Получен ответ: {r.status_code}")
        logger.debug(f"Размер ответа: {len(r.text)} байт")
        logger.debug(f"Тип данных ответа: {type(response_data)}")

        if isinstance(response_data, dict):
            logger.debug(f"Ключи в ответе: {list(response_data.keys())}")

        return response_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка HTTP запроса: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Код ответа: {e.response.status_code}")
            logger.error(f"Тело ответа: {e.response.text[:500]}...")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return None


def save_channels(api_json: Dict):
    """Сохраняет полученный список каналов в JSON файл."""
    channels = []
    if not api_json:
        logger.error("Получен пустой ответ от API")
        return

    items = api_json.get("channels", [])
    if not items:
        logger.error("В ответе API нет списка каналов")
        return

    logger.info("Найдено %d каналов в ответе API", len(items))

    for item in items:
        if not item:
            continue

        stream_url = ""
        if "stream" in item and isinstance(item["stream"], dict):
            stream_url = item["stream"].get("common", "").strip()

        channel = {
            "our_id": item.get("our_id"),
            "name_ru": item.get("name_ru") or item.get("title") or "",
            "stream_common": stream_url,
            "url": (item.get("url") or "").strip(),
        }
        channels.append(channel)

    if not channels:
        logger.error("Не удалось извлечь данные каналов из ответа API")
        return

    with open(PLAYLIST_JSON, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

    logger.info("Сохранено %d каналов в %s", len(channels), PLAYLIST_JSON)

    # Выводим первый канал для отладки
    if channels:
        logger.debug(
            "Пример первого канала: %s", json.dumps(channels[0], ensure_ascii=False)
        )


def load_channels() -> List[Dict]:
    """Загружает список каналов из JSON файла."""
    if not PLAYLIST_JSON.exists():
        return []
    with open(PLAYLIST_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------- M3U8 Parser --------------------


def parse_master(text: str, base_url: str) -> List[Dict]:
    """Парсит M3U8 мастер-плейлист и возвращает список вариантов потоков."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    variants = []
    i = 0

    while i < len(lines):
        if not lines[i].startswith("#EXT-X-STREAM-INF:"):
            i += 1
            continue

        # Парсим атрибуты
        attrs = {}
        for part in lines[i].split(":", 1)[1].split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                attrs[k] = v.strip().strip('"')

        # Получаем URI следующей строки
        uri = lines[i + 1] if i + 1 < len(lines) else None
        if not uri:
            i += 1
            continue

        # Разбираем параметры потока
        bw = int(attrs.get("BANDWIDTH", 0))
        res = (0, 0)
        if "RESOLUTION" in attrs:
            try:
                w, h = attrs["RESOLUTION"].split("x")
                res = (int(w), int(h))
            except ValueError:
                logger.warning("Некорректное разрешение: %s", attrs["RESOLUTION"])

        # Добавляем вариант в список
        variants.append({"bw": bw, "res": res, "uri": urljoin(base_url, uri)})
        i += 2

    return variants


def best_variant(variants: List[Dict]) -> Optional[str]:
    """Находит лучший вариант потока по битрейту и разрешению."""
    if not variants:
        return None

    return max(variants, key=lambda v: (v["bw"], v["res"]))["uri"]


# -------------------- Проверка потока --------------------


class HLSStreamChecker:
    def __init__(self, url: str, channel_stats: Optional[ChannelStats] = None):
        self.url = url
        self.running = True
        self.stats = channel_stats or ChannelStats()
        self.segment_buffer = deque(maxlen=100)  # Буфер последних сегментов

        # Используем глобальную сессию для всех запросов
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

    def _stop(self, *_):
        self.running = False

    def fetch_text(self, url: str) -> Optional[str]:
        try:
            # Для HLS потоков используем базовые заголовки
            with SESSION.get(
                url, headers=BASE_HEADERS, timeout=config.REQUEST_TIMEOUT
            ) as r:
                r.raise_for_status()
                return r.text
        except Exception as e:
            logger.error("❌ Ошибка при получении manifest: %s [%s]", url, e)
            return None

    def parse_media(self, text: str) -> List[str]:
        """Извлекает URI сегментов из медиа-плейлиста."""
        return [ln.strip() for ln in text.splitlines() if ln and not ln.startswith("#")]

    def _extract_timestamp_from_url(self, url: str) -> tuple[str, Optional[datetime]]:
        """Извлекает timestamp и форматирует имя сегмента из URL."""
        # Пытаемся извлечь дату из пути URL
        parts = url.split("/")

        try:
            # Проверяем есть ли в URL временная структура YYYY/MM/DD/HH/MM
            if len(parts) >= 6:
                # Проверяем, что части похожи на дату/время
                year = int(parts[-6])
                month = int(parts[-5])
                day = int(parts[-4])
                hour = int(parts[-3])
                minute = int(parts[-2])

                # Извлекаем секунды из имени сегмента
                segment = parts[-1].split("?")[0]  # Отделяем параметры
                segment_time = segment.split("-")[0]
                second = int(segment_time)

                # Формируем полный путь с датой
                timestamp = datetime(year, month, day, hour, minute, second)

                # Форматируем имя с датой
                name_parts = [
                    f"{year}",
                    f"{month:02d}",
                    f"{day:02d}",
                    f"{hour:02d}",
                    f"{minute:02d}",
                    segment,
                ]
                formatted_name = "/".join(name_parts)

                return formatted_name, timestamp

        except (ValueError, IndexError):
            pass

        # Если не удалось извлечь дату, возвращаем оригинальное имя
        return parts[-1], None

    def download_segment(self, url: str) -> tuple[bool, SegmentStats]:
        """Скачивает сегмент и возвращает статистику."""
        # Извлекаем имя файла и timestamp из URL
        segment_name, timestamp = self._extract_timestamp_from_url(url)
        start_time = time.time()

        # Инициализируем статистику сегмента
        segment_stats = SegmentStats(
            name=segment_name,
            url=url,
            success=False,
            # Используем извлеченный timestamp если есть
            timestamp=timestamp or datetime.now(),
        )

        # Логируем начало запроса
        logger.info("📥 Запрашиваю сегмент: %s", segment_name)

        try:
            # Выполняем запрос с настроенными параметрами
            session_params = {
                "url": url,
                "headers": BASE_HEADERS,
                "timeout": config.REQUEST_TIMEOUT,
                "stream": True,
            }

            with SESSION.get(**session_params) as r:
                # Сохраняем код ответа
                segment_stats.response_code = r.status_code
                r.raise_for_status()

                # Скачиваем во временный файл
                tmp = tempfile.NamedTemporaryFile(delete=False)
                total_size = 0

                # Читаем данные блоками
                chunk_size = 1024 * 64  # 64KB chunks
                for chunk in r.iter_content(chunk_size):
                    if chunk:
                        tmp.write(chunk)
                        total_size += len(chunk)

                tmp.close()
                download_time = time.time() - start_time

                # Обновляем статистику
                segment_stats.success = True
                segment_stats.size_bytes = total_size
                segment_stats.download_time = download_time

                # Рассчитываем метрики для лога
                size_mb = total_size / (1024 * 1024)
                speed_mbps = size_mb / download_time if download_time > 0 else 0

                # Формируем сообщение об успешной загрузке
                log_msg = "✅ %s - %.2f MB, время: %.2fs " "(%.2f MB/s) [HTTP %d]"
                log_args = (
                    segment_name,
                    size_mb,
                    download_time,
                    speed_mbps,
                    r.status_code,
                )
                logger.info(log_msg, *log_args)

                # Очищаем временный файл
                os.unlink(tmp.name)
                return True, segment_stats

        except requests.exceptions.RequestException as e:
            download_time = time.time() - start_time
            segment_stats.download_time = download_time

            # Пытаемся получить код ответа из ошибки
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                segment_stats.response_code = status_code
                error_msg = f"HTTP {status_code}: {str(e)}"

                # Обновляем статистику ошибок
                if "http" not in self.stats.error_counts:
                    self.stats.error_counts["http"] = {}
                self.stats.error_counts["http"][status_code] = (
                    self.stats.error_counts["http"].get(status_code, 0) + 1
                )
            else:
                error_msg = f"Ошибка сети: {str(e)}"
                if "network" not in self.stats.error_counts:
                    self.stats.error_counts["network"] = {}
                error_type = type(e).__name__
                self.stats.error_counts["network"][error_type] = (
                    self.stats.error_counts["network"].get(error_type, 0) + 1
                )

            segment_stats.error_message = error_msg
            logger.error(
                "❌ %s - ошибка загрузки после %.2fs: %s",
                segment_name,
                download_time,
                error_msg,
            )

            # Обновляем глобальную статистику ошибок
            error_type = "http" if hasattr(e, "response") and e.response else "network"
            error_code = (
                e.response.status_code
                if hasattr(e, "response") and e.response
                else type(e).__name__
            )

            if error_type not in global_stats.error_counts:
                global_stats.error_counts[error_type] = {}
            global_stats.error_counts[error_type][error_code] = (
                global_stats.error_counts[error_type].get(error_code, 0) + 1
            )

        except Exception as e:
            download_time = time.time() - start_time
            segment_stats.download_time = download_time
            error_msg = f"Неожиданная ошибка: {str(e)}"
            segment_stats.error_message = error_msg

            # Обновляем статистику ошибок
            if "critical" not in self.stats.error_counts:
                self.stats.error_counts["critical"] = {}
            error_type = type(e).__name__
            self.stats.error_counts["critical"][error_type] = (
                self.stats.error_counts["critical"].get(error_type, 0) + 1
            )

            # Обновляем глобальную статистику ошибок
            if "critical" not in global_stats.error_counts:
                global_stats.error_counts["critical"] = {}
            global_stats.error_counts["critical"][error_type] = (
                global_stats.error_counts["critical"].get(error_type, 0) + 1
            )

            logger.error(
                "❌ %s - критическая ошибка после %.2fs: %s",
                segment_name,
                download_time,
                error_msg,
            )

        return False, segment_stats

    def _print_intermediate_stats(self):
        """Печатает промежуточную статистику"""
        if self.stats.total_segments == 0:
            return

        logger.info("📈 ПРОМЕЖУТОЧНАЯ СТАТИСТИКА")
        logger.info(
            "📄 Сегментов: %d/%d (%.1f%% успешно)",
            self.stats.successful_downloads,
            self.stats.total_segments,
            self.stats.success_rate,
        )
        if self.stats.total_bytes > 0:
            logger.info("📡 Загружено: %.2f MB", self.stats.total_bytes / (1024 * 1024))
        if self.stats.avg_download_speed > 0:
            logger.info("⚡ Средняя скорость: %.2f MB/s", self.stats.avg_download_speed)
        logger.info("⏱ Время работы: %.1f секунд", self.stats.duration)

        # Показываем последние ошибки
        recent_errors = [s for s in self.stats.segments[-10:] if not s.success]
        if recent_errors:
            logger.info("⚠️ Последние ошибки: %d из 10", len(recent_errors))

    def _print_final_stats(self):
        """Печатает финальную статистику по каналу"""
        logger.info("=" * 70)
        logger.info("📁 ФИНАЛЬНАЯ СТАТИСТИКА КАНАЛА")

        if self.stats.channel_name:
            logger.info("📺 Канал: %s", self.stats.channel_name)
        logger.info("🔗 URL: %s", self.url)
        logger.info("📈 Всего сегментов: %d", self.stats.total_segments)
        logger.info("✅ Успешных загрузок: %d", self.stats.successful_downloads)
        logger.info("❌ Неудачных загрузок: %d", self.stats.failed_downloads)

        if self.stats.total_segments > 0:
            logger.info("🎯 Процент успеха: %.1f%%", self.stats.success_rate)

        if self.stats.total_bytes > 0:
            total_mb = self.stats.total_bytes / (1024 * 1024)
            logger.info("📡 Общий объем: %.2f MB", total_mb)

        if self.stats.avg_download_speed > 0:
            logger.info("⚡ Средняя скорость: %.2f MB/s", self.stats.avg_download_speed)

        logger.info("⏱ Общая продолжительность: %.1f секунд", self.stats.duration)

        # Показываем детали ошибок
        if self.stats.failed_downloads > 0:
            logger.info("⚠️ Ошибки")
            error_counts = {}
            for seg in self.stats.segments:
                if not seg.success and seg.error_message:
                    err_msg = seg.error_message
                    error_counts[err_msg] = error_counts.get(err_msg, 0) + 1

            for error, count in error_counts.items():
                logger.info("   %s: %d раз", error, count)

        logger.info("=" * 70)

    def run_for_duration(self, seconds: int):
        """Запускает проверку на указанное время с детальной статистикой"""
        logger.info("=" * 70)
        logger.info("🚀 НАЧИНАЮ ПРОВЕРКУ HLS ПОТОКА")
        logger.info("📺 URL: %s", self.url)
        logger.info("⏱ Продолжительность: %d секунд", seconds)
        logger.info("⏹ Для остановки нажмите Ctrl+C")
        logger.info("=" * 70)

        self.stats.start_time = datetime.now()
        end_time = time.time() + seconds
        last_stats_update = time.time()
        stats_update_interval = 10.0  # Обновляем статистику каждые 10 секунд

        while self.running and time.time() < end_time:
            manifest = self.fetch_text(self.url)
            if not manifest:
                logger.warning("⚠️ Не удалось получить манифест. Повторяю попытку...")
                time.sleep(1)
                continue

            segments = self.parse_media(manifest)
            # Находим новые сегменты, которые еще не обработаны
            new_segments = [
                seg for seg in segments if seg not in self.stats.processed_segments
            ]

            for seg in new_segments:
                if time.time() >= end_time or not self.running:
                    break

                self.stats.processed_segments.add(seg)
                full_url = urljoin(self.url, seg)

                success, segment_stats = self.download_segment(full_url)

                # Обновляем статистику
                self.stats.total_segments += 1
                self.stats.segments.append(segment_stats)

                if success:
                    self.stats.successful_downloads += 1
                    self.stats.total_bytes += segment_stats.size_bytes
                    self.stats.total_time += segment_stats.download_time
                    self.segment_buffer.append(segment_stats)
                else:
                    self.stats.failed_downloads += 1

                # Обновляем глобальную статистику
                global_stats.total_segments += 1
                if success:
                    global_stats.successful_downloads += 1
                    global_stats.total_bytes += segment_stats.size_bytes
                else:
                    global_stats.failed_downloads += 1

                # Показываем промежуточную статистику
                current_time = time.time()
                if current_time - last_stats_update >= stats_update_interval:
                    self._print_intermediate_stats()
                    last_stats_update = current_time

                time.sleep(1)  # Пауза между сегментами

        self.stats.end_time = datetime.now()
        self._print_final_stats()
        logger.info("⏹ Проверка завершена")


# -------------------- Оркестратор --------------------
def run_checks(channels: List[Dict], minutes: int, count: str, args):
    """Запускает проверку каналов с детальной отчетностью"""
    # Определяем какие каналы проверять
    if count == "all":
        selected = channels
    else:
        try:
            selected = channels[: int(count)]
        except (ValueError, TypeError):
            selected = channels[:1]

    # Инициализируем глобальную статистику
    global_stats.total_channels = len(selected)
    global_stats.start_time = datetime.now()

    logger.info("=" * 80)
    logger.info("🎆 НАЧАЛО ПРОВЕРКИ HLS КАНАЛОВ")
    logger.info(f"📄 Всего каналов для проверки: {len(selected)}")
    logger.info(f"⏱ Продолжительность каждой проверки: {minutes} минут")
    logger.info(f"📊 Мониторинг ресурсов каждые {args.monitor_interval} секунд")
    logger.info("=" * 80)

    for i, ch in enumerate(selected, 1):
        try:
            # Получаем URL мастер плейлиста
            master = ch.get("stream_common") or ch.get("url")
            if not master:
                logger.warning(
                    "⚠️ Пропускаю канал %s - нет URL", ch.get("name_ru", "Неизвестный")
                )
                continue

            # Создаем статистику для канала
            channel_stats = ChannelStats(
                channel_name=ch.get("name_ru", ""),
                channel_id=ch.get("our_id"),
                master_url=master,
            )
            global_stats.channels.append(channel_stats)

            logger.info("\n" + "=" * 60)
            logger.info(
                "📺 Канал %d/%d: %s", i, len(selected), channel_stats.channel_name
            )
            logger.info("🔗 Master URL: %s", master)

            # Получаем мастер плейлист и находим лучший вариант
            try:
                # Для HLS потоков используем базовые заголовки
                with SESSION.get(
                    master, headers=BASE_HEADERS, timeout=config.REQUEST_TIMEOUT
                ) as response:
                    response.raise_for_status()
                    txt = response.text
            except Exception as e:
                logger.error("❌ Не удалось получить мастер плейлист: %s", e)
                continue

            variants = parse_master(txt, master)
            variant = best_variant(variants) or master
            channel_stats.variant_url = variant

            logger.info(f"⚙️ Найдено вариантов: {len(variants)}")
            logger.info(f"🎯 Выбранный вариант: {variant}")

            # Запускаем проверку
            checker = HLSStreamChecker(variant, channel_stats)
            checker.run_for_duration(minutes * 60)

            global_stats.completed_channels += 1

        except KeyboardInterrupt:
            logger.info("⚠️ Прервано пользователем")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке канала: {e}")
            continue

    # Печатаем итоговую статистику
    global_stats.end_time = datetime.now()
    print_global_stats()

    # Экспортируем статистику если экспорт не отключен
    if not getattr(args, "no_export", False):
        export_session_data(global_stats)


# -------------------- Глобальная отчетность --------------------
def print_global_stats():
    """Печатает общую статистику по всем каналам"""
    logger.info("\n" + "=" * 80)
    logger.info("🏆 ОБЩАЯ ИТОГОВАЯ СТАТИСТИКА")
    logger.info("=" * 80)

    # Общая информация
    logger.info(f"📺 Общее количество каналов: {global_stats.total_channels}")
    logger.info(f"✅ Успешно проверено: {global_stats.completed_channels}")
    logger.info("⏱ Общая продолжительность: %.1f секунд", global_stats.duration)

    # Статистика по сегментам
    logger.info("📈 Всего сегментов: %d", global_stats.total_segments)
    logger.info("✅ Успешных загрузок: %d", global_stats.successful_downloads)
    logger.info("❌ Неудачных загрузок: %d", global_stats.failed_downloads)

    if global_stats.total_segments > 0:
        logger.info(
            "🎯 Общий процент успеха: %.1f%%", global_stats.overall_success_rate
        )

    if global_stats.total_bytes > 0:
        total_mb = global_stats.total_bytes / (1024 * 1024)
        logger.info(f"📡 Общий объём данных: {total_mb:.2f} MB")

    # Статистика по каналам
    if global_stats.channels:
        logger.info("\n📉 СТАТИСТИКА ПО КАНАЛАМ:")
        logger.info("-" * 80)

        for channel in global_stats.channels:
            if channel.total_segments > 0:
                logger.info(
                    f"📺 {channel.channel_name or 'Неизвестный'}: "
                    f"{channel.successful_downloads}/{channel.total_segments} "
                    f"({channel.success_rate:.1f}%) - "
                    f"{channel.total_bytes / (1024 * 1024):.1f} MB - "
                    f"{channel.duration:.1f}s"
                )

        # Наилучшие и наихудшие каналы
        # Фильтруем каналы с данными
        channels_with_data = [
            ch for ch in global_stats.channels if ch.total_segments > 0
        ]

        if len(channels_with_data) > 1:
            # Находим лучший и худший каналы
            best_channel = max(channels_with_data, key=lambda x: x.success_rate)
            worst_channel = min(channels_with_data, key=lambda x: x.success_rate)

            logger.info("\n🏅 ЛУЧШИЕ РЕЗУЛЬТАТЫ:")
            logger.info(
                "🥇 Лучший канал: %s (%.1f%%)",
                best_channel.channel_name,
                best_channel.success_rate,
            )
            logger.info(
                "🥉 Проблемный канал: %s (%.1f%%)",
                worst_channel.channel_name,
                worst_channel.success_rate,
            )

    # Общие ошибки
    all_errors = {}
    for channel in global_stats.channels:
        for segment in channel.segments:
            if not segment.success and segment.error_message:
                err_msg = segment.error_message
                all_errors[err_msg] = all_errors.get(err_msg, 0) + 1

    if all_errors:
        logger.info("\n⚠️ ОБЩИЕ ОШИБКИ:")
        sorted_errors = sorted(all_errors.items(), key=lambda x: x[1], reverse=True)
        for error, count in sorted_errors:
            logger.info("   %s: %d раз", error, count)

    # Добавляем информацию о ресурсах
    try:
        from resource_monitor import get_resource_summary

        resource_summary = get_resource_summary()
        if resource_summary:
            logger.info("\n🖥️ СВОДКА ПО РЕСУРСАМ:")
            logger.info("-" * 80)
            logger.info(
                f"📈 Средняя загрузка CPU: {resource_summary.get('cpu_average', 0)}% ({resource_summary.get('cpu_absolute_average', 0)}% от общего количества {resource_summary.get('cpu_count', 0)} ядер)"
            )
            logger.info(
                f"📈 Среднее использование памяти: {resource_summary.get('memory_average_percent', 0)}% ({resource_summary.get('memory_average_mb', 0)} MB из {resource_summary.get('memory_total_mb', 0)} MB всего)"
            )
            logger.info(
                f"🔥 Пиковая загрузка CPU: {resource_summary.get('cpu_peak', 0)}% ({resource_summary.get('cpu_absolute_peak', 0)}% от общего количества {resource_summary.get('cpu_count', 0)} ядер)"
            )
            logger.info(
                f"🔥 Пиковое использование памяти: {resource_summary.get('memory_peak_percent', 0)}% ({resource_summary.get('memory_peak_mb', 0)} MB из {resource_summary.get('memory_total_mb', 0)} MB всего)"
            )
            logger.info(
                f"📊 Количество измерений: {resource_summary.get('measurements_count', 0)}"
            )
    except ImportError:
        pass  # Resource monitor not available


# Email functionality has been removed as per requirements


def export_session_data(global_stats):
    """Экспортирует финальную статистику сессии"""
    try:
        # Создаем экспортер данных
        from data_exporter import OptimizedDataExporter

        exporter = OptimizedDataExporter(
            session_start=global_stats.start_time, session_end=global_stats.end_time
        )

        # Экспортируем данные
        exported_files = exporter.export_final_statistics(global_stats)
        return exported_files

    except ImportError as e:
        logger.error("❌ Ошибка импорта модуля: %s", e)
        return None
    except Exception as e:
        logger.error("❌ Ошибка при экспорте данных: %s", e)
        return None


# -------------------- CLI --------------------
def get_argument_parser():
    """Создает и настраивает парсер аргументов командной строки"""
    examples = """
Примеры использования:
  %(prog)s --count 1 --minutes 1      # Проверить один канал

  %(prog)s --refresh --count 10 --minutes 5
  # Проверить 10 каналов с обновлением плейлиста

  %(prog)s --count all --minutes 5
  # Проверить все каналы

  %(prog)s --count 1 --minutes 1 --no-export
  # Без экспорта данных
"""

    parser = argparse.ArgumentParser(
        description="HLS Stream Checker - проверка качества HLS потоков",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples,
    )

    # Основные параметры проверки
    parser.add_argument(
        "--count", default="1", help="Количество каналов: 1,10,20,all (по умолчанию 1)"
    )
    parser.add_argument(
        "--minutes", type=int, default=1, help="Длительность теста в минутах"
    )

    # Дополнительные параметры
    parser.add_argument(
        "--refresh", action="store_true", help="Обновить плейлист перед проверкой"
    )
    parser.add_argument(
        "--no-export", action="store_true", help="Отключить экспорт данных"
    )
    parser.add_argument(
        "--monitor-interval",
        type=int,
        default=60,
        help="Интервал мониторинга ресурсов в секундах (по умолчанию 60)",
    )

    return parser


def main():
    """Основная точка входа программы"""
    # Разбор аргументов командной строки
    args = get_argument_parser().parse_args()

    # Запуск мониторинга ресурсов
    start_resource_monitoring(args.monitor_interval)

    try:
        # Обновляем плейлист при необходимости
        if args.refresh or not PLAYLIST_JSON.exists():
            data = fetch_playlist()
            if not data:
                sys.exit(1)
            save_channels(data)

        # Запускаем проверку каналов
        channels = load_channels()
        run_checks(channels, args.minutes, args.count, args)
    finally:
        # Остановка мониторинга ресурсов
        stop_resource_monitoring()


if __name__ == "__main__":
    main()
