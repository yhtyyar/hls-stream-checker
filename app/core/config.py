#!/usr/bin/env python3
"""
Core configuration for the FastAPI application
"""
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/v1/api"
    PROJECT_NAME: str = "Arabic TV HLS Stream Checker"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Professional HLS stream monitoring for Arabic TV channels"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.absolute()
    DATA_DIR: Path = PROJECT_ROOT / "data"
    CSV_DIR: Path = DATA_DIR / "csv"
    JSON_DIR: Path = DATA_DIR / "json"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    
    # Monitoring defaults
    DEFAULT_DURATION_MINUTES: int = 5
    MAX_DURATION_MINUTES: int = 1440  # 24 hours
    MIN_DURATION_MINUTES: int = 1
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000
    
    # File paths
    PLAYLIST_STREAMS_FILE: Path = PROJECT_ROOT / "playlist_streams.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(exist_ok=True)
settings.CSV_DIR.mkdir(exist_ok=True)
settings.JSON_DIR.mkdir(exist_ok=True)
settings.LOGS_DIR.mkdir(exist_ok=True)
