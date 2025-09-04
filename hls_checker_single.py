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

# Импорт модуля экспорта данных
from data_exporter import OptimizedDataExporter, create_optimized_readme

# -------------------- Конфигурация --------------------
PLAYLIST_URL = "https://pl.technettv.com/api/v4/playlist"
PLAYLIST_PARAMS = {
    "tz": "3", "region": "0", "native_region_only": "0", "lang": "en",
    "limit": "0", "page": "1", "epg": "0", "installts": "1756440756",
    "needCategories": "1", "podcasts": "1"
}
X_LHD_AGENT = {
    "generation": 2,
    "sdk": 30,
    "version_name": "1.0.4",
    "version_code": 6,
    "platform": "android",
    "device_id": "5dda2a6f7dcbe35f",
    "name": "samsung+SM-A127F",
    "app": "arabic.tv.watch.online"
}
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-LHD-Agent": json.dumps(X_LHD_AGENT, separators=(',', ':')),
    "Content-Type": "application/x-www-form-urlencoded",
}
PLAYLIST_JSON = Path("playlist_streams.json")

# -------------------- Структуры данных для отчетности --------------------
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

# Глобальная переменная для статистики
global_stats = GlobalStats()

# -------------------- Логирование --------------------
logging.basicConfig(
    level=logging.DEBUG,  # Изменили уровень на DEBUG для отладки
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hls_checker")

# Отключаем лишние сообщения от urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)

# -------------------- API --------------------
def fetch_playlist() -> Optional[Dict]:
    try:
        # Используем правильный payload из main.py
        data = ('subs_packs=%5B%5D&payload=W7ZxsWmx7n6mIy3LgFYDVYFu%2F8pa5iSJctK2rzIpzaFJyq'
               'bPMhjfTANi7fdMC0TXvpGJqInbwhgf%0AT%2BfiBojLZCzimRIvjowGZfdYvlrmoWeWe0ml9%2F'
               '5v6OaaKWYmM9gRJMUet%2FIJTFOvUvrIlgU%2FNUaj%0AyeieV6a3vV6OcJXzKcDEBNtS0JYS8'
               '%2BzK5LmFQvWOxxebn45hcwEkQ17jEsomIdPw4R6h4DgCb5qY%0AdQ0Nra9HwM6tG9s%2FQjBO'
               '9xuG21KkXazegIFLt1pQJpHdzaNiUJcYskSp%2BGa%2Fv%2FlKUjpG7dV5MVkh%0A2O71a9wje'
               'qSaKbmq4D9ZhiTYbRZiEhxdli7idQ%3D%3D%0A')
        
        # Обновляем заголовки согласно main.py
        ua = ('Mozilla/5.0 (Linux; Android 11; SM-A127F Build/RP1A.200720.012; wv) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/139.0.7258.158 '
              'Mobile Safari/537.36')
        
        headers = {
            "Host": "pl.technettv.com",
            "User-Agent": ua,
            "x-lhd-agent": json.dumps(X_LHD_AGENT, separators=(',', ':')),
            "x-token": "null",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        logger.debug(f"Отправка запроса на {PLAYLIST_URL}")
        logger.debug(f"Параметры: {PLAYLIST_PARAMS}")
        logger.debug(f"Заголовки: {headers}")
        
        r = requests.post(
            PLAYLIST_URL, 
            params=PLAYLIST_PARAMS, 
            data=data, 
            headers=headers, 
            timeout=20
        )
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
        if hasattr(e, 'response') and e.response is not None:
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
    channels = []
    if not api_json:
        logger.error("Получен пустой ответ от API")
        return
        
    items = api_json.get("channels", [])
    if not items:
        logger.error("В ответе API нет списка каналов")
        return
        
    logger.info(f"Найдено {len(items)} каналов в ответе API")
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
    logger.info(f"Сохранено {len(channels)} каналов в {PLAYLIST_JSON}")
    
    # Выводим первый канал для отладки
    if channels:
        logger.debug(f"Пример первого канала: {json.dumps(channels[0], ensure_ascii=False)}")

def load_channels() -> List[Dict]:
    if not PLAYLIST_JSON.exists():
        return []
    with open(PLAYLIST_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------- M3U8 --------------------
def parse_master(text: str, base_url: str) -> List[Dict]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    variants = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXT-X-STREAM-INF:"):
            attrs = {}
            for part in lines[i].split(":", 1)[1].split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    attrs[k] = v.strip().strip('"')
            uri = lines[i+1] if i+1 < len(lines) else None
            bw = int(attrs.get("BANDWIDTH", 0))
            res = (0, 0)
            if "RESOLUTION" in attrs:
                try:
                    w, h = attrs["RESOLUTION"].split("x")
                    res = (int(w), int(h))
                except: pass
            if uri:
                variants.append({"bw": bw, "res": res, "uri": urljoin(base_url, uri)})
            i += 2
        else:
            i += 1
    return variants

def best_variant(variants: List[Dict]) -> Optional[str]:
    if not variants: return None
    return max(variants, key=lambda v: (v["bw"], v["res"]))["uri"]

# -------------------- Проверка потока --------------------
class HLSStreamChecker:
    def __init__(self, url: str, channel_stats: Optional[ChannelStats] = None):
        self.url = url
        self.headers = HEADERS
        self.running = True
        self.stats = channel_stats or ChannelStats()
        self.segment_buffer = deque(maxlen=100)  # Буфер последних сегментов
        
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

    def _stop(self, *_):
        self.running = False

    def fetch_text(self, url: str) -> Optional[str]:
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.text
        except: return None

    def parse_media(self, text: str) -> List[str]:
        lines = [ln.strip() for ln in text.splitlines() if ln and not ln.startswith("#")]
        return lines

    def download_segment(self, url: str) -> tuple[bool, SegmentStats]:
        """Скачивает сегмент и возвращает статистику"""
        segment_name = url.split('/')[-1]
        start_time = time.time()
        
        segment_stats = SegmentStats(
            name=segment_name,
            url=url,
            success=False,
            timestamp=datetime.now()
        )
        
        try:
            with requests.get(url, headers=self.headers, timeout=10, stream=True) as r:
                r.raise_for_status()
                tmp = tempfile.NamedTemporaryFile(delete=False)
                total_size = 0
                
                for chunk in r.iter_content(1024*64):
                    if chunk: 
                        tmp.write(chunk)
                        total_size += len(chunk)
                
                tmp.close()
                download_time = time.time() - start_time
                
                # Обновляем статистику
                segment_stats.success = True
                segment_stats.size_bytes = total_size
                segment_stats.download_time = download_time
                
                # Логирование с деталями
                size_mb = total_size / (1024 * 1024)
                speed_mbps = size_mb / download_time if download_time > 0 else 0
                logger.info(f"✅ {segment_name} - {size_mb:.2f} MB, время: {download_time:.2f}s, скорость: {speed_mbps:.2f} MB/s")
                
                os.unlink(tmp.name)
                return True, segment_stats
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка HTTP: {e}"
            segment_stats.error_message = error_msg
            logger.error(f"❌ {segment_name} - {error_msg}")
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {e}"
            segment_stats.error_message = error_msg
            logger.error(f"❌ {segment_name} - {error_msg}")
        
        segment_stats.download_time = time.time() - start_time
        return False, segment_stats
    
    def _print_intermediate_stats(self):
        """Печатает промежуточную статистику"""
        if self.stats.total_segments == 0:
            return
            
        logger.info(f"📈 ПРОМЕЖУТОЧНАЯ СТАТИСТИКА:")
        logger.info(f"📄 Сегментов: {self.stats.successful_downloads}/{self.stats.total_segments} "
                   f"({self.stats.success_rate:.1f}% успешно)")
        if self.stats.total_bytes > 0:
            logger.info(f"📡 Загружено: {self.stats.total_bytes / (1024 * 1024):.2f} MB")
        if self.stats.avg_download_speed > 0:
            logger.info(f"⚡ Средняя скорость: {self.stats.avg_download_speed:.2f} MB/s")
        logger.info(f"⏱ Время работы: {self.stats.duration:.1f} секунд")
        
        # Показываем последние ошибки
        recent_errors = [s for s in self.stats.segments[-10:] if not s.success]
        if recent_errors:
            logger.info(f"⚠️ Последние ошибки: {len(recent_errors)} из 10")
    
    def _print_final_stats(self):
        """Печатает финальную статистику по каналу"""
        logger.info("=" * 70)
        logger.info("📁 ФИНАЛЬНАЯ СТАТИСТИКА КАНАЛА")
        
        if self.stats.channel_name:
            logger.info(f"📺 Канал: {self.stats.channel_name}")
        logger.info(f"🔗 URL: {self.url}")
        logger.info(f"📈 Всего сегментов: {self.stats.total_segments}")
        logger.info(f"✅ Успешных загрузок: {self.stats.successful_downloads}")
        logger.info(f"❌ Неудачных загрузок: {self.stats.failed_downloads}")
        
        if self.stats.total_segments > 0:
            logger.info(f"🎯 Процент успеха: {self.stats.success_rate:.1f}%")
        
        if self.stats.total_bytes > 0:
            total_mb = self.stats.total_bytes / (1024 * 1024)
            logger.info(f"📡 Общий объем: {total_mb:.2f} MB")
            
        if self.stats.avg_download_speed > 0:
            logger.info(f"⚡ Средняя скорость: {self.stats.avg_download_speed:.2f} MB/s")
            
        logger.info(f"⏱ Общая продолжительность: {self.stats.duration:.1f} секунд")
        
        # Показываем детали ошибок
        if self.stats.failed_downloads > 0:
            logger.info(f"⚠️ Ошибки:")
            error_counts = {}
            for seg in self.stats.segments:
                if not seg.success and seg.error_message:
                    error_counts[seg.error_message] = error_counts.get(seg.error_message, 0) + 1
            
            for error, count in error_counts.items():
                logger.info(f"   {error}: {count} раз")
        
        logger.info("=" * 70)

    def run_for_duration(self, seconds: int):
        """Запускает проверку на указанное время с детальной статистикой"""
        logger.info("=" * 70)
        logger.info(f"🚀 НАЧИНАЮ ПРОВЕРКУ HLS ПОТОКА")
        logger.info(f"📺 URL: {self.url}")
        logger.info(f"⏱ Продолжительность: {seconds} секунд")
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
            new_segments = [seg for seg in segments if seg not in self.stats.processed_segments]
            
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
            selected = channels[:int(count)]
        except: 
            selected = channels[:1]
    
    # Инициализируем глобальную статистику
    global_stats.total_channels = len(selected)
    global_stats.start_time = datetime.now()
    
    logger.info("=" * 80)
    logger.info("🎆 НАЧАЛО ПРОВЕРКИ HLS КАНАЛОВ")
    logger.info(f"📄 Всего каналов для проверки: {len(selected)}")
    logger.info(f"⏱ Продолжительность каждой проверки: {minutes} минут")
    logger.info("=" * 80)

    for i, ch in enumerate(selected, 1):
        try:
            # Получаем URL мастер плейлиста
            master = ch.get("stream_common") or ch.get("url")
            if not master: 
                logger.warning(f"⚠️ Пропускаю канал {ch.get('name_ru', 'Неизвестный')} - нет URL")
                continue
                
            # Создаем статистику для канала
            channel_stats = ChannelStats(
                channel_name=ch.get('name_ru', ''),
                channel_id=ch.get('our_id'),
                master_url=master
            )
            global_stats.channels.append(channel_stats)
            
            logger.info("\n" + "="*60)
            logger.info(f"📺 Канал {i}/{len(selected)}: {channel_stats.channel_name}")
            logger.info(f"🔗 Master URL: {master}")
            
            # Получаем мастер плейлист и находим лучший вариант
            try:
                response = requests.get(master, headers=HEADERS, timeout=10)
                response.raise_for_status()
                txt = response.text
            except Exception as e:
                logger.error(f"❌ Не удалось получить мастер плейлист: {e}")
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
    
    # Экспортируем статистику
    if not getattr(args, 'no_export', False):
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
    logger.info(f"⏱ Общая продолжительность: {global_stats.duration:.1f} секунд")
    
    # Статистика по сегментам
    logger.info(f"📈 Всего сегментов: {global_stats.total_segments}")
    logger.info(f"✅ Успешных загрузок: {global_stats.successful_downloads}")
    logger.info(f"❌ Неудачных загрузок: {global_stats.failed_downloads}")
    
    if global_stats.total_segments > 0:
        logger.info(f"🎯 Общий процент успеха: {global_stats.overall_success_rate:.1f}%")
    
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
        channels_with_data = [ch for ch in global_stats.channels if ch.total_segments > 0]
        if len(channels_with_data) > 1:
            best_channel = max(channels_with_data, key=lambda x: x.success_rate)
            worst_channel = min(channels_with_data, key=lambda x: x.success_rate)
            
            logger.info("\n🏅 ЛУЧШИЕ РЕЗУЛЬТАТЫ:")
            logger.info(f"🥇 Лучший канал: {best_channel.channel_name} ({best_channel.success_rate:.1f}%)")
            logger.info(f"🥉 Проблемный канал: {worst_channel.channel_name} ({worst_channel.success_rate:.1f}%)")
    
    # Общие ошибки
    all_errors = {}
    for channel in global_stats.channels:
        for segment in channel.segments:
            if not segment.success and segment.error_message:
                all_errors[segment.error_message] = all_errors.get(segment.error_message, 0) + 1
    
    if all_errors:
        logger.info("\n⚠️ ОБЩИЕ ОШИБКИ:")
        for error, count in sorted(all_errors.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   {error}: {count} раз")
    
    logger.info("\n" + "=" * 80)
    logger.info("🎉 ПРОВЕРКА ЗАВЕРШЕНА!")
    logger.info("=" * 80)


def export_session_data(global_stats):
    """Экспортирует финальную статистику сессии в оптимальные форматы"""
    try:
        # Создаем оптимизированный экспортер
        exporter = OptimizedDataExporter(
            session_start=global_stats.start_time,
            session_end=global_stats.end_time
        )
        
        # Экспортируем только финальную статистику
        exported_files = exporter.export_final_statistics(global_stats)
        
        # Создаем оптимизированный README при первом запуске
        readme_path = Path("data") / "README.md"
        if not readme_path.exists():
            create_optimized_readme()
        
        logger.info("\n🎆 ЭКСПОРТ ФИНАЛЬНОЙ СТАТИСТИКИ УСПЕШНО!")
        logger.info("📈 CSV файлы - для менеджеров в Excel")
        logger.info("🚀 JSON файлы - для API и фронтенда")
        
        return exported_files
        
    except Exception as e:
        logger.error(f"❌ Ошибка при экспорте данных: {e}")
        return None

# -------------------- CLI --------------------
def main():
    p = argparse.ArgumentParser(description="HLS Stream Checker - проверка качества HLS потоков")
    p.add_argument("--count", default="1", help="1,10,20,all (по умолчанию 1)")
    p.add_argument("--minutes", type=int, default=1, help="Время теста (минуты)")
    p.add_argument("--refresh", action="store_true", help="Обновить плейлист")
    p.add_argument("--no-export", action="store_true", help="Отключить экспорт в CSV/JSON")
    args = p.parse_args()

    if args.refresh or not PLAYLIST_JSON.exists():
        data = fetch_playlist()
        if not data: sys.exit(1)
        save_channels(data)

    channels = load_channels()
    run_checks(channels, args.minutes, args.count, args)

if __name__ == "__main__":
    main()
