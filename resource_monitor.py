#!/usr/bin/env python3
"""
Resource monitoring module for HLS Stream Checker
Monitors CPU, memory, and network usage during stream checking
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import psutil

logger = logging.getLogger("resource_monitor")


@dataclass
class ResourceStats:
    """Resource usage statistics"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    memory_total_mb: float  # Total system memory in MB
    network_bytes_sent: int
    network_bytes_recv: int
    disk_io_read_bytes: int
    disk_io_write_bytes: int
    cpu_count: int  # Number of CPU cores


class ResourceMonitor:
    """Monitors system resource usage"""

    def __init__(self, interval_seconds: int = 60):
        """
        Initialize resource monitor

        Args:
            interval_seconds: Interval between measurements in seconds (default: 60)
        """
        self.interval_seconds = interval_seconds
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stats_history: List[ResourceStats] = []
        self._last_net_io = psutil.net_io_counters()
        self._last_disk_io = psutil.disk_io_counters()

    def _get_resource_stats(self) -> ResourceStats:
        """Get current resource usage statistics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_mb = memory.used / (1024 * 1024)
        memory_total_mb = memory.total / (1024 * 1024)

        # Network I/O
        net_io = psutil.net_io_counters()
        network_bytes_sent = net_io.bytes_sent - self._last_net_io.bytes_sent
        network_bytes_recv = net_io.bytes_recv - self._last_net_io.bytes_recv
        self._last_net_io = net_io

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_io_read_bytes = disk_io.read_bytes - self._last_disk_io.read_bytes
        disk_io_write_bytes = disk_io.write_bytes - self._last_disk_io.write_bytes
        self._last_disk_io = disk_io

        return ResourceStats(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            memory_total_mb=memory_total_mb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            disk_io_read_bytes=disk_io_read_bytes,
            disk_io_write_bytes=disk_io_write_bytes,
            cpu_count=cpu_count,
        )

    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info(
            f"🚀 Resource monitoring started (interval: {self.interval_seconds}s)"
        )

        # Initial measurement
        stats = self._get_resource_stats()
        self.stats_history.append(stats)
        self._log_stats(stats)

        while self.is_running:
            time.sleep(self.interval_seconds)
            if self.is_running:  # Check again after sleep
                stats = self._get_resource_stats()
                self.stats_history.append(stats)
                self._log_stats(stats)

    def _log_stats(self, stats: ResourceStats):
        """Log resource statistics"""
        logger.info(
            "📊 RESOURCES | CPU: %.1f%% | MEM: %.1f%% (%.1f MB) | "
            "NET: ↑%s ↓%s | DISK: R%s W%s",
            stats.cpu_percent,
            stats.memory_percent,
            stats.memory_mb,
            self._format_bytes(stats.network_bytes_sent),
            self._format_bytes(stats.network_bytes_recv),
            self._format_bytes(stats.disk_io_read_bytes),
            self._format_bytes(stats.disk_io_write_bytes),
        )

    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}TB"

    def start_monitoring(self):
        """Start resource monitoring in a separate thread"""
        if self.is_running:
            logger.warning("Resource monitoring is already running")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, name="ResourceMonitor", daemon=True
        )
        self.monitor_thread.start()
        logger.info("📈 Resource monitoring thread started")

    def stop_monitoring(self):
        """Stop resource monitoring"""
        if not self.is_running:
            return

        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

        logger.info("🛑 Resource monitoring stopped")
        self._print_summary()

    def _print_summary(self):
        """Print resource usage summary"""
        if not self.stats_history:
            return

        logger.info("=" * 80)
        logger.info("🖥️  RESOURCE USAGE SUMMARY")
        logger.info("=" * 80)

        # Calculate averages
        cpu_avg = sum(s.cpu_percent for s in self.stats_history) / len(
            self.stats_history
        )
        mem_avg = sum(s.memory_percent for s in self.stats_history) / len(
            self.stats_history
        )
        mem_mb_avg = sum(s.memory_mb for s in self.stats_history) / len(
            self.stats_history
        )
        mem_total_mb = (
            self.stats_history[0].memory_total_mb if self.stats_history else 0
        )
        cpu_count = self.stats_history[0].cpu_count if self.stats_history else 0

        # Find peaks
        cpu_peak = max(s.cpu_percent for s in self.stats_history)
        mem_peak = max(s.memory_percent for s in self.stats_history)
        mem_mb_peak = max(s.memory_mb for s in self.stats_history)

        # Network totals
        net_sent_total = sum(s.network_bytes_sent for s in self.stats_history)
        net_recv_total = sum(s.network_bytes_recv for s in self.stats_history)

        # Disk I/O totals
        disk_read_total = sum(s.disk_io_read_bytes for s in self.stats_history)
        disk_write_total = sum(s.disk_io_write_bytes for s in self.stats_history)

        # Calculate absolute CPU usage (total CPU percentage)
        cpu_absolute_avg = cpu_avg * cpu_count
        cpu_absolute_peak = cpu_peak * cpu_count

        logger.info(
            f"📈 AVERAGE CPU USAGE: {cpu_avg:.1f}% ({cpu_absolute_avg:.1f}% of total {cpu_count} cores)"
        )
        logger.info(
            f"📈 AVERAGE MEMORY USAGE: {mem_avg:.1f}% ({mem_mb_avg:.1f} MB of {mem_total_mb:.1f} MB total)"
        )
        logger.info(
            f"🔥 PEAK CPU USAGE: {cpu_peak:.1f}% ({cpu_absolute_peak:.1f}% of total {cpu_count} cores)"
        )
        logger.info(
            f"🔥 PEAK MEMORY USAGE: {mem_peak:.1f}% ({mem_mb_peak:.1f} MB of {mem_total_mb:.1f} MB total)"
        )
        logger.info(
            f"🌐 TOTAL NETWORK I/O: ↑{self._format_bytes(net_sent_total)} ↓{self._format_bytes(net_recv_total)}"
        )
        logger.info(
            f"💾 TOTAL DISK I/O: R{self._format_bytes(disk_read_total)} W{self._format_bytes(disk_write_total)}"
        )
        logger.info(f"📊 MEASUREMENTS TAKEN: {len(self.stats_history)}")

        # Additional detailed information for scaling decisions
        logger.info(
            f"📋 SYSTEM RESOURCES: {cpu_count} CPU cores, {mem_total_mb:.1f} MB total memory"
        )
        logger.info(
            f"📋 ABSOLUTE USAGE: {cpu_absolute_avg:.1f} MB memory avg, {cpu_absolute_peak:.1f} MB memory peak"
        )

        logger.info("=" * 80)

    def get_stats_summary(self) -> Dict:
        """Get a summary of resource statistics"""
        if not self.stats_history:
            return {}

        cpu_avg = sum(s.cpu_percent for s in self.stats_history) / len(
            self.stats_history
        )
        mem_avg = sum(s.memory_percent for s in self.stats_history) / len(
            self.stats_history
        )
        cpu_peak = max(s.cpu_percent for s in self.stats_history)
        mem_peak = max(s.memory_percent for s in self.stats_history)
        mem_mb_avg = sum(s.memory_mb for s in self.stats_history) / len(
            self.stats_history
        )
        mem_mb_peak = max(s.memory_mb for s in self.stats_history)
        mem_total_mb = (
            self.stats_history[0].memory_total_mb if self.stats_history else 0
        )
        cpu_count = self.stats_history[0].cpu_count if self.stats_history else 0

        # Calculate absolute CPU usage (total CPU percentage)
        cpu_absolute_avg = cpu_avg * cpu_count
        cpu_absolute_peak = cpu_peak * cpu_count

        return {
            "cpu_average": round(cpu_avg, 2),
            "cpu_absolute_average": round(cpu_absolute_avg, 2),
            "memory_average_percent": round(mem_avg, 2),
            "memory_average_mb": round(mem_mb_avg, 2),
            "cpu_peak": round(cpu_peak, 2),
            "cpu_absolute_peak": round(cpu_absolute_peak, 2),
            "memory_peak_percent": round(mem_peak, 2),
            "memory_peak_mb": round(mem_mb_peak, 2),
            "memory_total_mb": round(mem_total_mb, 2),
            "cpu_count": cpu_count,
            "measurements_count": len(self.stats_history),
        }


# Global resource monitor instance
resource_monitor = ResourceMonitor()


def start_resource_monitoring(interval_seconds: int = 60):
    """
    Start resource monitoring

    Args:
        interval_seconds: Interval between measurements in seconds (default: 60)
    """
    resource_monitor.interval_seconds = interval_seconds
    resource_monitor.start_monitoring()


def stop_resource_monitoring():
    """Stop resource monitoring"""
    resource_monitor.stop_monitoring()


def get_resource_summary() -> Dict:
    """
    Get resource usage summary

    Returns:
        Dictionary with resource usage statistics
    """
    return resource_monitor.get_stats_summary()
