#!/usr/bin/env python3
"""
Unit tests for the resource monitoring module
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from resource_monitor import ResourceMonitor, ResourceStats


class TestResourceMonitor(unittest.TestCase):
    """Test cases for the ResourceMonitor class"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.monitor = ResourceMonitor(interval_seconds=1)

    def tearDown(self):
        """Clean up after each test method."""
        if self.monitor.is_running:
            self.monitor.stop_monitoring()

    def test_resource_stats_creation(self):
        """Test ResourceStats dataclass creation"""
        stats = ResourceStats(
            timestamp=time.time(),
            cpu_percent=25.5,
            memory_percent=45.2,
            memory_mb=512.0,
            memory_total_mb=1024.0,
            network_bytes_sent=1024,
            network_bytes_recv=2048,
            disk_io_read_bytes=4096,
            disk_io_write_bytes=8192,
            cpu_count=4,
        )

        self.assertEqual(stats.cpu_percent, 25.5)
        self.assertEqual(stats.memory_percent, 45.2)
        self.assertEqual(stats.memory_mb, 512.0)
        self.assertEqual(stats.memory_total_mb, 1024.0)
        self.assertEqual(stats.cpu_count, 4)
        self.assertEqual(stats.network_bytes_sent, 1024)
        self.assertEqual(stats.network_bytes_recv, 2048)
        self.assertEqual(stats.disk_io_read_bytes, 4096)
        self.assertEqual(stats.disk_io_write_bytes, 8192)

    def test_monitor_initialization(self):
        """Test ResourceMonitor initialization"""
        self.assertEqual(self.monitor.interval_seconds, 1)
        self.assertFalse(self.monitor.is_running)
        self.assertIsNone(self.monitor.monitor_thread)
        self.assertEqual(len(self.monitor.stats_history), 0)

    @patch("resource_monitor.psutil")
    def test_get_resource_stats(self, mock_psutil):
        """Test _get_resource_stats method"""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=45.2, used=512 * 1024 * 1024, total=1024 * 1024 * 1024
        )
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=1024, bytes_recv=2048
        )
        mock_psutil.disk_io_counters.return_value = MagicMock(
            read_bytes=4096, write_bytes=8192
        )

        stats = self.monitor._get_resource_stats()

        self.assertIsInstance(stats, ResourceStats)
        self.assertEqual(stats.cpu_percent, 25.5)
        self.assertEqual(stats.memory_percent, 45.2)
        self.assertEqual(stats.memory_mb, 512.0)
        self.assertEqual(stats.cpu_count, 4)

    def test_format_bytes(self):
        """Test _format_bytes method"""
        # Test different byte values
        self.assertEqual(self.monitor._format_bytes(1023), "1023.0B")
        self.assertEqual(self.monitor._format_bytes(1024), "1.0KB")
        self.assertEqual(self.monitor._format_bytes(1024 * 1024), "1.0MB")
        self.assertEqual(self.monitor._format_bytes(1024 * 1024 * 1024), "1.0GB")
        self.assertEqual(self.monitor._format_bytes(1024 * 1024 * 1024 * 1024), "1.0TB")

    def test_start_stop_monitoring(self):
        """Test start_monitoring and stop_monitoring methods"""
        # Initially not running
        self.assertFalse(self.monitor.is_running)

        # Start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.is_running)

        # Stop monitoring
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.is_running)

    @patch("resource_monitor.psutil")
    def test_get_stats_summary(self, mock_psutil):
        """Test get_stats_summary method"""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(
            percent=45.2, used=512 * 1024 * 1024, total=1024 * 1024 * 1024
        )
        mock_psutil.net_io_counters.return_value = MagicMock(
            bytes_sent=1024, bytes_recv=2048
        )
        mock_psutil.disk_io_counters.return_value = MagicMock(
            read_bytes=4096, write_bytes=8192
        )

        # Add some stats to history
        stats1 = self.monitor._get_resource_stats()
        time.sleep(0.1)  # Small delay to ensure different timestamps
        stats2 = self.monitor._get_resource_stats()

        self.monitor.stats_history = [stats1, stats2]

        summary = self.monitor.get_stats_summary()

        self.assertIn("cpu_average", summary)
        self.assertIn("memory_average_percent", summary)
        self.assertIn("cpu_peak", summary)
        self.assertIn("memory_peak_percent", summary)
        self.assertIn("measurements_count", summary)
        self.assertIn("cpu_absolute_average", summary)
        self.assertIn("cpu_absolute_peak", summary)
        self.assertIn("memory_average_mb", summary)
        self.assertIn("memory_peak_mb", summary)
        self.assertIn("memory_total_mb", summary)
        self.assertIn("cpu_count", summary)
        self.assertEqual(summary["measurements_count"], 2)


if __name__ == "__main__":
    unittest.main()
