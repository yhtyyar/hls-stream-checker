from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from hls_checker_single import ChannelStats, HLSStreamChecker


@pytest.fixture
def hls_checker():
    # Create a ChannelStats object for testing
    channel_stats = ChannelStats()
    return HLSStreamChecker(
        url="http://example.com/test.m3u8", channel_stats=channel_stats
    )


def test_headers_configuration():
    """Test that headers are properly configured"""
    # The headers are now in the global SESSION object, not in the checker instance
    # We can test that the SESSION has the correct headers
    from hls_checker_single import SESSION

    assert "user-agent" in SESSION.headers
    # Note: Host header is set per request, not globally


def test_download_segment(hls_checker):
    """Test segment download functionality"""
    # Create a mock response that supports the context manager protocol
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"test content"]

    # Create a context manager mock
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_response)
    mock_context.__exit__ = Mock(return_value=None)

    with patch("hls_checker_single.SESSION.get", return_value=mock_context):
        success, result = hls_checker.download_segment("http://example.com/segment.ts")
        assert success is True
        assert result.size_bytes == len(b"test content")


def test_data_export_directories():
    """Test that export directories exist"""
    from config import CSV_DIR, JSON_DIR

    assert CSV_DIR.exists()
    assert JSON_DIR.exists()


def test_playlist_format():
    """Test playlist JSON structure"""
    import json

    playlist_file = Path("playlist_streams.json")
    assert playlist_file.exists()

    with open(playlist_file) as f:
        data = json.load(f)
        # The playlist is now an array, not a dictionary with "streams" key
        assert isinstance(data, list)
        # Each item should be a dictionary with channel information
        if data:
            assert isinstance(data[0], dict)
            assert "name_ru" in data[0]
            assert "stream_common" in data[0] or "url" in data[0]
