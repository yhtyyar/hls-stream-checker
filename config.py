#!/usr/bin/env python3
"""
Configuration file for HLS Stream Checker
This file contains default settings that can be overridden by command line arguments
"""

import os
from pathlib import Path

# Default configuration values
DEFAULT_CHANNEL_COUNT = "all"
DEFAULT_DURATION_MINUTES = 5
DEFAULT_REFRESH_PLAYLIST = False
DEFAULT_EXPORT_DATA = True

# Directory paths
PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
CSV_DIR = DATA_DIR / "csv"
JSON_DIR = DATA_DIR / "json"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
CSV_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Playlist configuration
PLAYLIST_URL = "https://pl.technettv.com/api/v4/playlist"
PLAYLIST_PARAMS = {
    "tz": "3", 
    "region": "0", 
    "native_region_only": "0", 
    "lang": "en",
    "limit": "0", 
    "page": "1", 
    "epg": "0", 
    "installts": "1756440756",
    "needCategories": "1", 
    "podcasts": "1"
}

# User agent configuration
X_LHD_AGENT = {
    "generation": 2,
    "sdk": 30,
    "version_name": "1.0.4",
    "version_code": 6,
    "platform": "android",
    "device_id": "5dda2a6f7dcbe35f",
    "name": "samsung+SM-A127F"
}

# Logging configuration
LOG_LEVEL = os.getenv("HLS_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

# Network configuration
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

# Data export configuration
EXPORT_FILE_PREFIX = "hls"
EXPORT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Service configuration
SERVICE_CHECK_INTERVAL = 60  # seconds