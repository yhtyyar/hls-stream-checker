import pytest
import os
from pathlib import Path
from unittest.mock import patch, Mock

from hls_checker_single import HLSStreamChecker
from config import DEFAULT_HEADERS

@pytest.fixture
def hls_checker():
    return HLSStreamChecker(channel_count=1, duration_minutes=1)

def test_headers_configuration():
    """Test that headers are properly configured"""
    checker = HLSStreamChecker(channel_count=1, duration_minutes=1)
    headers = checker.get_headers()
    assert "user-agent" in headers
    assert headers["Host"] == "pl.technettv.com"

@pytest.mark.asyncio
async def test_download_segment(hls_checker):
    """Test segment download functionality"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test content"
    
    with patch('requests.get', return_value=mock_response):
        result = await hls_checker.download_segment(
            "test_segment",
            "http://example.com/segment.ts"
        )
        assert result.success is True
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
        assert isinstance(data, dict)
        assert "streams" in data
